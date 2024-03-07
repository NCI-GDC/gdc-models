from typing import Iterable

import pytest

import gdcmodels
from gdcmodels import esmodels
from gdcmodels.export import cli, common


def get_index_params() -> Iterable:
    exporters = ((i, d, e) for i, es in cli.EXPORTERS.items() for d, e in es.items())

    for index, doc_type, exporter in exporters:
        yield pytest.param(index, doc_type, exporter, id=f"{index}/{doc_type}")


@pytest.fixture(scope="session")
def models() -> esmodels.Models:
    return gdcmodels.get_es_models(vestigial_included=False)


@pytest.mark.parametrize(("index_name", "doc_type", "exporter"), get_index_params())
def test__export__index_is_exported(
    models: esmodels.Models,
    index_name: str,
    doc_type: str,
    exporter: common.Exporter,
) -> None:
    index = models[index_name]
    mapping = index[doc_type]["_mapping"]
    settings = index["_settings"]

    exported = exporter.export(mapping, settings)

    assert (mapping, settings) == exported


def test__normalizer_export__add_normalizer() -> None:
    mapping: esmodels.ESMapping = {"properties": {"foo": {"type": "keyword"}}}
    settings = {}
    exporter = common.DefaultNormalizerExporter(
        normalizer_name="test_norm", excluded_properties=()
    )

    mapping, settings = exporter.export(mapping, settings)

    assert settings == {}
    assert "normalizer" in mapping["properties"]["foo"]
    assert mapping["properties"]["foo"]["normalizer"] == "test_norm"


def test__normalizer_export__add_normalizer_recursively() -> None:
    mapping: esmodels.ESMapping = {
        "properties": {"foo": {"properties": {"bar": {"type": "keyword"}}}}
    }
    settings = {}
    exporter = common.DefaultNormalizerExporter(
        normalizer_name="test_norm", excluded_properties=()
    )

    mapping, settings = exporter.export(mapping, settings)

    assert settings == {}
    assert "properties" in mapping["properties"]["foo"]
    assert "normalizer" in mapping["properties"]["foo"]["properties"]["bar"]
    assert mapping["properties"]["foo"]["properties"]["bar"]["normalizer"] == "test_norm"


def test__normalizer_export__exclude_properties() -> None:
    mapping: esmodels.ESMapping = {"properties": {"foo": {"type": "keyword"}}}
    settings = {}
    exporter = common.DefaultNormalizerExporter(
        normalizer_name="test_norm", excluded_properties=("foo",)
    )

    mapping, settings = exporter.export(mapping, settings)

    assert settings == {}
    assert "normalizer" not in mapping["properties"]["foo"]
