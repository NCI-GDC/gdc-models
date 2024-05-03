"""Manage the sync of the viz indices."""

import types
from typing import Any, Iterable, Mapping, Tuple

import gdcmodels
from gdcmodels import esmodels
from gdcmodels.sync import common


def _get_case_properties(case_properties: esmodels.Properties) -> esmodels.Properties:
    """
    Build a bare-bones copy of the case properties.

    This drops such things as copy-to and normalizers and only preserves the structure
    of the properties and their associated type.

    Args:
        case_properties: The properties from the graph/case mapping to copy.

    Returns:
        A copy of the properties contained in the case_properties with only
        the structure of names and their associated type captured.
    """
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
        """
        Sync the graph/case mapping into the case centric mapping.

        This ensures that the case centric mapping is a superset of graph/case. This is
        required as the FE uses the fields available in graph/case to determine how to
        build several queries which are run against the case centric index in actuality.

        Args:
            mappings: The mappings associated with the model.
            settings: The settings associated with the model.

        Returns:
            An the same settings but an updated mapping w/ any new fields from the
            graph/case mapping.
        """
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
