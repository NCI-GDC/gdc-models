#!/usr/bin/env python

import argparse
import logging

from gdcmodels import esutils

FORMAT = "[%(asctime)s][%(name)14s][%(levelname)7s] %(message)s"


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
        "index", nargs="+", help="Indices to do the merge.",
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


def main():
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    parser = get_parser()
    args = parser.parse_args()
    es = esutils.get_elasticsearch(args.host, args.port, args.user, args.password, True)
    esutils.force_merge_elasticsearch_indices(es, args.index)


if __name__ == "__main__":
    main()
