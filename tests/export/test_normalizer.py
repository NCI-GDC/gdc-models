import copy
import itertools

import pytest

import gdcmodels
from gdcmodels.export import cli, normalizer


@pytest.mark.parametrize(
    ("index", "doc_type", "normalizer"),
    itertools.chain(
        # ((i, d, normalizer.GraphNormalizer()) for i, d in gdcmodels.GRAPH_INDICES),
        ((i, d, normalizer.DefaultNormalizer()) for i, d in gdcmodels.VIZ_INDICES),
    ),
)
def test__normalize__index_is_normalized(
    index: str, doc_type: str, normalizer: normalizer.Normalizer
) -> None:
    mapping = cli.load_models()[index][doc_type]["_mapping"]
    normalized_mapping = copy.deepcopy(mapping)

    normalizer.normalize(normalized_mapping)

    assert mapping == normalized_mapping
