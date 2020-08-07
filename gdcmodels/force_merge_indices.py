#!/usr/bin/env python

import argparse
import logging

from gdcmodels.init_index import get_elasticsearch
from services.force_merge_service import force_merge_elasticsearch_indices

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
        "--index",
        required=True,
        help="Comma separated indices to do the merge, if not provide, all indices will be merged.",
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
    es = get_elasticsearch(args, True, args.verify_certs)
    force_merge_elasticsearch_indices(es, args.index.split(","))


if __name__ == "__main__":
    main()
