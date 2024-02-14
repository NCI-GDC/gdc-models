import os
import pathlib
from typing import Callable, Iterator
import pkg_resources

import elasticsearch
import pytest


@pytest.fixture
def es_models(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """Creates a temporary es-models directory and ensures via patching that it is
    loaded by the resources library.
    """
    models = tmp_path / "es-models"

    models.mkdir()
    monkeypatch.setattr(pkg_resources, "resource_filename", lambda *_: models)

    return models


@pytest.fixture(scope="session")
def es():
    """Create an Elasticsearch client for the test cluster."""
    return elasticsearch.Elasticsearch(
        hosts=[f"{os.getenv('ES_HOST', 'localhost')}:9200"], timeout=30
    )


@pytest.fixture
def index_exists(es: elasticsearch.Elasticsearch) -> Callable[[str], bool]:
    """Returns true if an index exists in elasticsearch."""

    def inner(index: str) -> bool:
        return es.indices.exists(index=index)

    return inner


@pytest.fixture(scope="class")
def clear_test_indices(es: elasticsearch.Elasticsearch) -> Iterator[None]:
    """Remove any ES indices starting with ``test_`` from the test cluster."""
    yield None

    es.indices.delete(index="test_*")
