import deepdiff
import pytest

import gdcmodels
from gdcmodels import constants
from gdcmodels.sync import mappings

CURRENT_MAPPINGS = gdcmodels.get_es_models(vestigial_included=False)


@pytest.mark.parametrize("index", constants.Index)
def test__sync(index: constants.Index) -> None:
    """NOTE: If this test fails the sync process should be called to update the mappings. See
    README for further details.
    """
    index_name, doc_type = index.components
    current_mapping = dict(CURRENT_MAPPINGS[index_name][doc_type].mappings)
    synced_mapping = mappings.sync(index)

    current_mapping.pop("_meta", None)  # TODO: DEV-4065 Remove when we start syncing _meta

    assert not deepdiff.DeepDiff(current_mapping, synced_mapping, ignore_order=True)
