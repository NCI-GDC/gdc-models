import pkg_resources

import pytest
import yaml

from gdcmodels import init_index


pytestmark = pytest.mark.usefixtures("clear_test_indices")


def load_yaml(package_name, resource_name):
    """Load the YAML data from the given resource."""
    with pkg_resources.resource_stream(package_name, resource_name) as yaml_in:
        return yaml.safe_load(yaml_in)


@pytest.fixture(scope="session")
def get_args(es):
    """Create a function that parses args for `init_index`.

    Use the actual arg parser because it's less work than writing a dummy args class
    and it's an excuse to boost our test coverage. Add the host/port for the test
    Elasticsearch cluster so we don't have to keep passing that.
    """

    # Assume we only configured one host for the ES client fixture.
    host_info = es.transport.hosts[0]
    es_args = ["--host", host_info["host"], "--port", str(host_info["port"])]

    def parse(*args):
        actual_args = es_args + list(args)
        return init_index.get_parser().parse_args(actual_args)

    return parse


@pytest.fixture(scope="session")
def validate_index(es):
    """Create a validator for the successful creation and setup of an ES index."""

    def validator(
        index_name, mapping_resource, settings_resource, descriptions_resource=None
    ):
        """Verify an ES index was created and configured as expected.

        Args:
            index_name (str): Name of the index to validate.
            mapping_resource (str): Resource name with expected mapping YAML.
            settings_resource (str): Resource name with expected settings YAML.
            descriptions_resource (optional(str)): Resource name with expected
                descriptions YAML, or None to expect no descriptions.
        """
        index_info = es.indices.get(index_name)
        assert index_info is not None, "Index {} does not exist".format(index_name)
        assert index_name in index_info

        expected_mapping = load_yaml("gdcmodels", mapping_resource)
        if descriptions_resource:
            expected_mapping.update(load_yaml("gdcmodels", descriptions_resource))

        assert index_info[index_name]["mappings"] == expected_mapping

        # Elasticsearch adds some junk to the actual index settings, and we also rely
        # on it to flatten some things out, so just check that a couple things line up
        # rather than try to verify an exact match.
        expected_settings = load_yaml("gdcmodels", settings_resource)
        actual_settings = index_info[index_name]["settings"]["index"]

        assert (
            int(actual_settings["max_result_window"])
            == expected_settings["index.max_result_window"]
        )

        max_terms_count = actual_settings.get("max_terms_count")
        if max_terms_count:
            assert int(max_terms_count) == expected_settings["index.max_terms_count"]

        if "analysis" in expected_settings:
            assert actual_settings["analysis"] == expected_settings["analysis"]
        else:
            assert "analysis" not in actual_settings

    return validator


@pytest.fixture
def preexisting_case_set(es, clear_test_indices):
    """Create a ``test_case_set`` index with the case index's mapping and settings.

    Explicitly depend on ``clear_test_indices`` to force the right fixture order.
    """
    mapping = load_yaml("gdcmodels", "es-models/gdc_from_graph/case.mapping.yaml")
    settings = load_yaml("gdcmodels", "es-models/gdc_from_graph/settings.yaml")
    es.indices.create("test_case_set", body={"mappings": mapping, "settings": settings})


@pytest.fixture
def patch_input(monkeypatch):
    """Create a function to patch user input in the `init_index` module."""

    def apply_patch(user_input):
        def return_input(*args, **kwargs):
            return user_input

        monkeypatch.setattr("gdcmodels.init_index.input", return_input)

    return apply_patch


@pytest.mark.parametrize('args', [
    ['--prefix', 'foo-bar'],
    ['--prefix', 'foo-bar', '--host', 'localhost'],
    ['--prefix', 'foo-bar', '--index', 'case_centric'],
    ['--index', 'case_centric', 'gene_centric'],
    ['--index', 'case_centric', '--host', 'localhost'],
    ['--host', 'localhost'],
])
def test_get_parser__requires_args(args):
    """Test that `get_parser` aborts if certain arguments are missing."""
    with pytest.raises(SystemExit):
        init_index.get_parser().parse_args(args)


def test_init_index__creates_graph_indices(get_args, validate_index):
    """Verify `init_index` can create the active graph indices correctly.

    Expect the names to be ``test_gdc_from_graph...`` because that's how the init logic
    works, even though it's not how we'd normally name the indices. We don't normally
    use this init script to create the graph index anyway (we let esbuild do it).
    """
    args = get_args("--index", "gdc_from_graph", "--prefix", "test")
    init_index.init_index(args)

    validate_index(
        index_name="test_gdc_from_graph_annotation",
        mapping_resource="es-models/gdc_from_graph/annotation.mapping.yaml",
        settings_resource="es-models/gdc_from_graph/settings.yaml",
        descriptions_resource="es-models/gdc_from_graph/descriptions.yaml",
    )
    validate_index(
        index_name="test_gdc_from_graph_case",
        mapping_resource="es-models/gdc_from_graph/case.mapping.yaml",
        settings_resource="es-models/gdc_from_graph/settings.yaml",
        descriptions_resource="es-models/gdc_from_graph/descriptions.yaml",
    )
    validate_index(
        index_name="test_gdc_from_graph_file",
        mapping_resource="es-models/gdc_from_graph/file.mapping.yaml",
        settings_resource="es-models/gdc_from_graph/settings.yaml",
        descriptions_resource="es-models/gdc_from_graph/descriptions.yaml",
    )
    validate_index(
        index_name="test_gdc_from_graph_project",
        mapping_resource="es-models/gdc_from_graph/project.mapping.yaml",
        settings_resource="es-models/gdc_from_graph/settings.yaml",
        descriptions_resource="es-models/gdc_from_graph/descriptions.yaml",
    )


def test_init_index__creates_set_indices(get_args, validate_index):
    """Verify `init_index` can create the saved set indices correctly."""
    args = get_args(
        "--index", "case_set", "file_set", "gene_set", "ssm_set", "--prefix", "test_set"
    )
    init_index.init_index(args)

    validate_index(
        index_name="test_set_case_set",
        mapping_resource="es-models/case_set/case_set.mapping.yaml",
        settings_resource="es-models/case_set/settings.yaml",
    )
    validate_index(
        index_name="test_set_file_set",
        mapping_resource="es-models/file_set/file_set.mapping.yaml",
        settings_resource="es-models/file_set/settings.yaml",
    )
    validate_index(
        index_name="test_set_gene_set",
        mapping_resource="es-models/gene_set/gene_set.mapping.yaml",
        settings_resource="es-models/gene_set/settings.yaml",
    )
    validate_index(
        index_name="test_set_ssm_set",
        mapping_resource="es-models/ssm_set/ssm_set.mapping.yaml",
        settings_resource="es-models/ssm_set/settings.yaml",
    )


def test_init_index__creates_viz_indices(get_args, validate_index):
    """Verify `init_index` can create the visualization indices correctly."""
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

    validate_index(
        index_name="test_viz_case_centric",
        mapping_resource="es-models/case_centric/case_centric.mapping.yaml",
        settings_resource="es-models/case_centric/settings.yaml",
    )
    validate_index(
        index_name="test_viz_cnv_centric",
        mapping_resource="es-models/cnv_centric/cnv_centric.mapping.yaml",
        settings_resource="es-models/cnv_centric/settings.yaml",
    )
    validate_index(
        index_name="test_viz_cnv_occurrence_centric",
        mapping_resource=(
            "es-models/cnv_occurrence_centric/cnv_occurrence_centric.mapping.yaml"
        ),
        settings_resource="es-models/cnv_occurrence_centric/settings.yaml",
    )
    validate_index(
        index_name="test_viz_gene_centric",
        mapping_resource="es-models/gene_centric/gene_centric.mapping.yaml",
        settings_resource="es-models/gene_centric/settings.yaml",
    )
    validate_index(
        index_name="test_viz_ssm_centric",
        mapping_resource="es-models/ssm_centric/ssm_centric.mapping.yaml",
        settings_resource="es-models/ssm_centric/settings.yaml",
    )
    validate_index(
        index_name="test_viz_ssm_occurrence_centric",
        mapping_resource=(
            "es-models/ssm_occurrence_centric/ssm_occurrence_centric.mapping.yaml"
        ),
        settings_resource="es-models/ssm_occurrence_centric/settings.yaml",
    )


def test_init_index__ignores_unknown_indices(get_args, validate_index):
    """Confirm unknown indices are ignored, and do not block creating known indices."""
    args = get_args(
        "--index", "awg_centric", "case_set", "cnv_set", "file_set", "--prefix", "test"
    )
    init_index.init_index(args)

    validate_index(
        index_name="test_case_set",
        mapping_resource="es-models/case_set/case_set.mapping.yaml",
        settings_resource="es-models/case_set/settings.yaml",
    )
    validate_index(
        index_name="test_file_set",
        mapping_resource="es-models/file_set/file_set.mapping.yaml",
        settings_resource="es-models/file_set/settings.yaml",
    )


@pytest.mark.usefixtures("preexisting_case_set")
def test_init_index__skips_existing_indices(get_args, validate_index):
    """Confirm existing indices are not recreated when ``--delete`` is not passed."""
    args = get_args("--index", "case_set", "--prefix", "test")
    init_index.init_index(args)

    # The preexisting test_case_set should have the graph case mapping/settings.
    validate_index(
        index_name="test_case_set",
        mapping_resource="es-models/gdc_from_graph/case.mapping.yaml",
        settings_resource="es-models/gdc_from_graph/settings.yaml",
    )


@pytest.mark.parametrize("user_input", ["case_set", "test_case_settee", "NO", ""])
@pytest.mark.usefixtures("preexisting_case_set")
def test_init_index__skips_if_prompt_doesnt_match(
    get_args, validate_index, patch_input, user_input
):
    """Confirm ``--delete`` does not delete indices if the confirmation prompt fails."""
    patch_input(user_input)

    args = get_args("--index", "case_set", "--prefix", "test", "--delete")
    init_index.init_index(args)

    validate_index(
        index_name="test_case_set",
        mapping_resource="es-models/gdc_from_graph/case.mapping.yaml",
        settings_resource="es-models/gdc_from_graph/settings.yaml",
    )


@pytest.mark.usefixtures("preexisting_case_set")
def test_init_index__deletes_if_prompt_matches(get_args, validate_index, patch_input):
    """Confirm ``--delete`` deletes and recreates indices if the prompt passes."""
    patch_input("test_case_set")

    args = get_args("--index", "case_set", "--prefix", "test", "--delete")
    init_index.init_index(args)

    # init_index should have recreated the case set index with the proper settings.
    validate_index(
        index_name="test_case_set",
        mapping_resource="es-models/case_set/case_set.mapping.yaml",
        settings_resource="es-models/case_set/settings.yaml",
    )
