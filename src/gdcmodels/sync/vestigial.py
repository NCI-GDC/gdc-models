"""A module containing the logic for computing vestigial properties."""

from collections.abc import Mapping
from typing import Any

import deepdiff

import gdcmodels
from gdcmodels import constants, extraction_utils

CURRENT_MAPPINGS = gdcmodels.get_es_models(vestigial_included=True)


class VestigialDelta(deepdiff.Delta):
    """A custom Delta object which only writes the items added to the dictionary."""

    def __init__(self, diff: deepdiff.DeepDiff) -> None:
        """Initializes a vestigial delta.

        Args:
            diff: The deep diff upon which this delta is based.
        """
        super().__init__(diff, serializer=extraction_utils.dump_yaml)

    def dumps(self):
        # NOTE: The vestigial data is only data which must be added to the current
        #       dictionary.
        if "dictionary_item_added" in self.diff:
            return self.serializer(
                {"dictionary_item_added": self.diff["dictionary_item_added"]}
            )

        return self.serializer({})


def compute_delta(index: constants.Index, new_mapping: Mapping[str, Any]) -> deepdiff.Delta:
    """Computes the delta between the current and new mapping of the given index.

    Args:
        index: The index which is represented by the given mappings.
        new_mappings: The newly synced mappings.

    Returns:
        A delta representing the difference between the new and old mapping for the index.
    """
    index_name, doc_type = index.components
    old_mapping = CURRENT_MAPPINGS[index_name][doc_type].mappings
    diff = deepdiff.DeepDiff(new_mapping, old_mapping)

    return VestigialDelta(diff)
