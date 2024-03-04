import sys
from typing import Optional, Type

import pytest

from gdcmodels import mapper, utils

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources


@pytest.fixture
def mock_mapper():
    mapping_file = resources.files("tests") / "data/mapper/mapping.yaml"
    mapping = utils.load_yaml(mapping_file.read_bytes())
    gene = mapper.ModelMapper("gene_centric", "gene_centric", {}, mapping)

    return gene


@pytest.mark.parametrize(
    ("doc_type", "selector", "exception_type"),
    (
        ("foo_single", lambda _: (), ValueError),
        ("multiple", None, ValueError),
    ),
)
def test_select_mapping_flow(
    mock_mapper: mapper.ModelMapper,
    doc_type: str,
    selector: Optional[mapper.Selector],
    exception_type: Type[BaseException],
) -> None:
    with pytest.raises(exception_type):
        mock_mapper.select_mapping(doc_type, selector)


@pytest.mark.parametrize(
    ("doc_type", "selector", "path"),
    (
        ("foo", None, "properties.foo"),
        ("bar", None, "properties.bar"),
        ("foo_single", None, "properties.foo.properties.foo_single"),
        (
            "multiple",
            lambda x: list(filter(lambda y: "foo" in y, x)),
            "properties.foo.properties.multiple",
        ),
        ("multiple", "bar", "properties.bar.properties.multiple"),
    ),
)
def test_select_mapping_results(
    mock_mapper: mapper.ModelMapper,
    doc_type: str,
    selector: Optional[mapper.Selector],
    path: str,
) -> None:
    actual = mock_mapper.select_mapping(doc_type, selector)

    expected = mock_mapper.mappings
    for part in path.split("."):
        expected = expected[part]

    assert actual == expected, actual
