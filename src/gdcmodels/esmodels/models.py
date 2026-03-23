from collections.abc import Sequence
from typing import Literal, Union

from typing_extensions import NotRequired, TypedDict

GRAPH_INDICES = tuple(("gdc_from_graph", d) for d in ("annotation", "case", "file", "project"))
VIZ_INDICES = tuple(
    (i, i)
    for i in (
        "case_centric",
        "cnv_centric",
        "cnv_occurrence_centric",
        "gene_centric",
        "segment_cnv_centric",
        "segment_cnv_occurrence_centric",
        "ssm_centric",
        "ssm_occurrence_centric",
    )
)


class Meta(TypedDict):
    """The metadata associated with a mapping."""

    descriptions: dict[str, str]


Properties = dict[str, Union["Property", "Autocomplete"]]


class Property(TypedDict):
    """A property in an es mapping."""

    normalizer: NotRequired[str]
    type: NotRequired[Literal["boolean", "double", "keyword", "long", "nested"]]
    copy_to: NotRequired[Sequence[str]]
    properties: NotRequired[Properties]


class AutocompleteField(TypedDict):
    """An autocomplete field's details in an es mapping."""

    analyzer: str
    search_analyzer: str
    type: str


class Autocomplete(Property):
    """An autocomplete object in an es mapping."""

    fields: dict[str, AutocompleteField]


class ESMapping(TypedDict):
    """An elasticsearch mapping."""

    _meta: NotRequired[Meta]
    properties: Properties
