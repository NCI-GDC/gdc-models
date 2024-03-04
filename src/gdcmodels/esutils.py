import logging
from time import sleep

import urllib3
from elasticsearch.exceptions import ConnectionTimeout
from urllib3.exceptions import ReadTimeoutError

UPDATE_INTERVAL = 10

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def force_merge_elasticsearch_indices(es, index, max_num_segments=1):
    """Force merge segments in elasticsearch indices.

    Args:
        es: Elasticsearch object, Elasticsearch low-level client
        index: A list of index names
        max_num_segments: The number of segments the index should be merged into
    """
    if not index or not isinstance(index, list):
        raise ValueError("index must be a list of index names.")

    try:
        logging.info("Start merging")
        es.indices.forcemerge(index, max_num_segments=max_num_segments)
    except (ConnectionTimeout, ReadTimeoutError):
        while True:
            res = es.nodes.stats(metric="thread_pool")
            active_count = sum(
                stat["thread_pool"]["force_merge"]["active"] for stat in res["nodes"].values()
            )
            if active_count == 0:
                break
            logging.info(f"Still merging. Active thread count: {active_count}")
            sleep(UPDATE_INTERVAL)
    logging.info("Finished merging.")
