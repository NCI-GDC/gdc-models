from typing import Iterable

import pytest

import gdcmodels
from gdcmodels import esmodels
from gdcmodels.sync import cli, common
from gdcmodels.sync.graph import common as graph


def get_index_params() -> Iterable:
    synchronizers = ((i, d, e) for i, es in cli.SYNCHRONIZERS.items() for d, e in es.items())

    for index, doc_type, synchronizer in synchronizers:
        yield pytest.param(index, doc_type, synchronizer, id=f"{index}/{doc_type}")


@pytest.fixture(scope="session")
def models() -> esmodels.Models:
    return gdcmodels.get_es_models(vestigial_included=False)


@pytest.mark.parametrize(("index_name", "doc_type", "synchronizer"), get_index_params())
def test__sync__index_is_synced(
    models: esmodels.Models,
    index_name: str,
    doc_type: str,
    synchronizer: common.Synchronizer,
) -> None:
    index = models[index_name]
    mapping = index[doc_type]["_mapping"]
    settings = index["_settings"]

    synced = synchronizer.sync(mapping, settings)

    assert (mapping, settings) == synced


def test__normalizer_sync__add_normalizer() -> None:
    mapping: esmodels.ESMapping = {"properties": {"foo": {"type": "keyword"}}}
    settings = {}
    synchronizer = common.DefaultNormalizerSynchronizer(
        normalizer_name="test_norm", excluded_properties=()
    )

    mapping, settings = synchronizer.sync(mapping, settings)

    assert settings == {}
    assert "normalizer" in mapping["properties"]["foo"]
    assert mapping["properties"]["foo"]["normalizer"] == "test_norm"


def test__normalizer_sync__add_normalizer_recursively() -> None:
    mapping: esmodels.ESMapping = {
        "properties": {"foo": {"properties": {"bar": {"type": "keyword"}}}}
    }
    settings = {}
    synchronizer = common.DefaultNormalizerSynchronizer(
        normalizer_name="test_norm", excluded_properties=()
    )

    mapping, settings = synchronizer.sync(mapping, settings)

    assert settings == {}
    assert "properties" in mapping["properties"]["foo"]
    assert "normalizer" in mapping["properties"]["foo"]["properties"]["bar"]
    assert mapping["properties"]["foo"]["properties"]["bar"]["normalizer"] == "test_norm"


def test__normalizer_sync__exclude_properties() -> None:
    mapping: esmodels.ESMapping = {"properties": {"foo": {"type": "keyword"}}}
    settings = {}
    synchronizer = common.DefaultNormalizerSynchronizer(
        normalizer_name="test_norm", excluded_properties=("foo",)
    )

    mapping, settings = synchronizer.sync(mapping, settings)

    assert settings == {}
    assert "normalizer" not in mapping["properties"]["foo"]


@pytest.mark.parametrize(
    ("field", "substring"),
    (
        ("annotations.analyte.project_id", "Unique ID for any specific"),
        ("annotations.annotation.submitter_id", "project-specific"),
        ("annotations.slide.section_location", "Tissue source"),
        ("cases.case.created_datetime", "combination of date and time"),
        ("cases.case.primary_site", "the primary site of disease"),
        ("cases.diagnoses.morphology", "The third edition"),
        ("cases.follow_ups.molecular_tests.intron", "Intron number"),
        ("cases.project.code", "Project code"),
        ("files.center.code", "Numeric code for the center"),
        ("files.file.md5sum", "The 128-bit hash"),
        ("projects.project.state", "The possible states"),
    ),
)
def test__descriptions_sync__spot_check(field: str, substring: str):
    synchronizer = graph.DescriptionsSynchronizer()

    mapping, _ = synchronizer.sync({"properties": {}}, {})

    assert "_meta" in mapping
    assert field in mapping["_meta"]["descriptions"]
    assert substring in mapping["_meta"]["descriptions"][field]
