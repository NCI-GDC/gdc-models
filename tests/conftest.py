import os
import pathlib
import tempfile
from collections.abc import Callable, Iterator
from importlib import resources
from typing import Any

import elasticsearch
import pytest
from testcontainers import compose


@pytest.fixture(scope="session")
def services() -> Iterator[None]:
    if os.environ.get("CI"):
        yield
        return

    docker_resource = resources.files("tests") / "docker"

    with (
        resources.as_file(docker_resource) as docker_dir,
        compose.DockerCompose(docker_dir) as services,
    ):
        es_port = services.get_service_port("elasticsearch", 9200)
        os.environ["ES_HOST"] = "localhost"
        os.environ["ES_PORT"] = str(es_port)

        yield


@pytest.fixture
def es_models(monkeypatch: pytest.MonkeyPatch) -> Iterator[pathlib.Path]:
    """Creates a temporary esmodels directory and ensures via patching that it is
    loaded by the resources library.
    """

    with tempfile.TemporaryDirectory() as tmp_dir:
        models = pathlib.Path(tmp_dir)

        monkeypatch.setattr(resources, "files", lambda *_: models)

        yield models


@pytest.fixture(scope="session")
def es(services: Any) -> Iterator[elasticsearch.Elasticsearch]:
    """Create an Elasticsearch client for the test cluster."""
    with elasticsearch.Elasticsearch(
        hosts=[
            {
                "host": os.getenv("ES_HOST", "localhost"),
                "port": int(os.getenv("ES_PORT", "9200")),
            }
        ],
        timeout=30,
    ) as client:
        yield client


@pytest.fixture
def index_exists(es: elasticsearch.Elasticsearch) -> Callable[[str], bool]:
    """Returns true if an index exists in elasticsearch."""

    def inner(index: str) -> bool:
        return es.indices.exists(index=index)

    return inner


@pytest.fixture
def alias_exists(es: elasticsearch.Elasticsearch) -> Callable[[str], bool]:
    """Returns true if an alias exists in elasticsearch."""

    def inner(name: str) -> bool:
        return es.indices.exists_alias(name=name)

    return inner


@pytest.fixture(scope="class")
def clear_test_indices(es: elasticsearch.Elasticsearch) -> Iterator[None]:
    """Remove any ES indices starting with ``test_`` from the test cluster."""
    yield None

    indices = es.indices.get(index="test_*", expand_wildcards="all", allow_no_indices=True)

    es.indices.delete(index=list(indices.keys()))
