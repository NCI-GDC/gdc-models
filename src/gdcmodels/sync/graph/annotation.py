from typing import Optional

from gdcmodels import esmodels
from gdcmodels.sync.graph import common


class Synchronizer(common.GraphSynchronizer):
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

    def _load_mapping(self) -> esmodels.ESMapping:
        mapping = esmodels.ESMapping(
            properties={
                **self._annotations.load_properties(),
                "project": esmodels.Property(properties=self._projects.load_properties()),
            }
        )

        self._add_autocomplete(mapping, "annotation_autocomplete", ("annotation_id",))

        del mapping["properties"]["creator"]

        return mapping


SYNCHRONIZER = common.CompositeSynchronizer((Synchronizer(), *common.COMMON_SYNCHRONIZERS))
