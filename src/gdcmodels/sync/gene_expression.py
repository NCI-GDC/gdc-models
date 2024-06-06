import types

from gdcmodels.sync import common

SYNCHRONIZERS = types.MappingProxyType(
    {
        "gene_expression": types.MappingProxyType(
            {
                "gene_expression": common.CompositeSynchronizer(
                    (
                        common.DefaultMappingsSynchronizer(),
                        common.DefaultSettingsSynchronizer(),
                        common.DefaultNormalizerSynchronizer(),
                    )
                )
            }
        )
    }
)
