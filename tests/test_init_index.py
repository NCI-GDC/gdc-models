import contextlib
import sys
from typing import Any, Callable, Iterator, NamedTuple, Optional, Sequence

import elasticsearch
import pytest
import yaml
from typing_extensions import Protocol

import gdcmodels
from gdcmodels import init_index

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources


class Files(NamedTuple):
    mapping: str
    settings: str
    descriptions: Optional[str] = None


class Models:
    """The file paths for all models/indices."""

    class Graph:
        ANNOTATION = Files(
            "es-models/gdc_from_graph/annotation/mapping.yaml",
            "es-models/gdc_from_graph/settings.yaml",
            "es-models/gdc_from_graph/descriptions.yaml",
        )
        CASE = Files(
            "es-models/gdc_from_graph/case/mapping.yaml",
            "es-models/gdc_from_graph/settings.yaml",
            "es-models/gdc_from_graph/descriptions.yaml",
        )
        FILE = Files(
            "es-models/gdc_from_graph/file/mapping.yaml",
            "es-models/gdc_from_graph/settings.yaml",
            "es-models/gdc_from_graph/descriptions.yaml",
        )
        PROJECT = Files(
            "es-models/gdc_from_graph/project/mapping.yaml",
            "es-models/gdc_from_graph/settings.yaml",
            "es-models/gdc_from_graph/descriptions.yaml",
        )

    class Viz:
        CASE_CENTRIC = Files(
            "es-models/case_centric/mapping.yaml", "es-models/case_centric/settings.yaml"
        )
        CNV_CENTRIC = Files(
            "es-models/cnv_centric/mapping.yaml", "es-models/cnv_centric/settings.yaml"
        )
        CNV_OCCURRENCE_CENTRIC = Files(
            "es-models/cnv_occurrence_centric/mapping.yaml",
            "es-models/cnv_occurrence_centric/settings.yaml",
        )
        GENE_CENTRIC = Files(
            "es-models/gene_centric/mapping.yaml", "es-models/gene_centric/settings.yaml"
        )
        SSM_CENTRIC = Files(
            "es-models/ssm_centric/mapping.yaml", "es-models/ssm_centric/settings.yaml"
        )
        SSM_OCCURRENCE_CENTRIC = Files(
            "es-models/ssm_occurrence_centric/mapping.yaml",
            "es-models/ssm_occurrence_centric/settings.yaml",
        )

    class Sets:
        CASE = Files("es-models/case_set/mapping.yaml", "es-models/case_set/settings.yaml")
        FILE = Files("es-models/file_set/mapping.yaml", "es-models/file_set/settings.yaml")
        GENE = Files("es-models/gene_set/mapping.yaml", "es-models/gene_set/settings.yaml")
        SSM = Files("es-models/ssm_set/mapping.yaml", "es-models/ssm_set/settings.yaml")


def load_yaml(resource_name: str) -> dict:
    """Load the YAML data from the given resource."""
    resource = resources.files(gdcmodels) / resource_name

    return yaml.safe_load(resource.read_bytes())


class GetArgs(Protocol):
    """A function for parsing the given arges into a Namespace."""

    def __call__(self, *args: str) -> init_index.Arguments:
        ...


@pytest.fixture(scope="class")
def get_args(es: elasticsearch.Elasticsearch) -> GetArgs:
    """Create a function that parses args for `init_index`.

    Use the actual arg parser because it's less work than writing a dummy args class
    and it's an excuse to boost our test coverage. Add the host/port for the test
    Elasticsearch cluster so we don't have to keep passing that.
    """

    # Assume we only configured one host for the ES client fixture.
    assert es.transport.hosts

    host_info = es.transport.hosts[0]
    es_args = ("--host", host_info["host"], "--port", str(host_info["port"]))

    def parse(*args: str) -> init_index.Arguments:
        actual_args = (*es_args, *args)
        return init_index.get_parser().parse_args(actual_args)

    return parse


Validate = Callable[[str, Files], None]


@pytest.fixture
def validate_index(es: elasticsearch.Elasticsearch) -> Validate:
    """Create a validator for the successful creation and setup of an ES index."""

    def validator(index_name: str, files: Files) -> None:
        """Verify an ES index was created and configured as expected.

        Args:
            index_name: Name of the index to validate.
            files: The model files associated with the given index.
        """
        index_info = es.indices.get(index=index_name)
        assert index_info is not None, f"Index {index_name} does not exist"
        assert index_name in index_info

        expected_mapping = load_yaml(files.mapping)
        if files.descriptions:
            expected_mapping["_meta"] = {"descriptions": load_yaml(files.descriptions)}

        assert index_info[index_name]["mappings"] == expected_mapping

        # Elasticsearch adds some junk to the actual index settings, and we also rely
        # on it to flatten some things out, so just check that a couple things line up
        # rather than try to verify an exact match.
        expected_settings = load_yaml(files.settings)
        actual_settings = index_info[index_name]["settings"]["index"]

        assert int(actual_settings["max_result_window"]) == (
            expected_settings.get("index.max_result_window")
            or expected_settings["index"]["max_result_window"]
        )

        max_terms_count = actual_settings.get("max_terms_count")
        if max_terms_count:
            assert int(max_terms_count) == (
                expected_settings.get("index.max_terms_count")
                or expected_settings["index"]["max_terms_count"]
            )

        if "analysis" in expected_settings:
            assert actual_settings["analysis"] == expected_settings["analysis"]
        else:
            assert "analysis" not in actual_settings

    return validator


@pytest.fixture
def patch_input(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """Create a function to patch user input in the `init_index` module."""

    def apply_patch(user_input: str) -> None:
        def return_input(*args, **kwargs):
            return user_input

        monkeypatch.setattr("builtins.input", return_input)

    return apply_patch


@pytest.mark.parametrize(
    "args",
    (
        ("--prefix", "foo-bar"),
        ("--prefix", "foo-bar", "--host", "localhost"),
        ("--prefix", "foo-bar", "--index", "case_centric"),
        ("--index", "case_centric", "gene_centric"),
        ("--index", "case_centric", "--host", "localhost"),
        ("--host", "localhost"),
    ),
)
def test_get_parser__requires_args(args: Sequence[str]) -> None:
    """Test that `get_parser` aborts if certain arguments are missing."""
    with pytest.raises(SystemExit):
        init_index.get_parser().parse_args(args)


@pytest.fixture(scope="class")
def create_graph_indices(get_args: GetArgs, clear_test_indices: Any) -> None:
    args = get_args("--index", "gdc_from_graph", "--prefix", "test")

    init_index.init_index(args)


@pytest.mark.usefixtures("create_graph_indices")
class TestGraphIndices:
    @pytest.mark.parametrize(
        ("index", "files"),
        (
            pytest.param(
                "test_gdc_from_graph_annotation", Models.Graph.ANNOTATION, id="annotation"
            ),
            pytest.param("test_gdc_from_graph_case", Models.Graph.CASE, id="case"),
            pytest.param("test_gdc_from_graph_file", Models.Graph.FILE, id="file"),
            pytest.param("test_gdc_from_graph_project", Models.Graph.PROJECT, id="project"),
        ),
    )
    @pytest.mark.usefixtures("create_graph_indices")
    def test_init_index__creates_graph_indices(
        self, validate_index: Validate, index: str, files: Files
    ) -> None:
        """Verify `init_index` can create the active graph indices correctly.

        Expect the names to be ``test_gdc_from_graph...`` because that's how the init logic
        works, even though it's not how we'd normally name the indices. We don't normally
        use this init script to create the graph index anyway (we let esbuild do it).
        """
        validate_index(index, files)


@pytest.fixture(scope="class")
def create_set_indices(get_args: GetArgs, clear_test_indices: Any) -> None:
    args = get_args(
        "--index",
        "case_set",
        "file_set",
        "gene_set",
        "ssm_set",
        "awg_centric",  # unknown index
        "--prefix",
        "test_set",
    )

    init_index.init_index(args)


RecreateIndex = Callable[[Sequence[str], Optional[str]], None]


@pytest.fixture
def recreate_index(get_args: GetArgs, patch_input: Callable[[str], None]) -> RecreateIndex:
    def inner(args: Sequence[str], user_input: Optional[str]) -> None:
        if user_input is not None:
            patch_input(user_input)

        init_index.init_index(get_args(*args))

    return inner


@pytest.mark.usefixtures("create_set_indices")
class TestSetsIndices:
    @pytest.fixture(autouse=True)
    def init_fixtures(
        self,
        es: elasticsearch.Elasticsearch,
    ) -> None:
        self._es = es

    @contextlib.contextmanager
    def _create_set(self, index: str, ids: Sequence[str]) -> Iterator[str]:
        response = self._es.index(index=index, document={"ids": ids}, refresh=True)
        id = response["_id"]

        yield id

        self._es.delete(index=index, id=id, ignore=404)

    @pytest.mark.parametrize(
        ("index", "files"),
        (
            pytest.param("test_set_case_set", Models.Sets.CASE, id="case_set"),
            pytest.param("test_set_file_set", Models.Sets.FILE, id="file_set"),
            pytest.param("test_set_gene_set", Models.Sets.GENE, id="gene_set"),
            pytest.param("test_set_ssm_set", Models.Sets.SSM, id="ssm_set"),
        ),
    )
    def test_init_index__creates_set_indices(
        self, validate_index: Validate, index: str, files: Files
    ) -> None:
        """Verify `init_index` can create the saved set indices correctly."""

        validate_index(index, files)

    def test_init_index__ignores_unknown_indices(
        self, index_exists: Callable[[str], bool]
    ) -> None:
        """Confirm unknown indices are ignored, and do not block creating known indices."""
        assert not index_exists("awg_centric")

    def test_init_index__skips_existing_indices(self, recreate_index: RecreateIndex) -> None:
        """Confirm existing indices are not recreated when ``--delete`` is not passed."""

        with self._create_set("test_case_set", ("case-0", "case-1")) as set_id:
            recreate_index(("--index", "case_set", "--prefix", "test"), None)

            assert self._es.exists(index="test_case_set", id=set_id)

    @pytest.mark.parametrize("user_input", ["case_set", "test_case_settee", "NO", ""])
    def test_init_index__skips_if_prompt_doesnt_match(
        self, recreate_index: RecreateIndex, user_input: str
    ) -> None:
        """Confirm ``--delete`` does not delete indices if the confirmation prompt fails."""
        with self._create_set("test_case_set", ("case-0", "case-1")) as set_id:
            recreate_index(("--index", "case_set", "--prefix", "test", "--delete"), user_input)

            assert self._es.exists(index="test_case_set", id=set_id)

    def test_init_index__deletes_if_prompt_matches(self, recreate_index: RecreateIndex) -> None:
        """Confirm ``--delete`` deletes and recreates indices if the prompt passes."""

        with self._create_set("test_case_set", ("case-0", "case-1")) as set_id:
            recreate_index(
                ("--index", "case_set", "--prefix", "test", "--delete"), "test_case_set"
            )

            assert not self._es.exists(index="test_case_set", id=set_id)


@pytest.fixture(scope="class")
def create_viz_indices(get_args: GetArgs, clear_test_indices: Any) -> None:
    args = get_args(
        "--index",
        "case_centric",
        "cnv_centric",
        "cnv_occurrence_centric",
        "gene_centric",
        "ssm_centric",
        "ssm_occurrence_centric",
        "--prefix",
        "test_viz",
    )

    init_index.init_index(args)


@pytest.mark.usefixtures("create_viz_indices")
class TestVizIndices:
    @pytest.mark.parametrize(
        ("index", "files"),
        (
            pytest.param("test_viz_case_centric", Models.Viz.CASE_CENTRIC, id="case_centric"),
            pytest.param("test_viz_cnv_centric", Models.Viz.CNV_CENTRIC, id="cnv_centric"),
            pytest.param(
                "test_viz_cnv_occurrence_centric",
                Models.Viz.CNV_OCCURRENCE_CENTRIC,
                id="cnv_occurrence_centric",
            ),
            pytest.param("test_viz_gene_centric", Models.Viz.GENE_CENTRIC, id="gene_centric"),
            pytest.param("test_viz_ssm_centric", Models.Viz.SSM_CENTRIC, id="ssm_centric"),
            pytest.param(
                "test_viz_ssm_occurrence_centric",
                Models.Viz.SSM_OCCURRENCE_CENTRIC,
                id="ssm_occurrence_centric",
            ),
        ),
    )
    def test_init_index__creates_viz_indices(
        self, validate_index: Validate, index: str, files: Files
    ) -> None:
        """Verify `init_index` can create the visualization indices correctly."""
        validate_index(index, files)
