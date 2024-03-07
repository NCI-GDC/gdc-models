"""Manage the export of the viz indices."""

import sys
import types

from gdcmodels import esmodels
from gdcmodels.export import common

if sys.version_info < (3, 9):
    import importlib_resources as resources
    from importlib_resources import abc
else:
    from importlib import abc, resources


VIZ_EXPORTERS = (
    common.DefaultMappingsExporter(),
    common.DefaultSettingsExporter(),
    common.DefaultNormalizerExporter(),
)


EXPORTERS = types.MappingProxyType(
    {
        i: types.MappingProxyType({d: common.CompositeExporter(VIZ_EXPORTERS)})
        for i, d in esmodels.VIZ_INDICES
    }
)
