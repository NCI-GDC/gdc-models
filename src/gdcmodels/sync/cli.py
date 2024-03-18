"""The basic cli functionality for the sync."""

import functools
import itertools
import sys
import types
from typing import AbstractSet, Any, Mapping, Optional, Sequence

import click
import deepdiff

import gdcmodels
from gdcmodels import esmodels, extraction_utils
from gdcmodels.sync import common, graph, viz

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources


SYNCHRONIZERS: Mapping[str, Mapping[str, common.Synchronizer]] = types.MappingProxyType(
    {**viz.SYNCHRONIZERS, **graph.SYNCHRONIZERS}
)
INDICES = tuple(SYNCHRONIZERS.keys())
DOC_TYPES = tuple(itertools.chain.from_iterable(v.keys() for v in SYNCHRONIZERS.values()))


@functools.lru_cache(None)
def load_models() -> esmodels.Models:
    """Call get_es_models and manage cache of the results.

    Returns:
        The loaded models.
    """
    return gdcmodels.get_es_models(vestigial_included=True)


class VestigialDelta(deepdiff.Delta):
    """A custom Delta object which only writes the items added to the dictionary."""

    def __init__(self, diff) -> None:
        super().__init__(
            diff,
            serializer=lambda *args: extraction_utils.dump_yaml(*args),
        )

    def dumps(self):
        # NOTE: The vestigial data is only data which must be added to the current
        #       dictionary.
        if "dictionary_item_added" in self.diff:
            return self.serializer({"dictionary_item_added": self.diff["dictionary_item_added"]})

        return self.serializer({})


def _write_files(
    index_name: str,
    doc_type: str,
    mapping: esmodels.ESMapping,
    delta: deepdiff.Delta,
    settings: Mapping[str, Any],
    descriptions: Optional[Mapping[str, Any]],
) -> None:
    """Write the various data points to their appropriate files in the models.

    Args:
        index_name: The index name of the associated with the data.
        doc_type: The doc-type name of the associated with the data.
        mapping: The mapping of the index.
        delta: The delta object representing any vestigial data.
        settings: The settings with which the index needs to be configured.
        descriptions: Any optional descriptions associated with the index.
    """
    esmodels_dir = resources.files(esmodels)
    mapping_dir = index_name if index_name == doc_type else f"{index_name}/{doc_type}"
    mapping_file = esmodels_dir / mapping_dir / "mapping.yaml"
    vestigial_file = esmodels_dir / mapping_dir / "vestigial.yaml"
    settings_file = esmodels_dir / index_name / "settings.yaml"
    descriptions_file = esmodels_dir / index_name / "descriptions.yaml"

    with resources.as_file(settings_file) as file, open(file, "w") as f:
        extraction_utils.dump_yaml(settings, f)

    if delta.diff:
        with resources.as_file(mapping_file) as file, open(file, "w") as f:
            extraction_utils.dump_yaml(mapping, f)

        with resources.as_file(vestigial_file) as file, open(file, "w") as f:
            delta.dump(f)

    if descriptions:
        with resources.as_file(descriptions_file) as file, open(file, "w") as f:
            extraction_utils.dump_yaml(descriptions, f)


def run_synchronization(index_name: str, doc_type: str) -> None:
    """Run the synchronization of the index/doc-type.

    Args:
        index_name: The name of the index to sync.
        doc_type: The doc type associated with the index.
    """
    index = load_models()[index_name]
    old_mapping, old_settings = index[doc_type]["_mapping"], index["_settings"]
    _ = old_mapping.pop("_meta", None)

    synchronizer = SYNCHRONIZERS[index_name][doc_type]
    new_mapping, new_settings = synchronizer.sync(old_mapping, old_settings)
    descriptions = new_mapping.pop("_meta", {}).get("descriptions")

    diff = deepdiff.DeepDiff(new_mapping, old_mapping)
    delta = VestigialDelta(diff)

    assert (new_mapping + delta) == old_mapping

    _write_files(index_name, doc_type, new_mapping, delta, new_settings, descriptions)


def _doc_type_validation(
    ctx: click.Context, param: str, value: Sequence[str]
) -> AbstractSet[str]:
    """Validate the doc types provided in input and convert to set.

    Args:
        ctx: The click context.
        param: The name of the param being validated.
        value: The value of the param being validated.

    Returns:
        The validated input converted from a sequence to a set.
    """
    indices = ctx.params["index"]
    valid_doc_types = frozenset(
        itertools.chain.from_iterable(SYNCHRONIZERS[i].keys() for i in indices)
    )
    doc_types = frozenset(value)

    if not (doc_types <= valid_doc_types):
        invalid_doc_types = ",".join(doc_types - valid_doc_types)

        raise click.BadParameter(f"Invalid doc-type(s) for given indices: {invalid_doc_types}.")

    return doc_types


@click.command("sync")
@click.option("--index", "-i", type=click.Choice(INDICES), default=INDICES, multiple=True)
@click.option(
    "--doc-type",
    "-d",
    type=click.Choice(DOC_TYPES),
    default=DOC_TYPES,
    multiple=True,
    callback=_doc_type_validation,
)
def cli(index: Sequence[str], doc_type: AbstractSet[str]) -> None:
    """Sync a mapping with a different system and/or standardizes said mapping.

    Args:
        index:
            index: The indices to be synced.
            doc_type: The doc-types associated with the indices which are to be
                synced.
    """
    indices = index

    for _index in indices:
        for _doc_type in SYNCHRONIZERS[_index].keys() & doc_type:
            run_synchronization(_index, _doc_type)
