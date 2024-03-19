"""Manage the sync of the viz indices."""

import types

from gdcmodels import esmodels
from gdcmodels.sync import common

_SYNCHRONIZER = common.CompositeSynchronizer(
    (
        common.DefaultMappingsSynchronizer(),
        common.DefaultSettingsSynchronizer(),
        common.DefaultNormalizerSynchronizer(),
    )
)


SYNCHRONIZERS = types.MappingProxyType(
    {i: types.MappingProxyType({d: _SYNCHRONIZER}) for i, d in esmodels.VIZ_INDICES}
)
