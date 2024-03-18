from typing import Optional

from gdcmodels import esmodels
from gdcmodels.sync.graph import common


class Synchronizer(common.GraphSynchronizer):
    __slots__ = ("_cases", "_files")

    def __init__(
        self,
        cases: Optional[common.CaseProperties] = None,
        files: Optional[common.FileProperties] = None,
        gdc_dictionary: Optional[common.GDCDictionary] = None,
    ) -> None:
        super().__init__(gdc_dictionary)

        self._cases = cases or common.CaseProperties()
        self._files = files or common.FileProperties()

    def _get_file_properties(self) -> common.NestedDict:
        properties = self._files.load_properties()

        del properties["annotations"]
        del properties["associated_entities"]

        return properties

    def _load_mapping(self) -> esmodels.ESMapping:
        mapping: esmodels.ESMapping = {
            "properties": {
                **self._cases.load_properties(),
                "files": esmodels.Property(properties=self._get_file_properties(), type="nested"),
            }
        }

        self._add_autocomplete(
            mapping,
            "case_autocomplete",
            (
                "case_id",
                "disease_type",
                "primary_site",
                "project.disease_type",
                "project.intended_release_date",
                "project.primary_site",
                "project.project_id",
                "samples.portions.analytes.aliquots.aliquot_id",
                "samples.portions.analytes.aliquots.submitter_id",
                "samples.portions.analytes.analyte_id",
                "samples.portions.analytes.submitter_id",
                "samples.portions.portion_id",
                "samples.portions.submitter_id",
                "samples.portions.slides.slide_id",
                "samples.portions.slides.submitter_id",
                "samples.sample_id",
                "samples.submitter_id",
                "submitter_id",
            ),
        )

        return mapping


SYNCHRONIZER = common.get_final_synchronizer(Synchronizer())
