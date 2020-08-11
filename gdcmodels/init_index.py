#!/usr/bin/env python

import argparse
import sys

from six.moves import input

from gdcmodels import get_es_models, esutils


def get_parser():
    parser = argparse.ArgumentParser(
        description="Initialize ES index(es) with settings and mappings."
    )
    parser.add_argument(
        "--index",
        dest="index",
        required=True,
        nargs="+",
        help="index to be initialized",
    )
    parser.add_argument(
        "--prefix", dest="prefix", required=True, help="prefix for the index name"
    )
    parser.add_argument(
        "--host",
        dest="host",
        required=True,
        help="Elasticsearch server host name or IP",
    )
    parser.add_argument(
        "--port",
        dest="port",
        default=9200,
        help="Elasticsearch server port (default: 9200)",
    )
    parser.add_argument(
        "--user", dest="user", default="", help="Elasticsearch client user"
    )
    parser.add_argument(
        "--password", dest="password", default="", help="Elasticsearch client password"
    )
    parser.add_argument(
        "--delete",
        dest="delete",
        action="store_true",
        help="Delete existing index with the same name",
    )

    return parser


def format_index_name(prefix, index, index_type=None):
    """Format the actual index name to create."""
    if index_type is None or index_type == index:
        return "_".join([prefix, index])
    else:
        return "_".join([prefix, index, index_type])


def confirm_delete(index_name):
    """Prompt the user to confirm that the given index should be deleted.

    Args:
        index_name (str): The index for which to confirm deletion. The user must input
            the name of this index exactly to confirm.

    Returns:
        bool: Whether the user confirmed deletion.
    """
    ans = input(
        "Confirm deleting existing {} index by typing the "
        "index name: ".format(index_name)
    )

    return ans == index_name


def init_index(args):
    es_models = get_es_models()
    es = esutils.get_elasticsearch(
        args.host, args.port, args.user, args.password, False
    )

    for index in args.index:
        if not es_models.get(index):
            print(
                "Specified index '{}' is not defined in es-models,"
                " skipping it!".format(index)
            )
            continue

        for index_type in es_models[index]:
            if index_type == "_settings":
                continue  # settings, not index type

            full_index_name = format_index_name(
                prefix=args.prefix, index=index, index_type=index_type,
            )

            if es.indices.exists(index=full_index_name):
                if not args.delete:
                    print(
                        "Elasticsearch index '{}' exists, "
                        "'--delete' not specified, skipping".format(full_index_name)
                    )
                    continue
                else:
                    print(
                        "Elasticsearch index '{}' exists, "
                        "'--delete' specified".format(full_index_name)
                    )
                    if confirm_delete(full_index_name):
                        print("Deleting existing index '{}'".format(full_index_name))
                        es.indices.delete(index=full_index_name)
                    else:
                        print("Index name mismatch, skipping deleting")
                        continue

            print("Creating index '{}'".format(full_index_name))

            body = {
                "settings": es_models[index]["_settings"],
                "mappings": es_models[index][index_type]["_mapping"],
            }
            es.indices.create(index=full_index_name, body=body)


def main():
    parser = get_parser()
    args = parser.parse_args()
    if len(args.prefix) == 0:
        sys.exit("Please specify prefix for the index name, eg, 'gdc_r52'")

    init_index(args)


if __name__ == "__main__":
    main()
