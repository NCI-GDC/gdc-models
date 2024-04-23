#!/usr/bin/env python

import argparse
import sys
from typing import List, cast

import elasticsearch
from typing_extensions import Iterable, Optional, Protocol

import gdcmodels


class Arguments(Protocol):
    index: List[str]
    alias: List[str]
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
        "--alias",
        dest="alias",
        nargs="+",
        help="aliases to be initialized",
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

    aliases = ["" for _ in args.index]
    if args.alias:
        aliases = args.alias[:]

    # You cannot create a list of indices and provide a partial list of aliases.
    if len(args.index) != len(aliases):
        print(f"Mismatching arguments for index: {args.index} and alias: {args.alias}")

    for index, alias in zip(args.index, aliases):
        if not es_models.get(index):
            print(f"Specified index '{index}' is not defined in es-models, skipping it!")
            continue

        indices_created = 0
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
                settings=es_models[index][index_type].settings,
                mappings=es_models[index][index_type].mappings,
            )
            indices_created += 1

        # Skip this step if no alias provided.
        if not alias:
            continue

        # Skip this step if no index was created in the above steps.
        if not es.indices.exists(index=full_index_name):
            print(f"Index '{index}' not created so alias '{alias}' will not be created.")
            continue

        # This script uses the index names as defined by es_models and creates
        # indices from those instead of naively creating elements from the
        # --index flag directly. That means 'gdc_from_graph' can create
        # multiple indices despite only being one of the elements in the
        # --index flag. This breaks the alias logic but we don't use this
        # script to create those indices so this conditional should never
        # happen in practice.
        if indices_created > 1:
            print(f"Cannot create alias '{alias}' because too many indices created for '{index}'")
            continue

        if es.indices.exists_alias(name=alias):
            print(f"Alias '{alias}' exists already, skipping creating.")
            continue

        es.indices.put_alias(name=alias, index=full_index_name)


def main():
    parser = get_parser()
    args = parser.parse_args()
    if len(args.prefix) == 0:
        sys.exit("Please specify prefix for the index name, eg, 'gdc_r52'")

    init_index(args)


if __name__ == "__main__":
    main()
