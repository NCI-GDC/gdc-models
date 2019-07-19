import pytest

from init_index import get_parser
from gdcmodels import get_es_models, load_definitions


parser = get_parser()


@pytest.mark.parametrize('input_args', [
    ('--prefix', 'foo-bar'),
    ('--prefix', 'foo-bar', '--host', 'localhost'),
    ('--prefix', 'foo-bar', '--index', 'case_centric'),
    ('--index', 'case_centric gene_centric'),
    ('--index', 'case_centric', '--host', 'localhost'),
    ('--host', 'localhost'),
])
def test_missing_required_args(input_args):
    with pytest.raises(SystemExit):
        parser.parse_args(input_args)


def test_get_es_models_standard_behavior():
    models = get_es_models()

    assert len(models) == 11


def test_get_es_models_parametrized(mock_listdir):
    _, expected = mock_listdir
    models = get_es_models()

    expected_indices = set(expected.keys())

    assert set(models.keys()) == expected_indices
    assert all(set(models[ind].keys()) == expected[ind]
               for ind in models)


def test_get_es_models_from_directory(foo_bar_mappings):
    root, expected = foo_bar_mappings

    mappings = get_es_models(str(root))
    assert set(mappings.keys()) == set(expected.keys())
    for name in mappings:
        assert expected[name]['settings'] == mappings[name]['_settings']
        assert expected[name]['mapping'] == mappings[name][name]['_mapping']


def test_get_models_with_definitions(defs_mappings):
    root, expected = defs_mappings
    mappings = get_es_models(str(root))
    for name, mapping in mappings.items():
        assert expected[name]['mapping'] == mapping[name]['_mapping']


def test_get_models_no_definitions(no_defs_mappings):
    root, expected = no_defs_mappings
    mappings = get_es_models(str(root))
    for name, mapping in mappings.items():
        assert expected[name]['mapping'] == mapping[name]['_mapping']


def test_get_models_empty_definitions(empty_defs_mappings):
    root, expected = empty_defs_mappings
    mappings = get_es_models(str(root))
    for name, mapping in mappings.items():
        assert expected[name]['mapping'] == mapping[name]['_mapping']


def test_get_models_definitions_with_other_data(other_properties_defs_mappings):
    root, expected = other_properties_defs_mappings
    mappings = get_es_models(str(root))
    for name, mapping in mappings.items():
        assert expected[name]['mapping'] == mapping[name]['_mapping']


