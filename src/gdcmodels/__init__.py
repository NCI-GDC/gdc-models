import collections
import functools
from typing import (
    Any,
    DefaultDict,
    Dict,
    Iterator,
    Literal,
    Mapping,
    NamedTuple,
    Protocol,
    Sequence,
    Union,
    cast,
    overload,
)

import deepdiff
import importlib_resources as resources
import yaml
from importlib_resources import abc
from typing_extensions import NotRequired, TypedDict


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


class MutableIndex(Index, Protocol):

    def __setitem__(self, key: str, value: Any) -> None:
        pass  # pragma: no cover


Models = Mapping[str, Index]


class _MappingDetail(NamedTuple):
    """The various details needed to load a given mapping."""

    index_name: str
    doc_type: str
    mapping: abc.Traversable
    settings: abc.Traversable
    descriptions: abc.Traversable
    vestigial: abc.Traversable


def _extract_details(models: abc.Traversable) -> Iterator[_MappingDetail]:
    """Extracts the mapping details from the models resource.

    This works with the following model/index file structures within the given models
    directory:

    1.
        index/
            mapping.yaml
            settings.yaml?
            vestigial.yaml
            descriptions.yaml?
    2.
        index/
            doc_type/
                mapping.yaml
                vestigial.yaml
            settings.yaml?
            descriptions.yaml?

    Args:
        models: The gdcmodes es-models resource from which to extract the mapping
            details.

    Yields:
        The details associated with each model/mapping found within the models resource.
    """

    def _extract_detail(
        index_name: str,
        settings: abc.Traversable,
        descriptions: abc.Traversable,
        doc_type: abc.Traversable,
    ) -> _MappingDetail:
        mapping = doc_type / "mapping.yaml"
        vestigial = doc_type / "vestigial.yaml"

        return _MappingDetail(
            index_name, doc_type.name, mapping, settings, descriptions, vestigial
        )

    for index in models.iterdir():
        index_name = index.name
        settings = index / "settings.yaml"
        descriptions = index / "descriptions.yaml"
        extract_detail = functools.partial(_extract_detail, index_name, settings, descriptions)

        # If mapping.yaml is a file then we have struct 1 and the index file can be
        # considered the doc_type
        if index.joinpath("mapping.yaml").is_file():
            yield extract_detail(index)

        # Otherwise, we have struct 2 and each sub dir is a doc_type
        else:
            doc_types = (p for p in index.iterdir() if p.is_dir())

            yield from map(extract_detail, doc_types)


def _extract_es_mapping(detail: _MappingDetail, vestigial_included: bool) -> ESMapping:
    """Extract the elasticsearch mapping described in the given detail.

    Args:
        detail: The detail with the relavant paths from which to load the mapping.
        vestigial_included: A flag which determins if the vestial properties should be
            included when loading the mapping.

    Returns:
        The ESMapping loaded from the paths within the given detail.
    """
    mapping = yaml.safe_load(detail.mapping.read_bytes())

    if vestigial_included and detail.vestigial.is_file():
        vestigial_delta = deepdiff.Delta(
            detail.vestigial.read_text(), deserializer=yaml.safe_load
        )
        mapping += vestigial_delta

    if detail.descriptions.is_file():
        descriptions = yaml.safe_load(detail.descriptions.read_bytes())

        if descriptions:
            mapping["_meta"] = {"descriptions": descriptions}

    return mapping


def _extract_settings(detail: _MappingDetail) -> dict:
    """Extract the settings from the given detail.

    Args:
        detail: The detail which describes the settings to be loaded.

    Returns:
        The settings associated with the mapping if none are found the default are
        provided.
    """
    return yaml.safe_load(detail.settings.read_bytes()) if detail.settings.is_file() else {}


def get_es_models(vestigial_included: bool = True) -> Models:
    """Loads all models/mappings provided by this library.

    Args:
        vestigial_included: If true the vestigial properties will be added to the
            models. Otherwise, they are omitted.

    Return:
        The models/mappings associated with the indices configured within gdc-models.
    """
    models = resources.files("gdcmodels") / "es-models"
    details = _extract_details(models)
    result = cast(DefaultDict[str, MutableIndex], collections.defaultdict(dict))

    for detail in details:
        result[detail.index_name][detail.doc_type] = {
            "_mapping": _extract_es_mapping(detail, vestigial_included)
        }
        result[detail.index_name]["_settings"] = _extract_settings(detail)

    result.default_factory = None

    return result
