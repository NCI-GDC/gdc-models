from collections.abc import Mapping

import deepdiff
import pytest

import gdcmodels
from gdcmodels import constants, mapper
from gdcmodels.sync import main


@pytest.fixture(scope="session")
def models() -> Mapping[str, Mapping[str, mapper.ModelMapper]]:
    return gdcmodels.get_es_models(vestigial_included=False)


@pytest.mark.parametrize("index", constants.Index)
def test__sync__index_is_synced(
    models: Mapping[str, Mapping[str, mapper.ModelMapper]], index: constants.Index
) -> None:
    index_name, doc_type = index.components
    actual_mappings = models[index_name][doc_type].mappings
    actual_mappings = {k: v for k, v in actual_mappings.items() if k != "_meta"}

    synced_mappings = main.sync(index)

    assert not deepdiff.DeepDiff(actual_mappings, synced_mappings)
