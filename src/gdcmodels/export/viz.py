import sys
import types

import gdcmodels
from gdcmodels import utils
from gdcmodels.export import common, normalizer

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources


class Exporter(common.Exporter):
    """An exporter for the viz indices.

    This normalizes the properties within the associated mappings file.
    """

    def __init__(self, mapping_path: str) -> None:
        self._mapping_path = resources.files(gdcmodels) / "es-models" / mapping_path

    def export_mapping(self) -> gdcmodels.ESMapping:
        mapping: gdcmodels.ESMapping = utils.load_yaml(self._mapping_path.read_bytes())

        return normalizer.normalize(mapping)


MAPPING_PATH = "{index}/mapping.yaml"
EXPORTERS = types.MappingProxyType(
    {
        i: types.MappingProxyType({d: Exporter(MAPPING_PATH.format(index=i))})
        for i, d in gdcmodels.VIZ_INDICES
    }
)
