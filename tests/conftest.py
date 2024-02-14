import os
import pathlib
from typing import Callable, Iterator

import elasticsearch
import importlib_resources
import pytest


@pytest.fixture
def es_models(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    models = tmp_path / "es-models"

    models.mkdir()
    monkeypatch.setattr(importlib_resources, "files", lambda _: tmp_path)

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
