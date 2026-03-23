"""Manage the sync of the viz indices."""

from __future__ import annotations

import abc
import types
from collections.abc import Iterable, Mapping
from typing import Any, ClassVar

import more_itertools
from typing_extensions import override

import gdcmodels
from gdcmodels import esmodels
from gdcmodels.sync import common

UNNORMALIZED_FIELDS = (
    common.DefaultNormalizerSynchronizer.DEFAULT_EXCLUDED_PROPERTIES
    - frozenset(("case_submitter_id", "entity_submitter_id"))
)
"""Fields within the mappings which should NOT have the clinical normalizer applied."""
NORMALIZER_SYNCHRONIZER = common.DefaultNormalizerSynchronizer(
    excluded_properties=UNNORMALIZED_FIELDS
)
"""The synchronizer for add the clinical normalizer to the appropriate fields."""


class PropertyTree:
    """A structure representing a tree of properties and their own sub-properties."""

    __slots__ = ("_tree",)

    def __init__(self, paths: Iterable[Iterable[str]] = ()) -> None:
        """Initialize a property tree from the given paths.

        Args:
            properties: A sequence of properties each represented as a path (a sequence of
            strings in their own right.)
        """
        paths = filter(None, paths)
        self._tree = types.MappingProxyType(
            more_itertools.map_reduce(
                ((property, sub_paths) for property, *sub_paths in paths),
                keyfunc=lambda p: p[0],
                valuefunc=lambda p: p[1],
                reducefunc=PropertyTree,
            )
        )

    @staticmethod
    def build_from_strs(unsplit_paths: Iterable[str]) -> PropertyTree:
        """Build a PropertyTree from a set of paths which need to be split on the `.` char.

        Args:
            unsplit_paths: A sequence of paths which need to be split before constructing the
                property tree.

        Returns:
            A property tree representing the given paths.
        """
        return PropertyTree(map(lambda s: s.split("."), unsplit_paths))

    def is_leaf_node(self) -> bool:
        """Determine if this node in the tree is a leaf node.

        Returns:
            True if this is a leaf node; otherwise False.
        """
        return not self.is_internal_node()

    def is_internal_node(self) -> bool:
        """Determine if this node is an internal node in the tree.

        Returns:
            True if this is an internal node; otherwise False.
        """
        return bool(self._tree)

    def __contains__(self, property: str) -> bool:
        return property in self._tree

    def __getitem__(self, property: str) -> PropertyTree:
        return self._tree[property]

    def get(self, property: str) -> PropertyTree:
        """Get the given property's subtree from this tree or returns a dummy empty tree.

        Args:
            property: The property node which should be returned if it is contained within
                this tree.
        """
        return self._tree.get(property, PropertyTree())


def _get_case_properties(
    case_properties: esmodels.Properties,
    excluded: PropertyTree = PropertyTree.build_from_strs(("case_autocomplete",)),
) -> esmodels.Properties:
    """Build a bare-bones copy of the case properties.

    This drops such things as copy-to and normalizers and only preserves the structure
    of the properties and their associated type.

    Args:
        case_properties: The properties from the graph/case mapping to copy.
        excluded: A property tree whose leaves should be excluded from the copied properties.

    Returns:
        A copy of the properties contained in the case_properties with only
        the structure of names and their associated type captured.
    """

    def _is_included(
        property: str, details: esmodels.Property | esmodels.Autocomplete
    ) -> bool:
        """Determine if the property should be included in the copy.

        Args:
            property: The name of the property
            details: The details of the property as described in the ES mapping.

        Returns:
            True if the property should be included within the copy. Otherwise, false.
        """
        return (
            # If the property is not excluded or just the parent of an excluded property, it
            # should be included.
            property not in excluded or excluded[property].is_internal_node()
        ) and (
            # Analyzers should always be excluded when copying mappings.
            "analyzer" not in details
        )

    result: esmodels.Properties = {}
    items: Iterable[tuple[str, esmodels.Property]] = (
        (p, d) for p, d in case_properties.items() if _is_included(p, d)
    )

    for name, property in items:
        if "properties" in property:
            result.setdefault(name, {})["properties"] = _get_case_properties(
                property["properties"], excluded.get(name)
            )
        if "type" in property:
            result.setdefault(name, {})["type"] = property["type"]

    return result


class CaseSynchronizer(common.Synchronizer, abc.ABC):
    EXCLUDED_PROPERTIES: ClassVar[PropertyTree] = PropertyTree.build_from_strs(
        (
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
    )
    """A property tree containing all props which should be excluded from the synced data."""

    @abc.abstractmethod
    def _remove_case_from(self, mappings: esmodels.ESMapping) -> None:
        """Remove any case properties in the current mapping that are dependent on the graph.

        This method should preserve any properties which are not based on the graph_case
        mappings. An example from the `gene_centric` index would be `case.cnvs`.

        Args:
            mappings: The current mappings as passed to this synchronizer.
        """

    @abc.abstractmethod
    def _structure_case_mappings(
        self, case_properties: esmodels.Properties
    ) -> esmodels.ESMapping:
        """Structures the properties loaded from the case index into a mappings structure.

        This method is intended to allow implementing classes to insert the case
        properties into the correct place within their own mappings structure.

        Example:
            in the `gene_centric` index
            {
                "properties": {
                    "case": {
                        "properties": case_properties
                    }
                }
            }

        Args:
            case_properties: The properties loaded from the `graph_case` index.

        Returns:
            A mappings object with the case_properties inserted within it.
        """

    @override
    def sync(self, mappings: esmodels.ESMapping, settings: Mapping[str, Any]) -> common.Export:
        graph_mappings = gdcmodels.get_es_models(vestigial_included=False)["gdc_from_graph"][
            "case"
        ].mappings
        case_properties = {
            **_get_case_properties(graph_mappings["properties"], self.EXCLUDED_PROPERTIES),
            "available_variation_data": {"type": "keyword"},
        }
        case_mappings = self._structure_case_mappings(case_properties)

        self._remove_case_from(mappings)

        return common.apply_defaults(mappings, case_mappings), settings


class CaseCentricSynchronizer(CaseSynchronizer):
    """A synchronizer for the case centric index mappings."""

    EXCLUDED_PROPERTIES: ClassVar[PropertyTree] = PropertyTree.build_from_strs(
        ("case_autocomplete",)
    )

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

    @override
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

    @override
    def _structure_case_mappings(
        self, case_properties: esmodels.Properties
    ) -> esmodels.ESMapping:
        return {"properties": case_properties}


class GeneCentricSynchronizer(CaseSynchronizer):
    """A synchronizer for the gene centric index mappings."""

    @override
    def _remove_case_from(self, mappings) -> None:
        case = mappings["properties"].pop("case")

        assert "properties" in case, "Case must have properties"

        cnv = case["properties"]["cnv"]
        ssm = case["properties"]["ssm"]

        mappings["properties"]["case"] = {
            "properties": {"cnv": cnv, "ssm": ssm},
            "type": "nested",
        }

    @override
    def _structure_case_mappings(
        self, case_properties: esmodels.Properties
    ) -> esmodels.ESMapping:
        _ = case_properties.get("samples", {}).pop("type", None)

        return {"properties": {"case": {"properties": case_properties}}}


class DataCentricSynchronizer(CaseSynchronizer):
    """A synchronizer for the cnv/segment_cnv/ssm centric index mappings."""

    @override
    def _remove_case_from(self, mappings: esmodels.ESMapping) -> None:
        occurrence = mappings["properties"]["occurrence"]

        assert "properties" in occurrence, "Occurrence must have a set of properties"
        assert "properties" in occurrence["properties"]["case"], (
            "Case must have set of properties"
        )

        observation = occurrence["properties"]["case"]["properties"]["observation"]
        occurrence["properties"]["case"]["properties"] = {"observation": observation}

    @override
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
    """A synchronizer for the cnv/segment_cnv/ssm occurrence centric index mappings."""

    @override
    def _remove_case_from(self, mappings: esmodels.ESMapping) -> None:
        assert "properties" in mappings["properties"]["case"], (
            "Case must have set of properties"
        )

        observation = mappings["properties"]["case"]["properties"]["observation"]
        mappings["properties"]["case"]["properties"] = {"observation": observation}

    @override
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
        # TODO: This will be explored more in DEV-3636 but this class should offer a jumping
        # off point for when we finalize what properties to include in the non-case indices
        # GeneCentricSynchronizer(),
        NORMALIZER_SYNCHRONIZER,
    )
)
DATA_CENTRIC_SYNCHRONIZERS = common.CompositeSynchronizer(
    (
        common.DefaultMappingsSynchronizer(),
        common.DefaultSettingsSynchronizer(),
        # TODO: This will be explored more in DEV-3636 but this class should offer a jumping
        # off point for when we finalize what properties to include in the non-case indices
        # DataCentricSynchronizer(),
        NORMALIZER_SYNCHRONIZER,
    )
)
OCCURRENCE_CENTRIC_SYNCHRONIZERS = common.CompositeSynchronizer(
    (
        common.DefaultMappingsSynchronizer(),
        common.DefaultSettingsSynchronizer(),
        # TODO: This will be explored more in DEV-3636 but this class should offer a jumping
        # off point for when we finalize what properties to include in the non-case indices
        # OccurrenceCentricSynchronizer(),
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
