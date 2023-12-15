#!/usr/bin/env python

import argparse
import logging

from gdcmodels import esutils
from gdcmodels.init_index import get_elasticsearch


FORMAT = "[%(asctime)s][%(name)14s][%(levelname)7s] %(message)s"


def get_parser():
    parser = argparse.ArgumentParser(
        description="Force a merge on the shards of one or more ES indices"
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
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Connect to Elasticsearch over SSL",
    )
    parser.add_argument("--ssl-ca", help="Path to CA certificate bundle for SSL")

    return parser


def main():
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    parser = get_parser()
    args = parser.parse_args()
    es = get_elasticsearch(args)
    esutils.force_merge_elasticsearch_indices(es, args.index)


if __name__ == "__main__":
    main()
