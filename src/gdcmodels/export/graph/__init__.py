"""Manage the export of the graph indices."""

import types

from gdcmodels import esmodels
from gdcmodels.export import common

EXPORTERS = types.MappingProxyType(
    {
        # TODO: export graph data from data models next PR.
        "gdc_from_graph": types.MappingProxyType(
            {d: common.CompositeExporter(exporters=()) for _, d in esmodels.GRAPH_INDICES}
        )
    }
)
