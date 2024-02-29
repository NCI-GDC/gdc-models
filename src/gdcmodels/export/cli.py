import functools
import itertools
import sys
import types
from typing import Mapping, Sequence

import click
import deepdiff
import yaml

import gdcmodels
from gdcmodels.export import common, graph, viz

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources

EXPORTERS: Mapping[str, Mapping[str, common.Exporter]] = types.MappingProxyType(
    {**viz.EXPORTERS, **graph.EXPORTERS}
)
INDICES = tuple(EXPORTERS.keys())
DOC_TYPES = tuple(itertools.chain.from_iterable(v.keys() for v in EXPORTERS.values()))


@functools.lru_cache(None)
def load_models() -> gdcmodels.Models:
    return gdcmodels.get_es_models(vestigial_included=True)


class Delta(deepdiff.Delta):
    def dumps(self):
        # NOTE: The vestigial data is only data which must be added to the current
        #       dictionary.
        if "dictionary_item_added" in self.diff:
            return self.serializer({"dictionary_item_added": self.diff["dictionary_item_added"]})

        return self.serializer({})


def run_export(index: str, doc_type: str) -> None:
    new_mapping = EXPORTERS[index][doc_type].export_mapping()
    _ = new_mapping.pop("_meta", None)
    old_mapping = load_models()[index][doc_type]["_mapping"]
    _ = old_mapping.pop("_meta", None)
    diff = deepdiff.DeepDiff(new_mapping, old_mapping)
    delta = Delta(diff, serializer=lambda d: yaml.dump(d, Dumper=yaml.CSafeDumper))

    gdcmodels_files = resources.files(gdcmodels)
    mapping_folder = (
        f"es-models/{index}" if index == doc_type else f"es-models/{index}/{doc_type}"
    )
    mapping_file = gdcmodels_files / f"{mapping_folder}/mapping.yaml"
    vestigial_file = gdcmodels_files / f"{mapping_folder}/vestigial.yaml"

    assert (new_mapping + delta) == old_mapping

    with resources.as_file(mapping_file) as file, open(file, "w") as f:
        yaml.dump(new_mapping, f, Dumper=yaml.CSafeDumper)

    with resources.as_file(vestigial_file) as file, open(file, "w") as f:
        delta.dump(f)


def _doc_type_validation(ctx: click.Context, param: str, value: Sequence[str]) -> Sequence[str]:
    indices = ctx.params["index"]
    doc_types = frozenset(itertools.chain.from_iterable(EXPORTERS[i].keys() for i in indices))

    return tuple(doc_types.intersection(value))


@click.command("export")
@click.option("--index", "-i", type=click.Choice(INDICES), default=INDICES, multiple=True)
@click.option(
    "--doc-type",
    "-d",
    type=click.Choice(DOC_TYPES),
    default=DOC_TYPES,
    multiple=True,
    callback=_doc_type_validation,
)
def cli(index: Sequence[str], doc_type: Sequence[str]):
    """Export a mapping from a different system and/or standardizes said mapping."""
    indices = index
    doc_types = frozenset(doc_type)

    for _index in indices:
        for _doc_type in EXPORTERS[_index].keys() & doc_types:
            run_export(_index, _doc_type)
