import copy
import itertools
from typing import Iterable

import pytest

import gdcmodels
from gdcmodels.export import cli, normalization


def get_index_params() -> Iterable:
    normalizers = itertools.chain(
        # ((i, d, normalization.GraphNormalizer()) for i, d in gdcmodels.GRAPH_INDICES),
        ((i, d, normalization.DefaultNormalizer()) for i, d in gdcmodels.VIZ_INDICES),
    )

    for index, doc_type, normalizer in normalizers:
        yield pytest.param(index, doc_type, normalizer, id=f"{index}/{doc_type}")


@pytest.mark.parametrize(("index", "doc_type", "normalizer"), get_index_params())
def test__normalize__index_is_normalized(
    index: str, doc_type: str, normalizer: normalization.Normalizer
) -> None:
    mapping = cli.load_models()[index][doc_type]["_mapping"]
    normalized_mapping = copy.deepcopy(mapping)

    normalizer.normalize(normalized_mapping)

    assert mapping == normalized_mapping
