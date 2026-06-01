from collections.abc import Mapping
from typing import Any

from gdcmodels import constants
from gdcmodels.sync.overlays import helpers
from gdcmodels.sync.overlays.graph import structures

__all__ = ("MAPPINGS",)

MAPPINGS: Mapping[constants.Index, Mapping[str, Any]] = helpers.LazyLoader(
    lambda index: structures.STRUCTURES[index].to_mapping(
        include_meta=False  # THIS WILL BE REMOVED IN LATER PR.
    )
)
