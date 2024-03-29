import functools
import pathlib

import gdcmodels
from tests import utils


def test__get_es_models__standard_behavior() -> None:
    """
    Test that correct number of index mappings are loaded from es-models.
    """
    models = gdcmodels.get_es_models()

    assert len(models) == 12

    for dtype in ["case", "project", "file", "annotation"]:
        dtype_mapping = models["gdc_from_graph"][dtype].mappings
        assert "_meta" in dtype_mapping, dtype_mapping.keys()
        assert "descriptions" in dtype_mapping["_meta"]
        # The description field below is somewhat random, but something that
        # will most likely preserve during dictionary updates, if this is not
        # the case at some point, update it
        assert "cases.case.project_id" in dtype_mapping["_meta"]["descriptions"]


def test__get_es_models__multiple_indices(es_models: pathlib.Path) -> None:
    """
    Test that content of mappings and settings is correct
    """
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
    """
    Test that default behavior without descriptions is preserved
    """
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
    """
    Test that default behavior without descriptions is preserved
    """
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
    """
    Test that empty _meta descriptions are picked up as expected
    """
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
    assert {"_meta": {"descriptions": descriptions}, **mapping} == models["foo"]["foo"].mappings


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
