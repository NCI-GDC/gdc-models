from typing import Optional

from gdcmodels import esmodels
from gdcmodels.export.graph import common


class Exporter(common.GraphExporter):
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

    def _export_mapping(self) -> esmodels.ESMapping:
        mapping = esmodels.ESMapping(
            properties={
                **self._files.export_properties(),
                "cases": esmodels.Property(
                    properties=self._cases.export_properties(), type="nested"
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


EXPORTER = common.CompositeExporter((Exporter(), *common.COMMON_EXPORTERS))
