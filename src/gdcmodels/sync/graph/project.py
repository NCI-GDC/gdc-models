from typing import Optional

from gdcmodels import esmodels
from gdcmodels.sync.graph import common


class Synchronizer(common.GraphSynchronizer):
    __slots__ = ("_projects", "_summaries")

    def __init__(
        self,
        projects: Optional[common.ProjectProperties] = None,
        summaries: Optional[common.SummaryProperties] = None,
        gdc_dictionary: Optional[common.GDCDictionary] = None,
    ) -> None:
        super().__init__(gdc_dictionary)

        self._projects = projects or common.ProjectProperties()
        self._summaries = summaries or common.SummaryProperties()

    def _get_summary(self) -> esmodels.Property:
        properties = self._summaries.load_properties()
        properties["case_count"] = common.ESProperty.long()
        properties["data_categories"]["properties"]["case_count"] = common.ESProperty().long()
        properties["experimental_strategies"]["properties"][
            "case_count"
        ] = common.ESProperty.long()

        return {"properties": properties}

    def _load_mapping(self) -> esmodels.ESMapping:
        mapping = esmodels.ESMapping(
            properties={**self._projects.load_properties(), "summary": self._get_summary()}
        )

        del mapping["properties"]["code"]

        self._add_autocomplete(
            mapping,
            "project_autocomplete",
            ("project_id", "disease_type", "name", "primary_site"),
        )

        return mapping


SYNCHRONIZER = common.get_final_synchronizer(Synchronizer())
