import copy
import functools
import re
import sys
from typing import Callable, Iterable, Iterator, Optional, Protocol, Tuple, Union

import more_itertools

import gdcmodels
from gdcmodels import utils

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources


def _walk_mapping(
    mapping: Union[gdcmodels.ESMapping, gdcmodels.Property], path: str = "root"
) -> Iterator[Tuple[str, gdcmodels.Property]]:
    """Walk the mapping/property returning all paths with their associated properties.

    Args:
        mapping: The elasticsearch mapping or property to walk.
        path: The path which has been walked upto the current mapping or property.

    Yields:
        The path and its associated property definition.
    """
    for name, property in mapping.get("properties", {}).items():
        sub_path = f"{path}.{name}"
        yield sub_path, property
        yield from _walk_mapping(property, sub_path)


class ModelMapper:
    """This translates the model into elasticsearch mappings/settings.

    NOTE: Instances of this class should be instantiated via this module's `load_mapper`
    """

    __slots__ = ("_index_name", "_doc_type", "_index")

    def __init__(self, index_name: str, doc_type: str, index: gdcmodels.Index) -> None:
        self._index_name = index_name
        self._doc_type = doc_type
        self._index = index

    @property
    def mappings(self) -> gdcmodels.ESMapping:
        """The elasticsearch mappings associated with the model."""
        return self._index[self._doc_type]["_mapping"]

    @property
    def settings(self) -> dict:
        """The settings object for the elasticsearch index."""
        return self._index["_settings"]

    def select_mapping(
        self,
        doc_type: str,
        selector: Optional[Union[str, Callable[[Iterable[str]], Iterable[str]]]] = None,
    ) -> Union[gdcmodels.ESMapping, gdcmodels.Property]:
        """Select a sub-mapping or the entire mapping based on the doc_type.

        Using the given doc_type any property within this mapping with that name will
        have it's property definition returned. If multiple exist a selector should be
        insure that the selection is deterministic.

        Example:
            # Just return the very first path:
            mapper.select_mapping("annotation", selector=more_itertools.first)
            # Only select root.(...).cnv.(...).observation:
            mapper.select_mapping("observation", selector="cnv")

        Args:
            doc_type: name of the property (or the index itself) which should be
                selected.
            selector: The selector can either be a callable which filters the possible
                paths to the desired property definition or the name of a parent
                property that must be within the desired properties path.

        Returns:
            The entire mapping definition or the property details associated with the
            given doc_type.
        """
        if self._doc_type in [doc_type, f"{doc_type}_centric"]:
            return self.mappings

        mappings = {p: m for p, m in _walk_mapping(self.mappings) if p.endswith(f".{doc_type}")}

        if isinstance(selector, str):
            pattern = re.compile(rf"\.{selector}\.")
            paths: Iterable[str] = filter(pattern.search, mappings.keys())
        elif callable(selector):
            paths = selector(mappings.keys())
        else:
            paths = mappings.keys()

        selected_path = more_itertools.one(paths)

        return mappings[selected_path]


class SettingsManager(Protocol):
    def update_settings(self, settings: dict) -> None:
        """Update the settings with any default settings."""
        pass


class DefaultSettingsManager(SettingsManager):
    def __init__(self) -> None:
        self._default_settings = utils.load_yaml(
            resources.files(gdcmodels).joinpath("common/settings.yaml").read_bytes()
        )

    def update_settings(self, settings: dict) -> None:
        utils.apply_defaults(settings, self._default_settings)


@functools.lru_cache(None)
def _load_models(vestigial_included: bool) -> gdcmodels.Models:
    """Cache copy of the loaded models; see `gdcmodels.get_es_models`."""
    return gdcmodels.get_es_models(vestigial_included)


def _load_index(index_name: str, vestigial_included: bool) -> gdcmodels.Index:
    """Load the requested index from the models.

    Args:
        index_name: The name of the desired index.
        vestigial_included: Indicates if the vestigial properties should be loaded with
            the mapping.

    Returns:
        The index as its represented in the models.
    """
    models = _load_models(vestigial_included)
    index = models.get(index_name)

    if not index:
        raise ValueError(f"No model associated with {index_name}.")

    return copy.deepcopy(index)


def load_mapper(
    index_name: str,
    doc_type: Optional[str] = None,
    vestigial_included: bool = True,
    settings: Optional[SettingsManager] = None,
) -> ModelMapper:
    """Load the requested model into a mapper object to interface with elasticsearch.

    Args:
        index_name: The name of the index to load.
        doc_type: The name of the doc_type associated w/ the index to load. Defaults to
            the name of the index if none is provided.
        vestigial_included: Indicates if the vestigial properties should be loaded with
            the mapping.
        settings: A settings manager for standardizing/defaulting setting
            configurations.

    Returns:
        The ModelMapper representation of the requested model.
    """
    doc_type = doc_type or index_name
    settings = settings or DefaultSettingsManager()
    index = _load_index(index_name, vestigial_included)

    if doc_type not in index:
        raise ValueError(f"No mapping associated with {index_name}/{doc_type}.")

    settings.update_settings(index["_settings"])

    return ModelMapper(index_name, doc_type, index)
