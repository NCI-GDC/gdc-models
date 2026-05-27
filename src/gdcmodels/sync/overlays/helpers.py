from collections.abc import Callable, Mapping
from typing import Any

from gdcmodels import constants, extraction_utils


class LazyLoader(dict[constants.Index, Mapping[str, Any]]):
    def __init__(self, loader: Callable[[constants.Index], Mapping[str, Any]]) -> None:
        super().__init__()

        self._loader = loader

    def __missing__(self, key: constants.Index) -> Mapping[str, Any]:
        self[key] = self._loader(key)

        return self[key]


def _load_yaml(data: bytes) -> Mapping[str, Any]:
    def copy(mappings: Mapping[str, Any]) -> Mapping[str, Any]:
        return {k: copy(v) if isinstance(v, Mapping) else v for k, v in mappings.items()}

    return copy(extraction_utils.load_yaml(data))


class LazyYAMLLoader(dict[constants.Index, Mapping[str, Any]]):
    def __init__(self, overlay: str) -> None:
        super().__init__()

        self._overlay = overlay

    def __missing__(self, key: constants.Index) -> Mapping[str, Any]:
        resource = key.overlay_file(self._overlay)
        print(f"LOADING: {key}")
        self[key] = _load_yaml(resource.read_bytes())

        return self[key]
