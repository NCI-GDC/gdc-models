#!/usr/bin/env python

import argparse
import dataclasses
import logging
import sys
from typing import List, cast

import elasticsearch
from typing_extensions import Iterable, Optional, Protocol

import gdcmodels

logger = logging.getLogger("init_index")


@dataclasses.dataclass
class ESIndexBuilder:
    index_name: str
    index_prefix: str
    index_type: str = dataclasses.field(default="")
    alias_name: str = dataclasses.field(default="")

    @property
    def full_index_name(self) -> str:
        """Format the actual index name to create."""
        if not self.index_type or self.index_type == self.index_name:
            return f"{self.index_prefix}_{self.index_name}"

        return f"{self.index_prefix}_{self.index_name}_{self.index_type}"

    @property
    def should_create_alias(self) -> bool:
        return self.alias_name != ""


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

    indices = [ESIndexBuilder(index_name, args.prefix) for index_name in args.index]
    if args.alias:
        if len(args.index) != len(args.alias):
            logger.error(f"Mismatching arguments for index: {args.index} and alias: {args.alias}")
            return

        for index, alias_name in zip(indices, args.alias):
            index.alias_name = alias_name

    for index_builder in indices:
        if not es_models.get(index_builder.index_name):
            logger.info(
                f"Specified index '{index_builder.index_name}' is not defined in es-models, skipping it!"
            )
            continue

        indices_created = 0
        for index_type in es_models[index_builder.index_name].keys():
            if index_type == "_settings":
                continue  # settings, not index type

            index_builder.index_type = index_type

            if es.indices.exists(index=index_builder.full_index_name):
                if not args.delete:
                    logger.info(
                        f"Elasticsearch index '{index_builder.full_index_name}' exists, "
                        "'--delete' not specified, skipping"
                    )
                    continue
                else:
                    logger.info(
                        f"Elasticsearch index '{index_builder.full_index_name}' exists, '--delete' specified"
                    )
                    if confirm_delete(index_builder.full_index_name):
                        logger.info(f"Deleting existing index '{index_builder.full_index_name}'")
                        es.indices.delete(index=index_builder.full_index_name)
                    else:
                        logger.info("Index name mismatch, skipping deleting")
                        continue

            logger.info(f"Creating index '{index_builder.full_index_name}'")

            es.indices.create(
                index=index_builder.full_index_name,
                settings=es_models[index_builder.index_name][index_type].settings,
                mappings=es_models[index_builder.index_name][index_type].mappings,
            )
            indices_created += 1

        # Skip this step if no alias provided.
        if not index_builder.should_create_alias:
            continue

        # Skip this step if no index was created in the above steps.
        if not es.indices.exists(index=index_builder.full_index_name):
            logger.warning(
                f"Index '{index_builder.index_name}' not created so alias '{index_builder.alias_name}' will not be created."
            )
            continue

        # This script uses the index names as defined by es_models and creates
        # indices from those instead of naively creating elements from the
        # --index flag directly. That means 'gdc_from_graph' can create
        # multiple indices despite only being one of the elements in the
        # --index flag. This breaks the alias logic but we don't use this
        # script to create those indices so this conditional should never
        # happen in practice.
        if indices_created > 1:
            logger.warning(
                f"Cannot create alias '{index_builder.alias_name}' because too many indices created for '{index_builder.index_name}'"
            )
            continue

        if es.indices.exists_alias(name=index_builder.alias_name):
            logger.warning(
                f"Alias '{index_builder.alias_name}' exists already, skipping creating."
            )
            continue

        es.indices.put_alias(name=index_builder.alias_name, index=index_builder.full_index_name)


def main():
    parser = get_parser()
    args = parser.parse_args()
    if len(args.prefix) == 0:
        sys.exit("Please specify prefix for the index name, eg, 'gdc_r52'")

    init_index(args)


if __name__ == "__main__":
    main()
