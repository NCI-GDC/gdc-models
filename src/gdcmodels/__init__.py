import collections
import pathlib
from typing import (
    Any,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    Literal,
    NamedTuple,
    Protocol,
    Sequence,
    Tuple,
    Union,
    cast,
    overload,
    Mapping,
)
from typing_extensions import TypedDict, NotRequired
import importlib_resources as resources
from importlib_resources import abc
import yaml
import deepdiff


class Meta(TypedDict):
    descriptions: Dict[str, str]


Properties = Dict[str, Union["Property", "Autocomplete"]]


class Property(TypedDict):
    normalizer: NotRequired[str]
    type: NotRequired[Literal["boolean", "double", "keyword", "long"]]
    copy_to: NotRequired[Sequence[str]]
    properties: NotRequired[Properties]


class InnerAutocomplete(TypedDict):
    analyzer: str
    search_analyzer: str
    type: str


class Autocomplete(Property):
    fields: Dict[str, InnerAutocomplete]


class InnerMapping(TypedDict):
    _meta: NotRequired[Meta]
    properties: Properties


class ESMapping(TypedDict):
    _mapping: InnerMapping


class Index(Protocol):
    @overload
    def __getitem__(self, key: Literal["_settings"]) -> dict: ...  # type: ignore

    @overload
    def __getitem__(self, key: str) -> ESMapping: ...

    def __getitem__(self, key: str) -> Any: ...

    def get(self, key: str, default: ESMapping) -> ESMapping: ...

    def __contains__(self, key: str) -> bool: ...


class MutableIndex(Index, Protocol):

    def __setitem__(self, key: str, value: Any) -> None: ...


Models = Mapping[str, Index]


class _MappingDetail(NamedTuple):
    index_name: str
    doc_type: str
    mapping: pathlib.Path
    settings: pathlib.Path
    descriptions: pathlib.Path
    vestigial: pathlib.Path


def _extract_details(models_dir: pathlib.Path) -> Iterator[_MappingDetail]:
    """
    Index File Struct:
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
    """

    def extract_dirs(index: pathlib.Path) -> Tuple[pathlib.Path, Iterable[pathlib.Path]]:
        mappings: Iterable[pathlib.Path] = index.glob("**/mapping.yaml")
        mappings = map(lambda m: m.relative_to(models_dir), mappings)

        return index.relative_to(models_dir), mappings

    indices = (extract_dirs(index) for index in models_dir.iterdir() if index.is_dir())

    for index, mappings in indices:
        index_name = index.name
        settings = index / "settings.yaml"
        descriptions = index / "descriptions.yaml"

        for mapping in mappings:
            # in structure 1 this is the index name.
            doc_type = mapping.parent.name
            vestigial = mapping.parent / "vestigial.yaml"

            yield _MappingDetail(index_name, doc_type, mapping, settings, descriptions, vestigial)


def _extract_inner_mapping(
    models: abc.Traversable, detail: _MappingDetail, vestigial_included: bool
) -> InnerMapping:
    mapping_file = models / detail.mapping
    vestigial_file = models / detail.vestigial
    descriptions_file = models / detail.descriptions
    mapping = yaml.safe_load(mapping_file.read_bytes())

    if vestigial_included and vestigial_file.is_file():
        vestigial_delta = deepdiff.Delta(vestigial_file.read_text(), deserializer=yaml.safe_load)
        mapping += vestigial_delta

    if descriptions_file.is_file():
        mapping["_meta"] = {"descriptions": yaml.safe_load(descriptions_file.read_bytes())}

    return mapping


def _extract_settings(models: abc.Traversable, detail: _MappingDetail) -> dict:
    settings_file = models / detail.settings

    if settings_file.is_file():
        return yaml.safe_load(settings_file.read_bytes())

    return {}


def get_es_models(vestigial_included: bool = True) -> Models:
    models = resources.files("gdcmodels") / "es-models"

    with resources.as_file(models) as models_dir:
        details = _extract_details(models_dir)

    result = cast(DefaultDict[str, MutableIndex], collections.defaultdict(dict))

    for detail in details:
        result[detail.index_name][detail.doc_type] = {
            "_mapping": _extract_inner_mapping(models, detail, vestigial_included)
        }
        result[detail.index_name]["_settings"] = _extract_settings(models, detail)

    result.default_factory = None

    return result
