from unittest import mock

import yaml

from gdcmodels import constants
from gdcmodels.sync import vestigial


def test__compute_delta() -> None:
    old_mapping = {"key0": "hello"}

    with mock.patch(
        "gdcmodels.sync.vestigial.CURRENT_MAPPINGS",
        {"case_centric": {"case_centric": mock.MagicMock(mappings=old_mapping)}},
    ):
        new_mapping = {"key1": "goodbye"}
        delta = vestigial.compute_delta(constants.Index.CASE_CENTRIC, new_mapping)

    # The vestigial properties when added to new mapping result in the old mapping.
    assert new_mapping + delta == old_mapping


def test__vestigial_diff__dumps() -> None:
    old_mapping = {"key0": "hello", "key1": "tschüss"}

    with mock.patch(
        "gdcmodels.sync.vestigial.CURRENT_MAPPINGS",
        {"case_centric": {"case_centric": mock.MagicMock(mappings=old_mapping)}},
    ):
        new_mapping = {"key1": "goodbye", "key2": "???"}
        delta = vestigial.compute_delta(constants.Index.CASE_CENTRIC, new_mapping)
        dump = delta.dumps()
        data = yaml.safe_load(dump)

    assert frozenset({"dictionary_item_added"}) == data.keys()
    assert data["dictionary_item_added"] == {"root['key0']": "hello"}
