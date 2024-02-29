import types
from typing import Mapping

import more_itertools

import gdcmodels
from gdcmodels.export import common


class Exporter(common.Exporter):
    def export_mapping(self) -> gdcmodels.ESMapping:
        raise NotImplementedError()  # Temporary will be implemented in next PR.


EXPORTERS: Mapping[str, Mapping[str, common.Exporter]] = types.MappingProxyType(
    more_itertools.map_reduce(
        gdcmodels.GRAPH_INDICES,
        keyfunc=lambda t: t[0],
        valuefunc=lambda t: t[1],
        reducefunc=lambda ds: types.MappingProxyType({d: Exporter() for d in ds}),
    )
)
