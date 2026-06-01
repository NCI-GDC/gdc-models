"""A module for helper functionality to load the various overlays."""

from collections.abc import Callable, Mapping
from importlib import abc
from typing import Any

from gdcmodels import constants, extraction_utils


class LazyLoader(dict[constants.Index, Mapping[str, Any]]):
    """A mapping of indices to their overlay which are loaded lazily from a function."""

    def __init__(self, loader: Callable[[constants.Index], Mapping[str, Any]]) -> None:
        """Initializes the mapping.

        Args:
            loader: The functionality which should be called for the index in order to load a
                dynamic overlay when the index is access in this mapping.
        """
        super().__init__()

        self._loader = loader

    def __missing__(self, key: constants.Index) -> Mapping[str, Any]:
        self[key] = self._loader(key)

        return self[key]


def _load_yaml(resource: abc.Traversable) -> Mapping[str, Any]:
    """Loads the data from the raw yaml.

    NOTE: This function creates a copy of all the data which is loaded from the yaml. This is
    to ensure that anchors and their associated aliases are distinct objects in memory.
    Otherwise, editing one of the references edits ALL instances of said mapping which is not
    desired.

    Args:
        resource: The file resource representing the yaml data which needs to be loaded.

    Returns:
        A mapping containing all data loaded from the given resource.
    """

    def copy(mappings: Mapping[str, Any]) -> Mapping[str, Any]:
        return {k: copy(v) if isinstance(v, Mapping) else v for k, v in mappings.items()}

    return copy(extraction_utils.load_yaml(resource.read_bytes()))


class LazyYAMLLoader(dict[constants.Index, Mapping[str, Any]]):
    """A mapping of indices to their overlay which are loaded lazily from a YAML."""

    def __init__(self, overlay: str) -> None:
        """Initializes an the mapping.

        Args:
            overlay: The name of the overlay i.e. the name of the overlay module within
                `overlays`; this will be used to load the appropriate static yaml file
                contained in that module.
        """
        super().__init__()

        self._overlay = overlay

    def __missing__(self, key: constants.Index) -> Mapping[str, Any]:
        resource = key.overlay_file(self._overlay)
        self[key] = _load_yaml(resource)

        return self[key]
