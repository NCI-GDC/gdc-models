import logging
import urllib3

from time import sleep

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionTimeout

UPDATE_INTERVAL = 10

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_elasticsearch(host, port=9200, user='', password='', use_ssl=True):
    """Create an Elasticsearch client according to the given CLI args.

    Args:
        host: Elasticsearch host
        port: Elasticsearch port
        user: Elasticsearch username
        password: Elasticsearch password
        use_ssl: Turn on/off SSL

    Returns:

    """
    return Elasticsearch(
        hosts=[{"host": host, "port": port}],
        http_auth=(user, password),
        use_ssl=use_ssl,
        verify_certs=False,
        timeout=60,
    )


def force_merge_elasticsearch_indices(es, index, max_num_segments=1):
    """force merge segments in elasticsearch indices

    Args:
        es: Elasticsearch object, Elasticsearch low-level client
        index: A comma-separated list of index names
        max_num_segments: The number of segments the index should be merged into

    Returns:

    """
    if not index or not isinstance(index, str):
        raise ValueError("index must be a comma-separated list of index names.")

    try:
        logging.info("Start merging")
        es.indices.forcemerge(index, max_num_segments=max_num_segments)
    except ConnectionTimeout:
        while True:
            res = es.nodes.stats(metric="thread_pool")
            active_count = sum(
                stat["thread_pool"]["force_merge"]["active"]
                for stat in res["nodes"].values()
            )
            if active_count == 0:
                break
            logging.info("Still merging. Active thread count: {}".format(active_count))
            sleep(UPDATE_INTERVAL)
    logging.info("Finished merging.")
