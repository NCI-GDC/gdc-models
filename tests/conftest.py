import os
import pathlib
import sys
import tempfile
from typing import Callable, Iterator

import elasticsearch
import importlib_resources
import pytest

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources


@pytest.fixture
def es_models(monkeypatch: pytest.MonkeyPatch) -> Iterator[pathlib.Path]:
    """Creates a temporary es-models directory and ensures via patching that it is
    loaded by the resources library.
    """

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = pathlib.Path(tmp_dir)
        models = root / "es-models"

        models.mkdir()
        monkeypatch.setattr(resources, "files", lambda *_: root)

        yield models


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
