import functools
import pathlib

import pytest

import gdcmodels
from tests import utils


@pytest.mark.parametrize(
    ("doc_type", "project_name_field"),
    (
        ("case", "cases.project.name"),
        ("project", "projects.name"),
        ("file", "files.cases.project.name"),
        ("annotation", "annotations.project.name"),
    ),
)
def test__get_es_models__standard_behavior(doc_type: str, project_name_field: str) -> None:
    """Test that correct number of index mappings are loaded from es-models."""
    models = gdcmodels.get_es_models()

    assert len(models) == 14

    mapping = models["gdc_from_graph"][doc_type].mappings
    assert "_meta" in mapping, mapping.keys()
    assert "descriptions" in mapping["_meta"]
    assert project_name_field in mapping["_meta"]["descriptions"]


def test__get_es_models__multiple_indices(es_models: pathlib.Path) -> None:
    """Test that content of mappings and settings is correct"""
    mappings = {
        "foo": {
            "index_name": "foo",
            "mapping": {
                "properties": {
                    "foo": {"type": "keyword"},
                    "bar": {"type": "long"},
                }
            },
            "settings": {"foo": 1, "bar": 2},
        },
        "bar": {
            "index_name": "bar",
            "doc_type": "foo_bar",
            "mapping": {
                "properties": {
                    "foo": {
                        "type": "nested",
                        "properties": {
                            "foofoo": {"type": "keyword"},
                            "foobar": {"type": "keyword"},
                        },
                    },
                    "bar": {"type": "long"},
                }
            },
            "settings": {"foo": 2, "bar": 4},
        },
    }
    load_model = functools.partial(utils.load_model, es_models)

    for mapping in mappings.values():
        load_model(**mapping)

    models = gdcmodels.get_es_models()

    assert "foo" in models
    assert "foo" in models["foo"]
    assert mappings["foo"]["mapping"] == models["foo"]["foo"].mappings
    assert mappings["foo"]["settings"] == models["foo"]["foo"].settings

    assert "bar" in models
    assert "foo_bar" in models["bar"]
    assert mappings["bar"]["mapping"] == models["bar"]["foo_bar"].mappings
    assert mappings["bar"]["settings"] == models["bar"]["foo_bar"].settings


def test__get_es_models__no_descriptions(es_models: pathlib.Path) -> None:
    """Test that default behavior without descriptions is preserved"""
    mapping = {
        "properties": {
            "foo": {"type": "keyword"},
            "bar": {"type": "long"},
        }
    }
    settings: dict = {}

    utils.load_model(es_models, "foo", mapping, settings)

    models = gdcmodels.get_es_models()

    assert "foo" in models
    assert "foo" in models["foo"]
    assert mapping == models["foo"]["foo"].mappings


def test__get_es_models__no_settings(es_models: pathlib.Path) -> None:
    """Test that default behavior without descriptions is preserved"""
    mapping = {
        "properties": {
            "foo": {"type": "keyword"},
            "bar": {"type": "long"},
        }
    }

    utils.load_model(es_models, "foo", mapping)

    models = gdcmodels.get_es_models()

    assert "foo" in models
    assert "foo" in models["foo"]
    assert {} == models["foo"]["foo"].settings
    assert mapping == models["foo"]["foo"].mappings


def test__get_es_models__empty_descriptions(es_models: pathlib.Path) -> None:
    """Test that empty _meta descriptions are picked up as expected"""
    mapping = {
        "properties": {
            "foo": {"type": "keyword"},
            "bar": {"type": "long"},
        }
    }
    settings: dict = {}

    utils.load_model(es_models, "foo", mapping, settings, descriptions={})

    models = gdcmodels.get_es_models()

    assert "foo" in models
    assert "foo" in models["foo"]
    assert mapping == models["foo"]["foo"].mappings


def test__get_es_models__with_descriptions(es_models: pathlib.Path) -> None:
    mapping = {
        "properties": {
            "foo": {"type": "keyword"},
            "bar": {"type": "long"},
        }
    }
    descriptions = {"this_property": "something"}
    settings: dict = {}

    utils.load_model(es_models, "foo", mapping, settings, descriptions=descriptions)

    models = gdcmodels.get_es_models()

    assert "foo" in models
    assert "foo" in models["foo"]
    assert {"_meta": {"descriptions": descriptions}, **mapping} == models["foo"][
        "foo"
    ].mappings


def test__get_es_models__with_vestigial_properties(es_models: pathlib.Path) -> None:
    mapping = {
        "properties": {
            "foo": {"type": "keyword"},
            "bar": {"type": "long"},
        }
    }
    settings: dict = {}
    vestigial = {
        "dictionary_item_added": {
            "root['properties']['vestigial']": {
                "properties": {
                    "obj": {
                        "properties": {
                            "vestigial_id": {
                                "type": "keyword",
                                "normalizer": "clinical_normalizer",
                            }
                        }
                    }
                }
            }
        }
    }

    utils.load_model(es_models, "foo", mapping, settings, vestigial=vestigial)

    models = gdcmodels.get_es_models()

    assert "foo" in models
    assert "foo" in models["foo"]
    assert {
        "properties": {
            "vestigial": {
                "properties": {
                    "obj": {
                        "properties": {
                            "vestigial_id": {
                                "type": "keyword",
                                "normalizer": "clinical_normalizer",
                            }
                        }
                    }
                }
            },
            **mapping["properties"],
        }
    } == models["foo"]["foo"].mappings


def test__get_es_models__exclude_vestigial_properties(es_models: pathlib.Path) -> None:
    mapping = {
        "properties": {
            "foo": {"type": "keyword"},
            "bar": {"type": "long"},
        }
    }
    settings: dict = {}
    vestigial = {
        "dictionary_item_added": {
            "root['properties']['vestigial']": {
                "properties": {
                    "obj": {
                        "properties": {
                            "vestigial_id": {
                                "type": "keyword",
                                "normalizer": "clinical_normalizer",
                            }
                        }
                    }
                }
            }
        }
    }

    utils.load_model(es_models, "foo", mapping, settings, vestigial=vestigial)

    models = gdcmodels.get_es_models(vestigial_included=False)

    assert "foo" in models
    assert "foo" in models["foo"]
    assert mapping == models["foo"]["foo"].mappings
