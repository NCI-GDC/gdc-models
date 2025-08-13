"""Manage the sync of the viz indices."""

from __future__ import annotations

import abc
import functools
import types
from collections.abc import Sequence
from typing import Any, ClassVar, Iterable, Mapping, Tuple

import gdcmodels
from gdcmodels import esmodels
from gdcmodels.sync import common

Excluded = Mapping[str, "Excluded"]
MutableExcluded = dict[str, "MutableExcluded"]

UNNORMALIZED_FIELDS = (
    common.DefaultNormalizerSynchronizer.DEFAULT_EXCLUDED_PROPERTIES
    - frozenset(("case_submitter_id", "entity_submitter_id"))
)
NORMALIZER_SYNCHRONIZER = common.DefaultNormalizerSynchronizer(
    excluded_properties=UNNORMALIZED_FIELDS
)


def _get_case_properties(
    case_properties: esmodels.Properties,
    excluded: Excluded = types.MappingProxyType(
        {"case_autocomplete": types.MappingProxyType({})}
    ),
) -> esmodels.Properties:
    """
    Build a bare-bones copy of the case properties.

    This drops such things as copy-to and normalizers and only preserves the structure
    of the properties and their associated type.

    Args:
        case_properties: The properties from the graph/case mapping to copy.

    Returns:
        A copy of the properties contained in the case_properties with only
        the structure of names and their associated type captured.
    """

    def _is_included(
        property: str, details: esmodels.Property | esmodels.Autocomplete
    ) -> bool:
        return (
            # If the property is not excluded or just the parent of an excluded property, it
            # should be included.
            property not in excluded
            or bool(excluded[property])
        ) and (
            # Analyzers should always be excluded when copying mappings.
            "analyzer"
            not in details
        )

    result: esmodels.Properties = {}
    items: Iterable[Tuple[str, esmodels.Property]] = (
        (p, d) for p, d in case_properties.items() if _is_included(p, d)
    )

    for name, property in items:
        if "properties" in property:
            result.setdefault(name, {})["properties"] = _get_case_properties(
                property["properties"], excluded.get(name, {})
            )
        if "type" in property:
            result.setdefault(name, {})["type"] = property["type"]

    return result


class CaseSynchronizer(common.Synchronizer, abc.ABC):
    EXCLUDED_PROPERTIES: ClassVar[Sequence[str]] = (
        "aliquot_ids",
        "analyte_ids",
        "annotations",
        "case_autocomplete",
        "created_datetime",
        "demographic.created_datetime",
        "demographic.updated_datetime",
        "diagnoses.annotations",
        "diagnoses.created_datetime",
        "diagnoses.pathology_details.created_datetime",
        "diagnoses.pathology_details.updated_datetime",
        "diagnoses.treatments.created_datetime",
        "diagnoses.treatments.updated_datetime",
        "diagnoses.updated_datetime",
        "diagnosis_ids",
        "exposures.created_datetime",
        "exposures.updated_datetime",
        "family_histories.created_datetime",
        "family_histories.updated_datetime",
        "files",
        "follow_ups",
        "portion_ids",
        "sample_ids",
        "samples.annotations",
        "samples.created_datetime",
        "samples.portions",
        "samples.updated_datetime",
        "samples.type",
        "slide_ids",
        "submitter_aliquot_ids",
        "submitter_analyte_ids",
        "submitter_diagnosis_ids",
        "submitter_portion_ids",
        "submitter_sample_ids",
        "submitter_slide_ids",
        "summary",
        "updated_datetime",
    )

    @abc.abstractmethod
    def _remove_case_from(self, mappings: esmodels.ESMapping) -> None:
        ...

    @abc.abstractmethod
    def _structure_case_mappings(
        self, case_properties: esmodels.Properties
    ) -> esmodels.ESMapping:
        ...

    @property
    def _excluded_properties(self) -> Excluded:
        properties = map(lambda p: p.split("."), self.EXCLUDED_PROPERTIES)
        excluded = {}

        for property in properties:
            functools.reduce(lambda e, p: e.setdefault(p, {}), property, excluded)

        return excluded

    def _build_available_variation_data(self) -> esmodels.Properties:
        return {"available_variation_data": {"type": "keyword"}}

    def sync(self, mappings: esmodels.ESMapping, settings: Mapping[str, Any]) -> common.Export:
        graph_mappings = gdcmodels.get_es_models(vestigial_included=False)["gdc_from_graph"][
            "case"
        ].mappings
        case_properties = _get_case_properties(
            graph_mappings["properties"], self._excluded_properties
        )
        case_mappings = self._structure_case_mappings(case_properties)

        self._remove_case_from(mappings)

        return common.apply_defaults(mappings, case_mappings), settings


class CaseCentricSynchronizer(CaseSynchronizer):
    EXCLUDED_PROPERTIES: ClassVar[Sequence[str]] = ("case_autocomplete",)

    def _get_copy_to_properties(self, properties: esmodels.Properties) -> esmodels.Properties:
        autocomplete_properties = {}

        for prop, details in properties.items():
            if "copy_to" in details:
                autocomplete_properties[prop] = details
            elif "properties" in details:
                sub_autocomplete_properties = self._get_copy_to_properties(
                    details["properties"]
                )

                if sub_autocomplete_properties:
                    autocomplete_properties[prop] = {"properties": sub_autocomplete_properties}

        return autocomplete_properties

    def _remove_case_from(self, mappings) -> None:
        autocomplete = mappings["properties"]["case_autocomplete"]
        gene = mappings["properties"]["gene"]
        segment_cnv = mappings["properties"]["segment_cnv"]

        mappings["properties"] = {
            "case_autocomplete": autocomplete,
            "gene": gene,
            "segment_cnv": segment_cnv,
            **self._get_copy_to_properties(mappings["properties"]),
        }

    def _structure_case_mappings(
        self, case_properties: esmodels.Properties
    ) -> esmodels.ESMapping:
        return {"properties": {**case_properties, **self._build_available_variation_data()}}


class GeneCentricSynchronizer(CaseSynchronizer):
    def _remove_case_from(self, mappings) -> None:
        case = mappings["properties"].pop("case")

        assert "properties" in case, "Case must have properties"

        cnv = case["properties"]["cnv"]
        ssm = case["properties"]["ssm"]

        mappings["properties"]["case"] = {
            "properties": {"cnv": cnv, "ssm": ssm},
            "type": "nested",
        }

    def _structure_case_mappings(
        self, case_properties: esmodels.Properties
    ) -> esmodels.ESMapping:
        _ = case_properties.get("samples", {}).pop("type", None)

        return {
            "properties": {
                "case": {
                    "properties": {**case_properties, **self._build_available_variation_data()}
                }
            }
        }


class DataCentricSynchronizer(CaseSynchronizer):
    def _remove_case_from(self, mappings: esmodels.ESMapping) -> None:
        occurrence = mappings["properties"]["occurrence"]

        assert "properties" in occurrence, "Occurrence must have a set of properties"
        assert (
            "properties" in occurrence["properties"]["case"]
        ), "Case must have set of properties"

        observation = occurrence["properties"]["case"]["properties"]["observation"]
        occurrence["properties"]["case"]["properties"] = {
            "observation": observation,
            **self._build_available_variation_data(),
        }

    def _structure_case_mappings(
        self, case_properties: esmodels.Properties
    ) -> esmodels.ESMapping:
        _ = case_properties.get("samples", {}).pop("type", None)

        return {
            "properties": {
                "occurrence": {"properties": {"case": {"properties": case_properties}}}
            }
        }


class OccurrenceCentricSynchronizer(CaseSynchronizer):
    def _remove_case_from(self, mappings: esmodels.ESMapping) -> None:
        assert (
            "properties" in mappings["properties"]["case"]
        ), "Case must have set of properties"

        observation = mappings["properties"]["case"]["properties"]["observation"]
        mappings["properties"]["case"]["properties"] = {
            "observation": observation,
            **self._build_available_variation_data(),
        }

    def _structure_case_mappings(
        self, case_properties: esmodels.Properties
    ) -> esmodels.ESMapping:
        _ = case_properties.get("samples", {}).pop("type", None)

        return {"properties": {"case": {"properties": case_properties}}}


CASE_CENTRIC_SYNCHRONIZERS = common.CompositeSynchronizer(
    (
        common.DefaultMappingsSynchronizer(),
        common.DefaultSettingsSynchronizer(),
        CaseCentricSynchronizer(),
        NORMALIZER_SYNCHRONIZER,
    )
)
GENE_CENTRIC_SYNCHRONIZERS = common.CompositeSynchronizer(
    (
        common.DefaultMappingsSynchronizer(),
        common.DefaultSettingsSynchronizer(),
        GeneCentricSynchronizer(),
        NORMALIZER_SYNCHRONIZER,
    )
)
DATA_CENTRIC_SYNCHRONIZERS = common.CompositeSynchronizer(
    (
        common.DefaultMappingsSynchronizer(),
        common.DefaultSettingsSynchronizer(),
        DataCentricSynchronizer(),
        NORMALIZER_SYNCHRONIZER,
    )
)
OCCURRENCE_CENTRIC_SYNCHRONIZERS = common.CompositeSynchronizer(
    (
        common.DefaultMappingsSynchronizer(),
        common.DefaultSettingsSynchronizer(),
        OccurrenceCentricSynchronizer(),
        NORMALIZER_SYNCHRONIZER,
    )
)


SYNCHRONIZERS = types.MappingProxyType(
    {
        "case_centric": {"case_centric": CASE_CENTRIC_SYNCHRONIZERS},
        "cnv_centric": {"cnv_centric": DATA_CENTRIC_SYNCHRONIZERS},
        "cnv_occurrence_centric": {"cnv_occurrence_centric": OCCURRENCE_CENTRIC_SYNCHRONIZERS},
        "gene_centric": {"gene_centric": GENE_CENTRIC_SYNCHRONIZERS},
        "segment_cnv_centric": {"segment_cnv_centric": DATA_CENTRIC_SYNCHRONIZERS},
        "segment_cnv_occurrence_centric": {
            "segment_cnv_occurrence_centric": OCCURRENCE_CENTRIC_SYNCHRONIZERS
        },
        "ssm_centric": {"ssm_centric": DATA_CENTRIC_SYNCHRONIZERS},
        "ssm_occurrence_centric": {"ssm_occurrence_centric": OCCURRENCE_CENTRIC_SYNCHRONIZERS},
    }
)
