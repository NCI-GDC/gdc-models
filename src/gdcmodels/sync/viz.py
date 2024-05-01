"""Manage the sync of the viz indices."""

import types
from typing import Any, Iterable, Mapping, Tuple

import gdcmodels
from gdcmodels import esmodels
from gdcmodels.sync import common


def _get_case_properties(case_properties: esmodels.Properties) -> esmodels.Properties:
    ignore_keys = frozenset({"case_autocomplete"})
    result: esmodels.Properties = {}
    items: Iterable[Tuple[str, esmodels.Property]] = (
        (n, p) for n, p in case_properties.items() if n not in ignore_keys and "analyzer" not in p
    )

    for name, property in items:
        if "properties" in property:
            result.setdefault(name, {})["properties"] = _get_case_properties(
                property["properties"]
            )
        if "type" in property:
            result.setdefault(name, {})["type"] = property["type"]

    return result


class CaseCentricSynchronizer(common.Synchronizer):
    def sync(self, mappings: esmodels.ESMapping, settings: Mapping[str, Any]) -> common.Export:
        # force a new load w/ get_es_models of graph/case index in case it was also
        # updated in this run.
        graph_mappings = gdcmodels.get_es_models(vestigial_included=True)["gdc_from_graph"][
            "case"
        ].mappings
        graph_mappings = {"properties": _get_case_properties(graph_mappings["properties"])}

        return common.apply_defaults(mappings, graph_mappings), settings


_SYNCHRONIZERS = {
    "case_centric": (
        common.DefaultMappingsSynchronizer(),
        common.DefaultSettingsSynchronizer(),
        CaseCentricSynchronizer(),
        common.DefaultNormalizerSynchronizer(),
    ),
    "default": (
        common.DefaultMappingsSynchronizer(),
        common.DefaultSettingsSynchronizer(),
        common.DefaultNormalizerSynchronizer(),
    ),
}


SYNCHRONIZERS = types.MappingProxyType(
    {
        i: types.MappingProxyType(
            {d: common.CompositeSynchronizer(_SYNCHRONIZERS.get(d, _SYNCHRONIZERS["default"]))}
        )
        for i, d in esmodels.VIZ_INDICES
    }
)
