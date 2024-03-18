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

    def _load_mapping(self) -> esmodels.ESMapping:
        mapping = esmodels.ESMapping(
            properties={
                **self._files.load_properties(),
                "cases": esmodels.Property(
                    properties=self._cases.load_properties(), type="nested"
                ),
            }
        )

        self._add_autocomplete(
            mapping,
            "file_autocomplete",
            (
                "data_category",
                "data_type",
                "experimental_strategy",
                "file_id",
                "file_name",
                "md5sum",
                "submitter_id",
            ),
        )

        return mapping


SYNCHRONIZER = common.get_final_synchronizer(Synchronizer())
