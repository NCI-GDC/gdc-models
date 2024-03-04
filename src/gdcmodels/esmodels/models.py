from typing import Any, Dict, KeysView, Literal, Mapping, Sequence, Union, overload

from typing_extensions import NotRequired, Protocol, TypedDict


class Meta(TypedDict):
    """The metadata associated with a mapping."""

    descriptions: Dict[str, str]


Properties = Dict[str, Union["Property", "Autocomplete"]]


class Property(TypedDict):
    """A property in an es mapping."""

    normalizer: NotRequired[str]
    type: NotRequired[Literal["boolean", "double", "keyword", "long"]]
    copy_to: NotRequired[Sequence[str]]
    properties: NotRequired[Properties]


class AutocompleteField(TypedDict):
    """An autocomplete field's details in an es mapping."""

    analyzer: str
    search_analyzer: str
    type: str


class Autocomplete(Property):
    """An autocomplete object in an es mapping."""

    fields: Dict[str, AutocompleteField]


class ESMapping(TypedDict):
    """An elasticsearch mapping."""

    _meta: NotRequired[Meta]
    properties: Properties


class DocType(TypedDict):
    """A document type and its details."""

    _mapping: ESMapping


class Index(Protocol):
    """An index and its associated details.

    NOTE: This is a bit of a workaround because a TypeDict w/ a _settings field cannot
    also be a Dict[str, DocType]. MyPy doesn't love this as the first overload can be
    confused with the second but this should allow most type hinters to hint property
    when accessing these keys in the associated dict.
    """

    @overload
    def __getitem__(self, key: Literal["_settings"]) -> dict:  # type: ignore
        pass  # pragma: no cover

    @overload
    def __getitem__(self, key: str) -> DocType:
        pass  # pragma: no cover

    def __getitem__(self, key: str) -> Any:
        pass  # pragma: no cover

    def get(self, key: str, default: DocType) -> DocType:  # type: ignore
        pass  # pragma: no cover

    def __contains__(self, key: str) -> bool:  # type: ignore
        pass  # pragma: no cover

    def keys(self) -> KeysView[str]:  # type: ignore
        pass  # pragma: no cover


class MutableIndex(Index, Protocol):
    def __setitem__(self, key: str, value: Any) -> None:
        pass  # pragma: no cover


Models = Mapping[str, Index]
