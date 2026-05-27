from collections.abc import Mapping, Set
from importlib import resources
from typing import Any

import deepdiff
import mergedeep
import tap

import gdcmodels
from gdcmodels import constants, extraction_utils
from gdcmodels.sync.overlays import autocomplete, graph, headers, static

CURRENT_MAPPINGS = gdcmodels.get_es_models(vestigial_included=True)


def _apply_normalizer(excluded: Set[str], mapping: Mapping[str, Any]) -> None:
    for prop, details in mapping["properties"].items():
        if "properties" in details:
            _apply_normalizer(excluded, details)
        elif details.get("type") == "keyword" and prop not in excluded:
            details["normalizer"] = "clinical_normalizer"


def _update_vestigial(index: constants.Index, new_mappings: Mapping[str, Any]) -> None:
    index_name, doc_type = index.components
    old_mappings = CURRENT_MAPPINGS[index_name][doc_type]
    diff = deepdiff.DeepDiff(new_mappings, old_mappings)

    if diff:
        with (
            resources.as_file(index.models_dir / constants.VESTIGIAL_FILE) as path,
            open(path, "w+") as f,
        ):
            VestigialDelta(diff).dump(f)


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
            return self.serializer(
                {"dictionary_item_added": self.diff["dictionary_item_added"]}
            )

        return self.serializer({})


def sync(index: constants.Index) -> Mapping[str, Any]:
    mappings = mergedeep.merge(
        {},
        autocomplete.MAPPINGS[index],
        graph.MAPPINGS[index],
        headers.MAPPINGS[index],
        static.MAPPINGS[index],
        strategy=mergedeep.Strategy.ADDITIVE,
    )

    _apply_normalizer(index.unnormalized_properties, mappings)

    with open("test.log", "w+") as f:
        extraction_utils.dump_yaml(mappings, f)

    return mappings


def _main(indices: tuple[constants.Index, ...] = tuple(constants.Index)):
    for index in indices:
        mappings = sync(index)

        _update_vestigial(index, mappings)

        with (
            resources.as_file(index.models_dir / constants.MAPPINGS_FILE) as path,
            open(path, "w") as f,
        ):
            extraction_utils.dump_yaml(mappings, f)


def main() -> None:
    tap.tapify(_main)
