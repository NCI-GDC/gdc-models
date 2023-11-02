import pytest
from gdcmodels import mapping_utils


@pytest.mark.parametrize(
    "one,two,expected",
    [
        (
            {"a": {"a": None}},
            {"a": {"b": None}},
            {"a": {"a": None, "b": None}},
        ),
        (
            {"a": {"a": {"a": None}}},
            {"a": {"b": None}},
            {"a": {"a": {"a": None}, "b": None}},
        ),
    ],
)
def test_deep_merge_mapping_files(one, two, expected):
    assert mapping_utils.deep_merge_mapping_files(one, two) == expected


@pytest.mark.parametrize(
    "old,new,difference",
    [
        (
            {"a": {"a": None, "b": None}},
            {"a": {"a": None}},
            {"a": {"b": None}},
        ),
        (
            {"a": {"a": {"a": None}, "b": None}},
            {"a": {"a": {"a": None}}},
            {"a": {"b": None}},
        ),
    ],
)
def test_deep_diff_mapping_files(old, new, difference):
    assert mapping_utils.deep_diff_mapping_files(new, old) == difference
