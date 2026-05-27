from collections.abc import Mapping
from typing import Any

from gdcmodels import constants
from gdcmodels.sync.overlays import helpers

__all__ = ("MAPPINGS",)

MAPPINGS: Mapping[constants.Index, Mapping[str, Any]] = helpers.LazyYAMLLoader(
    overlay="static"
)
