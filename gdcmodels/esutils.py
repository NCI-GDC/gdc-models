import logging
import urllib3

from time import sleep

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionTimeout

UPDATE_INTERVAL = 10

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_elasticsearch(args, use_ssl=False, verify_certs=True):
    """Create an Elasticsearch client according to the given CLI args."""
    return Elasticsearch(
        hosts=[{"host": args.host, "port": args.port}],
        http_auth=(args.user, args.password),
        use_ssl=use_ssl,
        verify_certs=verify_certs,
        timeout=60,
    )


def force_merge_elasticsearch_indices(es, index, max_num_segments=1):
    if not index or not isinstance(index, list):
        raise ValueError("index has to be a non empty list of strings.")

    try:
        logging.info("Start merging")
        es.indices.forcemerge(index, max_num_segments=max_num_segments)
    except ConnectionTimeout:
        active_count = 1
        while active_count != 0:
            res = es.nodes.stats(metric="thread_pool")
            active_count = sum(
                stat["thread_pool"]["force_merge"]["active"]
                for stat in res["nodes"].values()
            )
            logging.info("Still merging. Active thread count: {}".format(active_count))
            sleep(UPDATE_INTERVAL)
    logging.info("Finished merging.")
