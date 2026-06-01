"""A module for managing the logic around generating our index mappings."""

from collections.abc import Mapping, Set
from typing import Any

import mergedeep

from gdcmodels import constants
from gdcmodels.sync.overlays import autocomplete, graph, headers, static


def _apply_normalizer(excluded: Set[str], mapping: Mapping[str, Any]) -> None:
    """Applies the clinical normalizer to all keyword properties except those excluded.

    Args:
        excluded: The properties which need to be excluded from having the clinical normalizer
            applied to them.
        mapping: The mapping which needs to have the normalized applied to it.
    """
    for prop, details in mapping["properties"].items():
        if "properties" in details:
            _apply_normalizer(excluded, details)
        elif details.get("type") == "keyword" and prop not in excluded:
            details["normalizer"] = "clinical_normalizer"


def sync(index: constants.Index) -> Mapping[str, Any]:
    """Synchronizes the index mapping with all of its configured overlays.

    Args:
        index: The index whose latest mappings should be loaded.

    Returns:
        The mapping for the given index with all of the latest overlays applied.
    """
    mapping = mergedeep.merge(
        {},
        autocomplete.MAPPINGS[index],
        graph.MAPPINGS[index],
        headers.MAPPINGS[index],
        static.MAPPINGS[index],
        strategy=mergedeep.Strategy.ADDITIVE,
    )

    _apply_normalizer(index.unnormalized_properties, mapping)

    return mapping
