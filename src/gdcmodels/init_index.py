#!/usr/bin/env python

import argparse
import sys
from typing import cast

import elasticsearch
from typing_extensions import Iterable, Optional, Protocol

import gdcmodels


class Arguments(Protocol):
    index: str
    prefix: str
    host: str
    port: int
    ssl: bool
    ssl_ca: str
    user: str
    password: str
    delete: bool


class ArgumentParser(Protocol):
    def parse_args(self, args: Optional[Iterable] = None) -> Arguments:  # type: ignore
        pass  # pragma: no cover


def get_parser() -> ArgumentParser:
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
        type=int,
        help="Elasticsearch server port (default: 9200)",
    )
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Connect to Elasticsearch over SSL",
    )
    parser.add_argument("--ssl-ca", help="Path to CA certificate bundle for SSL")
    parser.add_argument("--user", dest="user", default="", help="Elasticsearch client user")
    parser.add_argument(
        "--password", dest="password", default="", help="Elasticsearch client password"
    )
    parser.add_argument(
        "--delete",
        dest="delete",
        action="store_true",
        help="Delete existing index with the same name",
    )

    return cast(ArgumentParser, parser)


def format_index_name(prefix: str, index: str, index_type=None):
    """Format the actual index name to create."""
    if index_type is None or index_type == index:
        return f"{prefix}_{index}"
    else:
        return f"{prefix}_{index}_{index_type}"


def get_elasticsearch(args: Arguments) -> elasticsearch.Elasticsearch:
    """Create an Elasticsearch client according to the given CLI args.

    Args:
        args: arguments. must have host, port, user, password attributes

    Returns:
        Elasticsearch: ES client instance
    """
    return elasticsearch.Elasticsearch(
        hosts=[{"host": args.host, "port": args.port}],
        use_ssl=args.ssl,
        ca_certs=args.ssl_ca,
        http_auth=(args.user, args.password),
        timeout=60,
    )


def confirm_delete(index_name: str) -> bool:
    """Prompt the user to confirm that the given index should be deleted.

    Args:
        index_name (str): The index for which to confirm deletion. The user must input
            the name of this index exactly to confirm.

    Returns:
        bool: Whether the user confirmed deletion.
    """
    ans = input(f"Confirm deleting existing {index_name} index by typing the index name: ")

    return ans == index_name


def init_index(args: Arguments):
    es_models = gdcmodels.get_es_models(vestigial_included=False)
    es = get_elasticsearch(args)

    for index in args.index:
        if not es_models.get(index):
            print(f"Specified index '{index}' is not defined in es-models, skipping it!")
            continue

        for index_type in es_models[index].keys():
            if index_type == "_settings":
                continue  # settings, not index type

            full_index_name = format_index_name(
                prefix=args.prefix,
                index=index,
                index_type=index_type,
            )

            if es.indices.exists(index=full_index_name):
                if not args.delete:
                    print(
                        f"Elasticsearch index '{full_index_name}' exists, "
                        "'--delete' not specified, skipping"
                    )
                    continue
                else:
                    print(f"Elasticsearch index '{full_index_name}' exists, '--delete' specified")
                    if confirm_delete(full_index_name):
                        print(f"Deleting existing index '{full_index_name}'")
                        es.indices.delete(index=full_index_name)
                    else:
                        print("Index name mismatch, skipping deleting")
                        continue

            print(f"Creating index '{full_index_name}'")

            es.indices.create(
                index=full_index_name,
                settings=es_models[index]["_settings"],
                mappings=es_models[index][index_type]["_mapping"],
            )


def main():
    parser = get_parser()
    args = parser.parse_args()
    if len(args.prefix) == 0:
        sys.exit("Please specify prefix for the index name, eg, 'gdc_r52'")

    init_index(args)


if __name__ == "__main__":
    main()
