import pytest

from gdcmodels.esutils import force_merge_elasticsearch_indices


@pytest.mark.parametrize("index", ["", None, [], 1])
def test_force_merge__index_has_to_be_list_and_not_empty(es, index):
    with pytest.raises(ValueError):
        force_merge_elasticsearch_indices(es, index)
