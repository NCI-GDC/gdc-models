"""This module defines the structures which need to be extracted from the GDC graph."""

from __future__ import annotations

import abc
import copy
import functools
import itertools
import logging
import types
from collections.abc import Iterator, Mapping, Sequence, Set
from typing import Any, TypedDict

import gdcdictionary
import more_itertools
from gdcdatamodel2 import models
from typing_extensions import ReadOnly, Self, override

from gdcmodels import constants

__all__ = ("STRUCTURES",)

logger = logging.getLogger(__name__)

DICTIONARY = gdcdictionary.gdcdictionary
"""The GDC dictionary object."""
UNIVERSALLY_EXCLUDED_PROPERTIES = frozenset(
    {"project_id", "batch_id", "file_state", "curated_model_index"}
)
"""These are properties from the graph which are always to be excluded from the mapping."""


class PropertyDetail(TypedDict):
    """A dictionary representing an atomic property in elasticsearch."""

    type: ReadOnly[str]


def _get_details(_types: tuple[type, ...], /) -> PropertyDetail:
    """Gets the elasticsearch property details for a property from the dictionary.

    Args:
        _types: The types which were defined for the property in gdcdatamodel2 via the
            `pg_property` wrapper.

    Returns:
        The elasticsearch property details which should be used for the exported dictionary
        property.
    """
    if float in _types:
        return PropertyDetail(type="double")
    elif int in _types:
        return PropertyDetail(type="long")

    return PropertyDetail(type="keyword")


def _get_nodes_by_category(*categories: str) -> Iterator[type[models.Node]]:
    """Gets all nodes from the dictionary whose `category` is one of the given categories.

    Args:
        categories: The category values which should be selected from the dictionary.

    Yields:
        All gdcdatamodel2 nodes whose category matches the given.
    """
    return filter(
        lambda n: (
            n._dictionary["category"]  # type: ignore
            in categories
        ),
        models.Node.get_subclasses(),
    )


def _to_occurrence_structure(case: Structure, description_root: str) -> Structure:
    """Nests the given case structure within an occurrence structure.

    Args:
        case: The structure which represents the case data.
        description_root: The root name to append before all property descriptions in the
            metadata.

    Returns:
        A new structure wherein the case data is a child of an occurrence node i.e. the path
        to the case data as: `occurrence.case`
    """
    return Structure(
        is_nested=False,
        description_root=description_root,
        children=dict(
            occurrence=Structure(is_nested=True, children=dict(case=case.as_unnested()))
        ),
    )


def _to_case_structure(
    case: Structure, description_root: str, is_nested: bool = False
) -> Structure:
    """Nests the given case structure within an single case structure.

    Args:
        case: The structure which represents the case data.
        description_root: The root name to append before all property descriptions in the
            metadata.

    Returns:
        A new structure wherein the case data is a child node of the root i.e. the path
        to the case data as: `case`
    """
    return Structure(
        is_nested=False,
        description_root=description_root,
        children=dict(case=case.as_nested() if is_nested else case.as_unnested()),
    )


class Structure:
    """A structure which represents an object in an elasticsearch mapping."""

    __slots__ = ("_children", "_description_root", "_is_nested")

    def __init__(
        self,
        is_nested: bool,
        description_root: str | None = None,
        children: Mapping[str, Structure] = types.MappingProxyType({}),
    ) -> None:
        """Initializes a structure.

        Args:
            is_nested: A flag indicating if this structure needs to be configured as a nested
                type within resulting mappings.
            description_root: The name which should prepend all descriptions within
                `_meta.descriptions`. This should only be defined for the root structure.
            children: All children structures which are nested within this one.
        """
        self._children = children
        self._description_root = description_root or "$"
        self._is_nested = is_nested

    @property
    def children(self) -> Mapping[str, Structure]:
        """All children structures which are nested within this one."""
        return self._children

    @property
    def is_nested(self) -> bool:
        """A flag indicating if this structure needs to be configured as a nested type."""
        return self._is_nested

    def as_nested(self) -> Self:
        """Copies this structure as a nested mapping.

        Returns:
            A copy of this structure with `is_nested == True`
        """
        struct = copy.copy(self)
        struct._is_nested = True

        return struct

    def as_unnested(self) -> Self:
        """Copies this structure as a regular mapping which is not nested.

        Returns:
            A copy of this structure with `is_nested == False`
        """
        struct = copy.copy(self)
        struct._is_nested = False

        return struct

    def _array_fields(self, path: Sequence[str] = ()) -> Sequence[str]:
        """Loads all array fields from the dictionary.

        Args:
            path: The names of the parent nodes in the tree which have been traversed in order
                to reach this node.

        Returns:
            A sorted sequence of fields which store array data. E.g.
            `("aliquot_ids", "diagnoses.treatments.treatment_anatomic_sites")`
        """
        fields = itertools.chain.from_iterable(
            child._array_fields((*path, name)) for name, child in self.children.items()
        )

        if self._is_nested:
            fields = more_itertools.value_chain(".".join(path), fields)

        return sorted(fields)

    def _load_descriptions(self, root: str) -> Mapping[str, str]:
        """Loads the descriptions of each field within the structure from the dictionary.

        Args:
            root: This is the namespace for which any description that is resolved in this
                load process should be nested within.

        Returns:
            A mapping of field names to their description from the dictionary. E.g.
            `{"cases.project.name": "Display name for the project"}`
        """
        return dict(
            itertools.chain.from_iterable(
                child._load_descriptions(f"{root}.{name}").items()
                for name, child in self.children.items()
            )
        )

    def _meta(self) -> Mapping[str, Any]:
        """Loads all data which should be found in the mappings' `_meta` field."""
        return {
            "arrays": self._array_fields(),
            "descriptions": self._load_descriptions(self._description_root),
        }

    def to_mapping(self, include_meta: bool = True) -> dict[str, Any]:
        """Converts the structure to an elasticsearch mapping.

        Args:
            include_meta: A flag indicating that the meta data for this node in the tree
                should be included. This is generally only true for the root node.

        Returns:
            A mapping structure representing all of the dynamic elements which are based on
            nodes and other elements of the graph.
        """
        properties = {
            name: child.to_mapping(include_meta=False) for name, child in self.children.items()
        }
        properties = dict(properties.items())
        mapping: dict[str, Any] = {"properties": properties}

        if include_meta:
            mapping["_meta"] = self._meta()

        if self._is_nested:
            mapping["type"] = "nested"

        return mapping


class NodesStructureABC(Structure, abc.ABC):
    """An abstract structure whose mapping is driven by a set of dictionary nodes."""

    __slots__ = ("_nodes",)

    def __init__(
        self,
        nodes: Sequence[type[models.Node]],
        is_nested: bool,
        description_root: str | None = None,
        children: Mapping[str, Structure] = types.MappingProxyType({}),
    ) -> None:
        """Initializes a node based structure in a tree.

        Args:
            nodes: All nodes which this structure represents. A set of ALL properties
                associated with each node is used to map this structures associated
                properties.
            is_nested: A flag indicating if this structure needs to be configured as a nested
                type within resulting mappings.
            description_root: The name which should prepend all descriptions within
                `_meta.descriptions`. This should only be defined for the root structure.
            children: All children structures which are nested within this one.
        """
        super().__init__(is_nested, description_root, children)

        self._nodes = nodes

    @property
    def nodes(self) -> Sequence[type[models.Node]]:
        """The nodes which drive the ultimate mapping represented by this structure."""
        return self._nodes

    def _is_prop_included(self, prop: str) -> bool:
        """Indicates if the given property should be included in the final mapping.

        Args:
            prop: The property which exists on one of the nodes associated with this
            structure.
        """
        return prop not in UNIVERSALLY_EXCLUDED_PROPERTIES

    @property
    def _pg_properties(self) -> Mapping[str, tuple[type, ...]]:
        """All pg properties and their associated types found in the node definitions."""
        return {
            prop: _types
            for node in self.nodes
            for prop, _types in node.get_pg_properties().items()
        }

    def _extract_properties(self) -> Mapping[str, PropertyDetail]:
        """Extracts all properties that need to be included in the generated mapping.

        Returns:
            A mapping of property names to their associated details required for mapping
            scalar values.
        """
        return {
            prop: _get_details(_types)
            for prop, _types in self._pg_properties.items()
            if self._is_prop_included(prop)
        }

    def _load_schema_properties(self) -> Iterator[tuple[str, Mapping[str, Any]]]:
        """Loads all properties and their associated json schema from the dictionary.

        Yields:
            A tuple of the property name & its json schema definition from the dictionary if
            it is included in the mapping.
        """
        for node in self.nodes:
            schema = DICTIONARY.schema[node.get_label()]

            for prop, details in schema["properties"].items():
                if self._is_prop_included(prop):
                    yield prop, details

    def _load_node_descriptions(self, root: str) -> Mapping[str, str]:
        """Loads the property description associated with this structure's nodes.

        Args:
            root: The current `.` delimited path from this node back to the mapping root.

        Returns:
            A mapping of fields contained in this structures mapping with their associated
            description from the dictionary.
        """
        descriptions = {}

        for prop, details in self._load_schema_properties():
            if description := details.get(
                "description", details.get("common", {}).get("description")
            ):
                descriptions[f"{root}.{prop}"] = description

        return descriptions

    @override
    def _load_descriptions(self, root: str) -> Mapping[str, str]:
        return {**super()._load_descriptions(root), **self._load_node_descriptions(root)}

    def _node_array_fields(self, path: Sequence[str]) -> Iterator[str]:
        """Recursively loads array fields associated with the structures nodes & children.

        Args:
            path: The names of all (if any) parents of this structure which are used to
                construct the full field name of an array field.

        Returns:
            Yields all fields as full paths in the structures associated mapping which contain
            array data.
        """
        for prop, details in self._load_schema_properties():
            if details.get("type") == "array":
                yield ".".join((*path, prop))

    @override
    def _array_fields(self, path: Sequence[str] = ()) -> Sequence[str]:
        return sorted(
            itertools.chain(
                super()._array_fields(path), frozenset(self._node_array_fields(path))
            )
        )

    @override
    def to_mapping(self, include_meta: bool = True) -> dict[str, Any]:
        mapping = super().to_mapping(include_meta)
        mapping["properties"] = dict(
            {**self._extract_properties(), **mapping["properties"]}.items()
        )

        return mapping


class NodesStructure(NodesStructureABC):
    """A structure whose mapping includes all properties defined by its associated nodes."""

    __slots__ = ("_excluded_properties",)

    def __init__(
        self,
        nodes: Sequence[type[models.Node]],
        is_nested: bool,
        description_root: str | None = None,
        children: Mapping[str, Structure] = types.MappingProxyType({}),
        excluded_properties: Set[str] = frozenset(),
    ) -> None:
        """Initializes a node based structure in a tree.

        Args:
            nodes: All nodes which this structure represents. A set of ALL properties
                associated with each node is used to map this structures associated
                elasticsearch properties unless explicitly excluded.
            is_nested: A flag indicating if this structure needs to be configured as a nested
                type within resulting mappings.
            description_root: The name which should prepend all descriptions within
                `_meta.descriptions`. This should only be defined for the root structure.
            children: All children structures which are nested within this one.
            excluded_properties: A set of property names which should be excluded when
                generating the mapping for this structure. By default, all properties are
                included.
        """
        super().__init__(nodes, is_nested, description_root, children)

        # Warn devs that there are old properties which should be removed from configured
        # excluded properties.
        # !!!DOES NOT CHANGE OUTPUT BUT KEEPS CODE CLEAN!!!
        if removed_properties := (excluded_properties - self._pg_properties.keys()):
            labels = [n.get_label() for n in self.nodes]
            removed_properties = list(removed_properties)

            logger.warning(
                f"Excluded properties {removed_properties} have been removed from {labels}."
            )

        self._excluded_properties = excluded_properties

    @property
    def excluded_properties(self) -> Set[str]:
        """The properties which are excluded from the final mapping."""
        return self._excluded_properties

    @override
    def _is_prop_included(self, prop: str) -> bool:
        return super()._is_prop_included(prop) and prop not in self.excluded_properties


class NodeStructure(NodesStructure):
    """A structure whose mapping includes all properties defined by its associated node."""

    def __init__(
        self,
        node: type[models.Node],
        is_nested: bool,
        description_root: str | None = None,
        children: Mapping[str, Structure] = types.MappingProxyType({}),
        excluded_properties: Set[str] = frozenset(),
    ) -> None:
        """Initializes a node based structure in a tree.

        Args:
            node: The singular node which this structure represents and from which this
                structure's mapped properties are derived.
            is_nested: A flag indicating if this structure needs to be configured as a nested
                type within resulting mappings.
            description_root: The name which should prepend all descriptions within
                `_meta.descriptions`. This should only be defined for the root structure.
            children: All children structures which are nested within this one.
            excluded_properties: A set of property names which should be excluded when
                generating the mapping for this structure. By default, all properties are
                included.
        """
        super().__init__((node,), is_nested, description_root, children, excluded_properties)

    @property
    def node(self) -> type[models.Node]:
        """The node from which this structure's mappings are derived."""
        return self._nodes[0]


class NodesRequiredStructure(NodesStructureABC):
    """A structure whose mapping includes only required properties the dictionary nodes."""

    __slots__ = ("_required_properties",)

    def __init__(
        self,
        nodes: Sequence[type[models.Node]],
        is_nested: bool,
        description_root: str | None = None,
        additional_properties: Set[str] = frozenset(),
        children: Mapping[str, Structure] = types.MappingProxyType({}),
    ) -> None:
        """Initializes a node based structure in a tree.

        Args:
            nodes: All nodes which this structure represents. A set of ALL required properties
                associated with each node is used to map this structures associated
                elasticsearch properties.
            is_nested: A flag indicating if this structure needs to be configured as a nested
                type within resulting mappings.
            description_root: The name which should prepend all descriptions within
                `_meta.descriptions`. This should only be defined for the root structure.
            additional_properties: Any non-required properties which should be included in the
                output mapping.
            children: All children structures which are nested within this one.
        """
        super().__init__(nodes, is_nested, description_root, children)

        # Warn devs that there are old properties which should be removed from configured
        # additional properties.
        # !!!DOES NOT CHANGE OUTPUT BUT KEEPS CODE CLEAN!!!
        if removed_properties := (additional_properties - self._pg_properties.keys()):
            labels = [n.get_label() for n in self.nodes]
            removed_properties = list(removed_properties)

            logger.warning(
                f"Additional properties {removed_properties} have been removed from {labels}."
            )

        self._required_properties = (
            frozenset(
                prop
                for node in nodes
                for prop in node._dictionary.get("required", ())  # type: ignore
            )
            | additional_properties
        )

    @override
    def _is_prop_included(self, prop: str) -> bool:
        return super()._is_prop_included(prop) and prop in self._required_properties


class NodeRequiredStructure(NodesRequiredStructure):
    """A structure whose mapping includes only required properties the dictionary node."""

    def __init__(
        self,
        node: type[models.Node],
        is_nested: bool,
        description_root: str | None = None,
        additional_properties: Set[str] = frozenset(),
        children: Mapping[str, Structure] = types.MappingProxyType({}),
    ) -> None:
        """Initializes a node based structure in a tree.

        Args:
            node: The singular node which this structure represents and from which this
                structure's mapped properties are derived.
            is_nested: A flag indicating if this structure needs to be configured as a nested
                type within resulting mappings.
            description_root: The name which should prepend all descriptions within
                `_meta.descriptions`. This should only be defined for the root structure.
            additional_properties: Any non-required properties which should be included in the
                output mapping.
            children: All children structures which are nested within this one.
        """
        super().__init__((node,), is_nested, description_root, additional_properties, children)

    @property
    def node(self) -> type[models.Node]:
        """The node from which this structure's mappings are derived."""
        return self._nodes[0]


# COMMON STRUCTURES USED WITHIN OTHER STRUCTURES.
_COMMON_FILE_NODES = tuple(_get_nodes_by_category("index_file", "data_file"))
_ANALYSIS_FILE_NODES = tuple(_get_nodes_by_category("analysis"))

_ANNOTATIONS = NodeStructure(node=models.Annotation, is_nested=True)
_CENTER = NodeStructure(node=models.Center, is_nested=False)
_IO_FILE = NodesStructure(nodes=_COMMON_FILE_NODES, is_nested=True)
_PROJECT = NodeStructure(
    node=models.Project,
    is_nested=False,
    excluded_properties=frozenset(
        {
            "code",
            "release_requested",
            "awg_review",
            "is_legacy",
            "in_review",
            "submission_enabled",
            "request_submission",
        }
    ),
    children=dict(program=NodeStructure(node=models.Program, is_nested=False)),
)

_CASE = NodeStructure(
    node=models.Case,
    is_nested=True,
    children=dict(
        annotations=_ANNOTATIONS,
        demographic=NodeStructure(node=models.Demographic, is_nested=False),
        diagnoses=NodeStructure(
            node=models.Diagnosis,
            is_nested=True,
            children=dict(
                annotations=_ANNOTATIONS,
                pathology_details=NodeStructure(node=models.PathologyDetail, is_nested=True),
                treatments=NodeStructure(node=models.Treatment, is_nested=True),
            ),
        ),
        exposures=NodeStructure(node=models.Exposure, is_nested=True),
        family_histories=NodeStructure(node=models.FamilyHistory, is_nested=True),
        follow_ups=NodeStructure(
            node=models.FollowUp,
            is_nested=True,
            children=dict(
                molecular_tests=NodeStructure(node=models.MolecularTest, is_nested=True),
                other_clinical_attributes=NodeStructure(
                    node=models.OtherClinicalAttribute, is_nested=True
                ),
            ),
        ),
        project=_PROJECT,
        samples=NodeStructure(
            node=models.Sample,
            is_nested=True,
            children=dict(
                annotations=_ANNOTATIONS,
                portions=NodeStructure(
                    node=models.Portion,
                    is_nested=True,
                    children=dict(
                        analytes=NodeStructure(
                            node=models.Analyte,
                            is_nested=True,
                            children=dict(
                                annotations=_ANNOTATIONS,
                                aliquots=NodeStructure(
                                    node=models.Aliquot,
                                    is_nested=True,
                                    children=dict(annotations=_ANNOTATIONS, center=_CENTER),
                                ),
                            ),
                        ),
                        annotations=_ANNOTATIONS,
                        center=_CENTER,
                        slides=NodeStructure(
                            node=models.Slide,
                            is_nested=True,
                            children=dict(annotations=_ANNOTATIONS),
                        ),
                    ),
                ),
            ),
        ),
        tissue_source_site=NodeStructure(node=models.TissueSourceSite, is_nested=False),
    ),
)
_FILE = NodesStructure(
    nodes=(models.File, *_COMMON_FILE_NODES),
    is_nested=True,
    children=dict(
        analysis=NodesStructure(
            nodes=_ANALYSIS_FILE_NODES,
            is_nested=False,
            children=dict(
                input_files=_IO_FILE,
                metadata=Structure(
                    is_nested=False,
                    children=dict(
                        read_groups=NodeStructure(
                            node=models.ReadGroup,
                            is_nested=True,
                            children=dict(
                                read_group_qcs=NodeStructure(
                                    node=models.ReadGroupQc, is_nested=True
                                )
                            ),
                        )
                    ),
                ),
            ),
        ),
        archive=NodeStructure(node=models.Archive, is_nested=False),
        center=_CENTER,
        downstream_analyses=NodesStructure(
            nodes=_ANALYSIS_FILE_NODES,
            is_nested=True,
            children=dict(output_files=_IO_FILE),
        ),
        index_files=NodesStructure(nodes=(models.File, *_COMMON_FILE_NODES), is_nested=True),
        metadata_files=NodeStructure(node=models.File, is_nested=True),
    ),
)
_CORE_CASE = NodeRequiredStructure(
    node=models.Case,
    is_nested=True,
    additional_properties=frozenset(
        {"consent_type", "days_to_consent", "index_date", "lost_to_followup", "state"}
    ),
    children=dict(
        demographic=NodeRequiredStructure(
            node=models.Demographic,
            is_nested=False,
            additional_properties=frozenset(
                {
                    "age_at_index",
                    "age_is_obfuscated",
                    "cause_of_death",
                    "days_to_birth",
                    "days_to_death",
                    "state",
                    "year_of_birth",
                    "year_of_death",
                }
            ),
        ),
        diagnoses=NodeRequiredStructure(
            node=models.Diagnosis,
            is_nested=True,
            additional_properties=frozenset(
                {
                    "ajcc_clinical_m",
                    "ajcc_clinical_n",
                    "ajcc_clinical_stage",
                    "ajcc_clinical_t",
                    "ajcc_pathologic_m",
                    "ajcc_pathologic_n",
                    "ajcc_pathologic_stage",
                    "ajcc_pathologic_t",
                    "ajcc_staging_system_edition",
                    "ann_arbor_b_symptoms",
                    "ann_arbor_clinical_stage",
                    "ann_arbor_extranodal_involvement",
                    "ann_arbor_pathologic_stage",
                    "burkitt_lymphoma_clinical_variant",
                    "classification_of_tumor",
                    "cog_renal_stage",
                    "days_to_diagnosis",
                    "days_to_last_follow_up",
                    "days_to_last_known_disease_status",
                    "days_to_recurrence",
                    "esophageal_columnar_dysplasia_degree",
                    "esophageal_columnar_metaplasia_present",
                    "figo_stage",
                    "figo_staging_edition_year",
                    "gastric_esophageal_junction_involvement",
                    "goblet_cells_columnar_mucosa_present",
                    "icd_10_code",
                    "igcccg_stage",
                    "inss_stage",
                    "international_prognostic_index",
                    "iss_stage",
                    "last_known_disease_status",
                    "laterality",
                    "masaoka_stage",
                    "metastasis_at_diagnosis",
                    "method_of_diagnosis",
                    "primary_gleason_grade",
                    "prior_malignancy",
                    "prior_treatment",
                    "progression_or_recurrence",
                    "residual_disease",
                    "secondary_gleason_grade",
                    "state",
                    "synchronous_malignancy",
                    "tumor_grade",
                    "year_of_diagnosis",
                }
            ),
            children=dict(
                pathology_details=NodeRequiredStructure(
                    node=models.PathologyDetail,
                    is_nested=True,
                    additional_properties=frozenset(
                        {
                            "anaplasia_present",
                            "anaplasia_present_type",
                            "bone_marrow_malignant_cells",
                            "breslow_thickness",
                            "circumferential_resection_margin",
                            "columnar_mucosa_present",
                            "dysplasia_degree",
                            "dysplasia_type",
                            "greatest_tumor_dimension",
                            "gross_tumor_weight",
                            "largest_extrapelvic_peritoneal_focus",
                            "lymph_node_involved_site",
                            "lymph_node_involvement",
                            "lymph_nodes_positive",
                            "lymph_nodes_tested",
                            "lymphatic_invasion_present",
                            "margin_status",
                            "metaplasia_present",
                            "morphologic_architectural_pattern",
                            "non_nodal_regional_disease",
                            "non_nodal_tumor_deposits",
                            "number_proliferating_cells",
                            "percent_tumor_invasion",
                            "perineural_invasion_present",
                            "peripancreatic_lymph_nodes_positive",
                            "peripancreatic_lymph_nodes_tested",
                            "prostatic_chips_positive_count",
                            "prostatic_chips_total_count",
                            "prostatic_involvement_percent",
                            "state",
                            "transglottic_extension",
                            "tumor_largest_dimension_diameter",
                            "vascular_invasion_present",
                            "vascular_invasion_type",
                        }
                    ),
                ),
                treatments=NodeRequiredStructure(
                    node=models.Treatment,
                    is_nested=True,
                    additional_properties=frozenset(
                        {
                            "chemo_concurrent_to_radiation",
                            "days_to_treatment_end",
                            "days_to_treatment_start",
                            "initial_disease_status",
                            "number_of_cycles",
                            "regimen_or_line_of_therapy",
                            "state",
                            "therapeutic_agents",
                            "treatment_dose",
                            "treatment_frequency",
                            "treatment_intent_type",
                            "treatment_or_therapy",
                            "treatment_outcome",
                            "treatment_type",
                        }
                    ),
                ),
            ),
        ),
        exposures=NodeRequiredStructure(
            node=models.Exposure,
            is_nested=True,
            additional_properties=frozenset(
                {
                    "alcohol_days_per_week",
                    "alcohol_history",
                    "alcohol_intensity",
                    "cigarettes_per_day",
                    "pack_years_smoked",
                    "state",
                    "tobacco_smoking_onset_year",
                    "tobacco_smoking_quit_year",
                    "tobacco_smoking_status",
                }
            ),
        ),
        family_histories=NodeRequiredStructure(
            node=models.FamilyHistory,
            is_nested=True,
            additional_properties=frozenset(
                {
                    "relationship_age_at_diagnosis",
                    "relationship_primary_diagnosis",
                    "relationship_type",
                    "relative_with_cancer_history",
                    "state",
                }
            ),
        ),
        follow_ups=NodeRequiredStructure(
            node=models.FollowUp,
            is_nested=True,
            children=dict(
                molecular_tests=NodeRequiredStructure(
                    node=models.MolecularTest, is_nested=True
                ),
                other_clinical_attributes=NodeRequiredStructure(
                    node=models.OtherClinicalAttribute, is_nested=True
                ),
            ),
        ),
        project=_PROJECT,
        samples=NodeRequiredStructure(
            node=models.Sample,
            is_nested=True,
            additional_properties=frozenset({"sample_type"}),
            children=dict(
                portions=NodeRequiredStructure(
                    node=models.Portion,
                    is_nested=True,
                    children=dict(
                        analytes=NodeRequiredStructure(
                            node=models.Analyte,
                            is_nested=True,
                            children=dict(
                                aliquots=NodeRequiredStructure(
                                    node=models.Aliquot, is_nested=True
                                )
                            ),
                        ),
                        slides=NodeRequiredStructure(node=models.Slide, is_nested=True),
                    ),
                ),
            ),
        ),
        tissue_source_site=NodeRequiredStructure(
            node=models.TissueSourceSite,
            is_nested=False,
            additional_properties=frozenset({"bcr_id", "code", "name", "project"}),
        ),
    ),
)
_occurrence_structure = functools.partial(_to_occurrence_structure, _CORE_CASE)
_case_structure = functools.partial(_to_case_structure, _CORE_CASE)
_EMPTY = Structure(is_nested=False)

# FINAL GRAPH STRUCTURES.
ANNOTATION = NodeStructure(
    node=_ANNOTATIONS.node,
    is_nested=False,
    description_root="annotations",
    excluded_properties=_ANNOTATIONS.excluded_properties | frozenset({"creator"}),
    children={
        "project": _PROJECT,
        **_ANNOTATIONS.children,
    },
)
CASE = NodeStructure(
    node=_CASE.node,
    is_nested=False,
    description_root="cases",
    excluded_properties=_CASE.excluded_properties,
    children={"files": _FILE, **_CASE.children},
)
FILE = NodesStructure(
    nodes=_FILE.nodes,
    is_nested=False,
    description_root="files",
    excluded_properties=_FILE.excluded_properties,
    children={"cases": _CASE, "annotations": _ANNOTATIONS, **_FILE.children},
)
PROJECT = NodeStructure(
    node=_PROJECT.node,
    is_nested=False,
    description_root="projects",
    excluded_properties=_PROJECT.excluded_properties,
    children=_PROJECT.children,
)

STRUCTURES = types.MappingProxyType(
    {
        constants.Index.ANNOTATION: ANNOTATION,
        constants.Index.CASE: CASE,
        constants.Index.FILE: FILE,
        constants.Index.PROJECT: PROJECT,
        constants.Index.CASE_CENTRIC: CASE,
        constants.Index.CNV_CENTRIC: _occurrence_structure("cnvs"),
        constants.Index.CNV_OCCURRENCE_CENTRIC: _case_structure("cnv_occurrences"),
        constants.Index.GENE_CENTRIC: _case_structure("genes", is_nested=True),
        constants.Index.SEGMENT_CNV_CENTRIC: _occurrence_structure("segment_cnvs"),
        constants.Index.SEGMENT_CNV_OCCURRENCE_CENTRIC: _case_structure(
            "segment_cnv_occurrences"
        ),
        constants.Index.SSM_CENTRIC: _occurrence_structure("ssms"),
        constants.Index.SSM_OCCURRENCE_CENTRIC: _case_structure("ssm_occurrences"),
    }
)
"""A mapping of the indices to their associated graph structures."""
