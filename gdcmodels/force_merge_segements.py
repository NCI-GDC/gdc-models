#!/usr/bin/env python

from __future__ import print_function

import argparse
import threading
import urllib3

from itertools import cycle
from time import sleep, time

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionTimeout


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_parser():
    parser = argparse.ArgumentParser(
        description="Force a merge on the shards of one or more ES indices"
    )
    parser.add_argument(
        "--verify-certs",
        default=False,
        action="store_true",
        help="Verify the ca certs for Elasticsearch",
    )
    parser.add_argument(
        "--index",
        help="The index to do the merge, if not provide, all indices will be merged.",
    )
    parser.add_argument(
        "--host", required=True, help="Elasticsearch server host name or IP",
    )
    parser.add_argument(
        "--port", default=9200, help="Elasticsearch server port (default: 9200)",
    )
    parser.add_argument("--user", default="", help="Elasticsearch client user")
    parser.add_argument(
        "--password", dest="password", default="", help="Elasticsearch client password"
    )

    return parser


def _force_merge_wrapper(args):
    es = Elasticsearch(
        hosts=[{"host": args.host, "port": args.port}],
        use_ssl=True,
        verify_certs=args.verify_certs,
        http_auth=(args.user, args.password),
    )

    return force_merge_elasticsearch_segments(es, args.index)


def _force_merge(es, index):
    if index is None:
        index = ""
    elif isinstance(index, str) and index != "":
        index = [index]

    try:
        es.indices.forcemerge(index, max_num_segments=1)
    except ConnectionTimeout:
        active_count = 1
        while active_count != 0:
            res = es.nodes.stats(metric="thread_pool")
            active_count = sum(
                stat["thread_pool"]["force_merge"]["active"]
                for stat in res["nodes"].values()
            )


def force_merge_elasticsearch_segments(es, index=None):

    start = time()
    t = threading.Thread(target=_force_merge, args=(es, index))

    print("Starting merging segments.")
    t.start()

    spinning_cursor = iter(cycle("|/-\\"))
    while t.is_alive():
        print("\r{} still merging.".format(next(spinning_cursor)), end="")
        sleep(1)
    print("\n{}: Finished merging.".format(time() - start))


def main():
    parser = get_parser()
    args = parser.parse_args()
    _force_merge_wrapper(args)


if __name__ == "__main__":
    main()
