import abc
import functools
from typing import Any, Container, DefaultDict, Iterable, Mapping, Optional, Tuple, TypeVar, cast

import gdcdictionary
from gdcdatamodel2 import models
from typing_extensions import Protocol, TypedDict

from gdcmodels import esmodels
from gdcmodels.sync import common

TMapping = TypeVar("TMapping", bound=Mapping[str, Any])


class NestedDict(DefaultDict[str, Any]):
    """A default dictionary whose values default to a nested instance of itself."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(NestedDict, **kwargs)

    @staticmethod
    def as_dict(mapping: TMapping) -> TMapping:
        """Make a copy of the given mapping and insures all values are a standard dict.

        Args:
            mapping: The mapping with mixed types of dictionaries.

        Returns:
            A copy of the mapping and any sub-mappings contained all constructed with
            standard dictionaries.
        """
        return cast(
            TMapping,
            {k: NestedDict.as_dict(v) if isinstance(v, dict) else v for k, v in mapping.items()},
        )


class ESProperty:
    """A class for managing standard elasticsearch property values."""

    @classmethod
    def _get_prop(cls, es_type: str) -> NestedDict:
        """Build a property description with the given type.

        Args:
            es_type: The type of the property

        Returns:
            A property description with the given type.
        """
        mapping = NestedDict()
        mapping["type"] = es_type

        return mapping

    @classmethod
    def double(cls) -> NestedDict:
        """Get a double property description."""
        return cls._get_prop("double")

    @classmethod
    def long(cls) -> NestedDict:
        """Get a long property description."""
        return cls._get_prop("long")

    @classmethod
    def string(cls) -> NestedDict:
        """Get a keyword property description."""
        return cls._get_prop("keyword")

    @classmethod
    def translate_python(cls, types: Container[type]) -> NestedDict:
        """Translate the given set up python types to an elasticsearch property.

        Args:
            types: A set of types which represents the python data.

        Returns:
            A float or int property if they are contained in the given types. Otherwise,
            a string property is returned.
        """
        if float in types:
            return cls.double()
        elif int in types:
            return cls.long()
        else:
            return cls.string()


class GDCDictionary(Protocol):
    class Properties(TypedDict):
        properties: Mapping[str, dict]

    schema: Mapping[str, Properties]


class DescriptionsSynchronizer(common.Synchronizer):
    def __init__(
        self,
        gdc_dictionary: Optional[GDCDictionary] = None,
    ) -> None:
        self._gdc_dictionary = gdc_dictionary or gdcdictionary.gdcdictionary

    def _load_descriptions_from(
        self, node: models.Node, prefix: str, description_label: Optional[str] = None
    ) -> NestedDict:
        descriptions = NestedDict()
        description_label = description_label or node.get_label()
        properties = self._gdc_dictionary.schema[description_label]["properties"]

        for property in node.get_pg_properties().keys():
            definition = properties.get(property, {})
            description = definition.get("description") or definition.get("common", {}).get(
                "description"
            )

            descriptions[f"{prefix}.{property}"] = description

        return descriptions

    def _get_descriptions(self) -> dict:
        nodes = {
            models.Aliquot: (
                "annotations.aliquot",
                "cases.samples.aliquots",
                "cases.samples.analytes.aliquots",
                "cases.samples.portions.analytes.aliquots",
            ),
            models.Analyte: (
                "annotations.analyte",
                "cases.samples.analytes",
                "cases.samples.portions.analytes",
            ),
            models.Annotation: (
                "cases.annotations",
                "cases.samples.annotations",
                "cases.samples.portions.annotations",
                "cases.samples.portions.analytes.annotations",
                "cases.samples.portions.analytes.aliquots.annotations",
                "cases.samples.slides.annotations",
                "cases.samples.portions.slides.annotations",
                "cases.diagnoses.annotations",
                "files.annotations",
            ),
            models.Archive: ("files.archive",),
            models.Case: ("annotations.case", "cases.case", "files.cases"),
            models.Center: (
                "cases.samples.portions.center",
                "cases.samples.portions.analytes.aliquots.center",
                "files.center",
            ),
            models.DataFormat: ("files.data_format",),
            models.DataSubtype: ("files.data_type",),
            models.DataType: ("files.data_type.data_category",),
            models.Demographic: ("cases.demographic",),
            models.Diagnosis: ("cases.diagnoses",),
            models.ExperimentalStrategy: ("files.experimental_strategy",),
            models.Exposure: ("cases.exposures",),
            models.FamilyHistory: ("cases.family_histories",),
            models.File: (
                "annotations.file",
                "cases.files",
                "files.file",
                "files.metadata_files",
            ),
            models.FollowUp: ("cases.follow_ups",),
            models.MolecularTest: (
                "cases.diagnoses.molecular_tests",
                "cases.follow_ups.molecular_tests",
            ),
            models.PathologyDetail: ("cases.diagnoses.pathology_details",),
            models.Platform: ("files.platform",),
            models.Portion: ("annotations.portion", "cases.samples.portions"),
            models.Program: (
                "annotations.project.program",
                "cases.project.program",
                "projects.program",
            ),
            models.Project: ("annotations.project", "cases.project", "projects.project"),
            models.Sample: ("annotations.sample", "cases.samples"),
            models.Slide: (
                "annotations.slide",
                "cases.samples.slides",
                "cases.samples.portions.slides",
            ),
            models.Tag: ("files.tags",),
            models.TissueSourceSite: ("cases.tissue_source_site",),
            models.Treatment: ("cases.diagnoses.treatments",),
        }
        descriptions = NestedDict()

        for node, paths in nodes.items():
            for path in paths:
                descriptions.update(self._load_descriptions_from(node, path))

        descriptions.update(
            self._load_descriptions_from(models.File, "annotations.annotation", "annotation")
        )

        return NestedDict.as_dict(descriptions)

    def sync(self, mappings: esmodels.ESMapping, settings: Mapping[str, Any]) -> common.Export:
        mappings["_meta"] = {"descriptions": self._get_descriptions()}

        return mappings, settings


COMMON_SYNCHRONIZERS = (
    DescriptionsSynchronizer(),
    common.DefaultSettingsSynchronizer(),
    common.DefaultMappingsSynchronizer(),
    common.DefaultNormalizerSynchronizer(),
)


def get_final_synchronizer(synchronizer: common.Synchronizer) -> common.Synchronizer:
    return common.CompositeSynchronizer((synchronizer, *COMMON_SYNCHRONIZERS))


def apply_clinical_normalizer(mapping: NestedDict, paths: Iterable[str]) -> NestedDict:
    for path in paths:
        property = functools.reduce(lambda m, p: m["properties"][p], path.split("."), mapping)
        property["normalizer"] = "clinical_normalizer"

    return mapping


class GraphSynchronizer(common.Synchronizer, abc.ABC):
    __slots__ = ("_gdc_dictionary",)

    def __init__(
        self,
        gdc_dictionary: Optional[GDCDictionary] = None,
    ) -> None:
        self._gdc_dictionary = gdc_dictionary or gdcdictionary.gdcdictionary

    def _add_autocomplete(
        self, mapping: esmodels.ESMapping, name: str, copied_paths: Iterable[str]
    ) -> None:
        autocomplete = ESProperty.string()
        autocomplete["fields"]["analyzed"]["analyzer"] = "autocomplete_analyzed"
        autocomplete["fields"]["analyzed"]["search_analyzer"] = "lowercase_keyword"
        autocomplete["fields"]["analyzed"]["type"] = "text"
        autocomplete["fields"]["lowercase"]["analyzer"] = "lowercase_keyword"
        autocomplete["fields"]["lowercase"]["type"] = "text"
        autocomplete["fields"]["prefix"]["analyzer"] = "autocomplete_prefix"
        autocomplete["fields"]["prefix"]["search_analyzer"] = "lowercase_keyword"
        autocomplete["fields"]["prefix"]["type"] = "text"

        for path in copied_paths:
            property = cast(
                esmodels.Property,
                functools.reduce(
                    lambda m, p: m.get("properties", {}).get(p, {}), path.split("."), mapping
                ),
            )
            property["copy_to"] = [name]

        mapping["properties"][name] = cast(esmodels.Autocomplete, autocomplete)

    @abc.abstractmethod
    def _load_mapping(self) -> esmodels.ESMapping:
        raise NotImplementedError()

    def sync(self, mappings: esmodels.ESMapping, settings: Mapping[str, Any]) -> common.Export:
        mappings = self._load_mapping()
        mappings = NestedDict.as_dict(mappings)

        return mappings, settings


def _get_nodes_by_category(category: str) -> Iterable[models.Node]:
    return filter(lambda n: n._dictionary["category"] == category, models.Node.get_subclasses())


def _load_properties_from(
    node: models.Node,
    include_id: bool = True,
    excluded_fields: Container[str] = frozenset(
        ("project_id", "batch_id", "file_state", "curated_model_index")
    ),
) -> NestedDict:
    def is_included(property: Tuple[str, Container[type]]) -> bool:
        return property[0] not in excluded_fields

    properties = NestedDict()

    if include_id:
        properties[f"{node.get_label()}_id"] = ESProperty.string()

    for field, types in filter(is_included, node.get_pg_properties().items()):
        properties[field] = ESProperty.translate_python(types)

    if "submitter_id" in properties:
        properties["submitter_id"] = ESProperty.string()

    return properties


class ProjectProperties:
    def load_properties(self) -> esmodels.Properties:
        properties = _load_properties_from(
            models.Project,
            excluded_fields=frozenset(
                (
                    "release_requested",
                    "awg_review",
                    "is_legacy",
                    "in_review",
                    "submission_enabled",
                    "request_submission",
                )
            ),
        )
        properties["program"] = NestedDict(properties=_load_properties_from(models.Program))

        return properties


class AnnotationProperties:
    def load_properties(self) -> esmodels.Properties:
        properties = NestedDict(
            **{
                f: ESProperty.string()
                for f in (
                    "case_id",
                    "case_submitter_id",
                    "entity_type",
                    "entity_id",
                    "entity_submitter_id",
                )
            }
        )

        properties.update(_load_properties_from(models.Annotation))

        return properties


class SummaryProperties:
    def load_properties(self) -> NestedDict:
        properties = NestedDict()
        properties["file_count"] = ESProperty.long()
        properties["file_size"] = ESProperty.long()
        properties["experimental_strategies"] = NestedDict(
            properties=NestedDict(
                experimental_strategy=ESProperty.string(),
                file_count=ESProperty.long(),
            ),
            type="nested",
        )
        properties["data_categories"] = NestedDict(
            properties=NestedDict(
                data_category=ESProperty.string(),
                file_count=ESProperty.long(),
            ),
            type="nested",
        )

        return properties


class CaseProperties:
    __slots__ = ("_annotations", "_projects", "_summaries")

    def __init__(
        self,
        annotation: Optional[AnnotationProperties] = None,
        projects: Optional[ProjectProperties] = None,
        summaries: Optional[SummaryProperties] = None,
    ) -> None:
        self._annotations = annotation or AnnotationProperties()
        self._projects = projects or ProjectProperties()
        self._summaries = summaries or SummaryProperties()

    def _get_project(self) -> NestedDict:
        mapping = NestedDict(properties=self._projects.load_properties())

        del mapping["properties"]["code"]

        return mapping

    def _get_aliquots(self) -> NestedDict:
        mapping = NestedDict(
            properties=_load_properties_from(models.Aliquot),
            type="nested",
        )
        properties = mapping["properties"]
        properties["annotations"]["properties"] = self._annotations.load_properties()
        properties["annotations"]["type"] = "nested"
        properties["center"] = NestedDict(properties=_load_properties_from(models.Center))

        return mapping

    def _get_analytes(self) -> NestedDict:
        mapping = NestedDict(
            properties=_load_properties_from(models.Analyte),
            type="nested",
        )
        properties = mapping["properties"]
        properties["annotations"]["properties"] = self._annotations.load_properties()
        properties["annotations"]["type"] = "nested"
        properties["aliquots"] = self._get_aliquots()

        return mapping

    def _get_slides(self) -> NestedDict:
        mapping = NestedDict(
            properties=_load_properties_from(models.Slide),
            type="nested",
        )
        properties = mapping["properties"]
        properties["annotations"]["properties"] = self._annotations.load_properties()
        properties["annotations"]["type"] = "nested"

        return mapping

    def _get_portions(self) -> NestedDict:
        mapping = NestedDict(
            properties=_load_properties_from(models.Portion),
            type="nested",
        )
        properties = mapping["properties"]
        properties["analytes"] = self._get_analytes()
        properties["annotations"]["properties"] = self._annotations.load_properties()
        properties["annotations"]["type"] = "nested"
        properties["center"] = NestedDict(properties=_load_properties_from(models.Center))
        properties["slides"] = self._get_slides()

        return mapping

    def _get_samples(self) -> NestedDict:
        mapping = NestedDict(
            properties=_load_properties_from(models.Sample),
            type="nested",
        )
        properties = mapping["properties"]
        properties["annotations"]["properties"] = self._annotations.load_properties()
        properties["annotations"]["type"] = "nested"
        properties["portions"] = self._get_portions()

        # TODO: REMOVE W/ MAPPING UPDATE
        properties["specimen_type"] = ESProperty.string()

        return mapping

    def _get_diagnoses(self) -> NestedDict:
        mapping = NestedDict(
            properties=_load_properties_from(models.Diagnosis),
            type="nested",
        )
        properties = mapping["properties"]
        properties["annotations"]["properties"] = self._annotations.load_properties()
        properties["annotations"]["type"] = "nested"
        properties["pathology_details"] = NestedDict(
            properties=_load_properties_from(models.PathologyDetail),
            type="nested",
        )
        properties["treatments"] = NestedDict(
            properties=_load_properties_from(models.Treatment),
            type="nested",
        )

        return mapping

    def _get_follow_ups(self) -> NestedDict:
        mapping = NestedDict(
            properties=_load_properties_from(models.FollowUp),
            type="nested",
        )
        properties = mapping["properties"]
        properties["molecular_tests"] = NestedDict(
            properties=_load_properties_from(models.MolecularTest),
            type="nested",
        )

        return mapping

    def load_properties(self) -> NestedDict:
        properties = _load_properties_from(models.Case)
        properties["annotations"]["properties"] = self._annotations.load_properties()
        properties["annotations"]["type"] = "nested"
        properties["project"] = self._get_project()
        properties["tissue_source_site"] = NestedDict(
            properties=_load_properties_from(models.TissueSourceSite)
        )
        properties["samples"] = self._get_samples()
        properties["demographic"] = NestedDict(
            properties=_load_properties_from(models.Demographic)
        )
        properties["exposures"] = NestedDict(
            properties=_load_properties_from(models.Exposure),
            type="nested",
        )
        properties["diagnoses"] = self._get_diagnoses()
        properties["follow_ups"] = self._get_follow_ups()
        properties["family_histories"] = NestedDict(
            properties=_load_properties_from(models.FamilyHistory),
            type="nested",
        )
        properties["summary"]["properties"] = self._summaries.load_properties()

        # id summaries
        properties["sample_ids"] = ESProperty.string()
        properties["submitter_sample_ids"] = ESProperty.string()
        properties["portion_ids"] = ESProperty.string()
        properties["submitter_portion_ids"] = ESProperty.string()
        properties["analyte_ids"] = ESProperty.string()
        properties["submitter_analyte_ids"] = ESProperty.string()
        properties["aliquot_ids"] = ESProperty.string()
        properties["submitter_aliquot_ids"] = ESProperty.string()
        properties["slide_ids"] = ESProperty.string()
        properties["submitter_slide_ids"] = ESProperty.string()
        properties["diagnosis_ids"] = ESProperty.string()
        properties["submitter_diagnosis_ids"] = ESProperty.string()

        return properties


class FileProperties:
    __slots__ = ("_annotations",)

    def __init__(self, annotations: Optional[AnnotationProperties] = None) -> None:
        self._annotations = annotations or AnnotationProperties()

    def _get_associated_entities(self) -> NestedDict:
        properties = NestedDict(
            case_id=ESProperty.string(),
            entity_type=ESProperty.string(),
            entity_id=ESProperty.string(),
            entity_submitter_id=ESProperty.string(),
        )
        mapping = NestedDict(properties=properties, type="nested")

        return mapping

    def _get_metadata_files(self) -> NestedDict:
        properties = NestedDict(
            **_load_properties_from(models.File),
            data_category=ESProperty.string(),
            data_type=ESProperty.string(),
            data_format=ESProperty.string(),
            access=ESProperty.string(),
            type=ESProperty.string(),
        )
        mapping = NestedDict(properties=properties, type="nested")

        return mapping

    def _get_index_files(self) -> NestedDict:
        properties = self._load_file_properties()
        mapping = NestedDict(properties=properties, type="nested")

        return mapping

    def _get_data_category(self) -> NestedDict:
        properties = NestedDict(**_load_properties_from(models.DataType))
        mapping = NestedDict(properties=properties)

        return mapping

    def _load_file_properties(self) -> NestedDict:
        properties = _load_properties_from(models.File)
        file_nodes = (
            *_get_nodes_by_category("index_file"),
            *_get_nodes_by_category("data_file"),
        )

        for node in file_nodes:
            properties.update(_load_properties_from(node, include_id=False))

        properties["access"] = ESProperty.string()
        # TODO: REMOVE W/ MAPPING UPDATE
        properties["wgs_coverage"] = ESProperty.string()

        return properties

    def _get_io_files(self) -> NestedDict:
        file_nodes = (
            *_get_nodes_by_category("index_file"),
            *_get_nodes_by_category("data_file"),
        )
        mapping = NestedDict(type="nested")
        properties: NestedDict = mapping["properties"]

        for node in file_nodes:
            properties.update(_load_properties_from(node, include_id=False))

        properties["access"] = ESProperty.string()
        properties["file_id"] = ESProperty.string()
        # TODO: REMOVE W/ MAPPING UPDATE
        properties["wgs_coverage"] = ESProperty.string()

        return mapping

    def _get_read_group_qcs(self) -> NestedDict:
        properties = _load_properties_from(models.ReadGroupQc)
        mapping = NestedDict(type="nested", properties=properties)

        return mapping

    def _get_read_groups(self) -> NestedDict:
        properties = NestedDict(
            **_load_properties_from(models.ReadGroup),
            read_group_qcs=self._get_read_group_qcs(),
        )
        mapping = NestedDict(properties=properties, type="nested")

        return mapping

    def _get_metadata(self) -> NestedDict:
        properties = NestedDict(read_groups=self._get_read_groups())
        mapping = NestedDict(properties=properties)

        return mapping

    def _get_analysis(self) -> NestedDict:
        analysis_nodes = _get_nodes_by_category("analysis")
        mapping = NestedDict()
        properties = mapping["properties"]

        for node in analysis_nodes:
            properties.update(_load_properties_from(node, include_id=False))

        properties["analysis_id"] = ESProperty.string()
        properties["analysis_type"] = ESProperty.string()
        properties["input_files"] = self._get_io_files()
        properties["metadata"] = self._get_metadata()

        return mapping

    def _get_downstream_analyses(self) -> NestedDict:
        analysis_nodes = _get_nodes_by_category("analysis")
        mapping = NestedDict(type="nested")
        properties = mapping["properties"]

        for node in analysis_nodes:
            properties.update(_load_properties_from(node, include_id=False))

        properties["analysis_id"] = ESProperty.string()
        properties["analysis_type"] = ESProperty.string()
        properties["output_files"] = self._get_io_files()

        return mapping

    def load_properties(self) -> NestedDict:
        properties = self._load_file_properties()

        # Additional
        properties["acl"] = ESProperty.string()
        properties["platform"] = ESProperty.string()
        properties["tags"] = ESProperty.string()
        properties["data_format"] = ESProperty.string()
        properties["experimental_strategy"] = ESProperty.string()

        # Related Entities
        properties["archive"]["properties"] = _load_properties_from(models.Archive)
        properties["center"]["properties"] = _load_properties_from(models.Center)

        properties["analysis"] = self._get_analysis()
        properties["annotations"]["properties"] = self._annotations.load_properties()
        properties["annotations"]["type"] = "nested"
        properties["associated_entities"] = self._get_associated_entities()
        properties["downstream_analyses"] = self._get_downstream_analyses()
        properties["index_files"] = self._get_index_files()
        properties["metadata_files"] = self._get_metadata_files()

        # Set type of file
        properties["type"] = ESProperty.string()

        return properties
