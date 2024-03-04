"""This module maintains the abstraction of the structures contained in the models."""

import re
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Tuple, Union

import more_itertools

from gdcmodels import esmodels

Selector = Union[Callable[[Iterable[str]], Iterable[str]], str]


def _walk_mapping(
    mapping: Union[esmodels.ESMapping, esmodels.Property], path: str = "root"
) -> Iterator[Tuple[str, esmodels.Property]]:
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

    NOTE: Instances of this class should be instantiated via `get_es_models`
    """

    __slots__ = ("_index_name", "_doc_type", "_settings", "_mapping")

    def __init__(
        self,
        index_name: str,
        doc_type: str,
        settings: Mapping[str, Any],
        mapping: esmodels.ESMapping,
    ) -> None:
        self._index_name = index_name
        self._doc_type = doc_type
        self._settings = settings
        self._mapping = mapping

    @property
    def index_name(self) -> str:
        return self._index_name

    @property
    def doc_type(self) -> str:
        return self._doc_type

    @property
    def mappings(self) -> esmodels.ESMapping:
        """The elasticsearch mappings associated with the model."""
        return self._mapping

    @property
    def settings(self) -> Mapping[str, Any]:
        """The settings object for the elasticsearch index."""
        return self._settings

    def select_mapping(
        self,
        doc_type: str,
        selector: Optional[Selector] = None,
    ) -> Union[esmodels.ESMapping, esmodels.Property]:
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
        if self.doc_type in [doc_type, f"{doc_type}_centric"]:
            return self.mappings

        mappings = {p: m for p, m in _walk_mapping(self.mappings) if p.endswith(f".{doc_type}")}

        if callable(selector):
            paths = selector(mappings.keys())
        elif isinstance(selector, str):
            pattern = re.compile(rf"\.{selector}\.")
            paths = filter(pattern.search, mappings.keys())
        else:
            paths = mappings.keys()

        selected_path = more_itertools.one(paths)

        return mappings[selected_path]
