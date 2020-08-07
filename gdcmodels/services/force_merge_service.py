import logging
import urllib3

from time import sleep

from elasticsearch.exceptions import ConnectionTimeout

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def force_merge_elasticsearch_indices(es, index, max_num_segments=1):
    if not index:
        logging.error('Index has to be a list of strings and can not be empty')

    try:
        logging.info('Start merging')
        es.indices.forcemerge(index, max_num_segments=max_num_segments)
    except ConnectionTimeout:
        active_count = 1
        while active_count != 0:
            res = es.nodes.stats(metric="thread_pool")
            active_count = sum(
                stat["thread_pool"]["force_merge"]["active"]
                for stat in res["nodes"].values()
            )
            logging.info('Still merging. Active thread count: {}'.format(active_count))
            sleep(3)
    logging.info('Finished merging.')
