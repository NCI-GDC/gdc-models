import sys

import pytest
from elasticsearch.exceptions import ConnectionTimeout

from gdcmodels.services.force_merge_service import force_merge_elasticsearch_indices

if sys.version_info > (3, 2):
    from unittest.mock import Mock


@pytest.mark.parametrize("index", ["", None, [], 1])
def test_force_merge__index_has_to_be_list_and_not_empty(es, index):
    with pytest.raises(ValueError):
        force_merge_elasticsearch_indices(es, index)


@pytest.mark.skipif(sys.version_info < (3, 5), reason="magicmock require version 3.3+")
def test_force_merge__finished_in_time(es):
    index = ["test_index"]
    es.indices.forcemerge = Mock(return_vallue={})
    force_merge_elasticsearch_indices(es, index)
    es.indices.forcemerge.asssert_called_once_with(index, 1)


@pytest.mark.skipif(sys.version_info < (3, 5), reason="magicmock require version 3.3+")
def test_force_merge__timeout(es):
    index = ["test_index"]
    es.indices.forcemerge = Mock(side_effect=ConnectionTimeout())
    counts = [1, 0]
    value = [
        {"nodes": {"test_node": {"thread_pool": {"force_merge": {"active": count}}}}}
        for count in counts
    ]
    es.nodes.stats = Mock(side_effect=value)
    force_merge_elasticsearch_indices(es, index)
    es.indices.forcemerge.asssert_called_once_with(index, 1)
    es.nodes.stats.assert_called_with(metric="thread_pool")
    assert es.nodes.stats.call_count == 2
