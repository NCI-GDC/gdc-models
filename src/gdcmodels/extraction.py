import collections
import functools
import sys
from typing import DefaultDict, Iterator, NamedTuple, cast

import deepdiff

from gdcmodels import esmodels, utils

if sys.version_info < (3, 9):
    import importlib_resources as resources
    from importlib_resources import abc
else:
    from importlib import abc, resources


class _MappingDetail(NamedTuple):
    """The various details needed to load a given mapping."""

    index_name: str
    doc_type: str
    mapping: abc.Traversable
    settings: abc.Traversable
    descriptions: abc.Traversable
    vestigial: abc.Traversable


def _extract_details(models: abc.Traversable) -> Iterator[_MappingDetail]:
    """Extract the mapping details from the models resource.

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
        models: The gdcmodels esmodels resource from which to extract the mapping
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

    indices = (i for i in models.iterdir() if i.is_dir())

    for index in indices:
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


def _extract_es_mapping(detail: _MappingDetail, vestigial_included: bool) -> esmodels.ESMapping:
    """Extract the elasticsearch mapping described in the given detail.

    Args:
        detail: The detail with the relevant paths from which to load the mapping.
        vestigial_included: A flag which determine if the vestigial properties should be
            included when loading the mapping.

    Returns:
        The ESMapping loaded from the paths within the given detail.
    """
    mapping = utils.load_yaml(detail.mapping.read_bytes())

    if vestigial_included and detail.vestigial.is_file():
        vestigial_delta = deepdiff.Delta(
            detail.vestigial.read_text(), deserializer=utils.load_yaml
        )
        mapping += vestigial_delta

    if detail.descriptions.is_file():
        descriptions = utils.load_yaml(detail.descriptions.read_bytes())

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
    return utils.load_yaml(detail.settings.read_bytes()) if detail.settings.is_file() else {}


def get_es_models(vestigial_included: bool = True) -> esmodels.Models:
    """Load all models/mappings provided by this library.

    Args:
        vestigial_included: If true the vestigial properties will be added to the
            models. Otherwise, they are omitted.

    Return:
        The models/mappings associated with the indices configured within gdc-models.
    """
    models = resources.files(esmodels)
    details = _extract_details(models)
    result = cast(DefaultDict[str, esmodels.MutableIndex], collections.defaultdict(dict))

    for detail in details:
        result[detail.index_name][detail.doc_type] = {
            "_mapping": _extract_es_mapping(detail, vestigial_included)
        }
        result[detail.index_name]["_settings"] = _extract_settings(detail)

    result.default_factory = None

    return result
