"""Manage the sync of the graph indices."""

import types

from gdcmodels import esmodels
from gdcmodels.sync import common

SYNCHRONIZERS = types.MappingProxyType(
    {
        # TODO: sync graph data from data models next PR.
        "gdc_from_graph": types.MappingProxyType(
            {d: common.CompositeSynchronizer(synchronizers=()) for _, d in esmodels.GRAPH_INDICES}
        )
    }
)
