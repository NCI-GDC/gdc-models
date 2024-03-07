from typing import Optional

from gdcmodels import esmodels
from gdcmodels.export.graph import common


class Exporter(common.GraphExporter):
    __slots__ = ("_annotations", "_projects")

    def __init__(
        self,
        annotations: Optional[common.AnnotationProperties] = None,
        projects: Optional[common.ProjectProperties] = None,
        gdc_dictionary: Optional[common.GDCDictionary] = None,
    ) -> None:
        super().__init__(gdc_dictionary)

        self._annotations = annotations or common.AnnotationProperties()
        self._projects = projects or common.ProjectProperties()

    def _export_mapping(self) -> esmodels.ESMapping:
        mapping = esmodels.ESMapping(
            properties={
                **self._annotations.export_properties(),
                "project": esmodels.Property(properties=self._projects.export_properties()),
            }
        )

        self._add_autocomplete(mapping, "annotation_autocomplete", ("annotation_id",))

        del mapping["properties"]["creator"]

        return mapping


EXPORTER = common.CompositeExporter((Exporter(), *common.COMMON_EXPORTERS))
