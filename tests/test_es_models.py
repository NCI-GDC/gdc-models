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


def test_get_es_models_from_directory(mock_mappings):
    root, expected = mock_mappings

    mappings = get_es_models(str(root))

    assert set(mappings.keys()) == set(expected.keys())

    for name in mappings:
        assert expected[name]['settings'] == mappings[name]['_settings']
        assert expected[name]['mapping'] == mappings[name][name]['_mapping']


def test_get_models_with_definitions(add_def_file):
    mappings = get_es_models()
    assert mappings['gdc_from_graph']['case']['_mapping']['_meta'] == 'expected_result'


def test_get_models_no_definitions(remove_def_file):
    mappings = get_es_models()
    assert '_meta' not in mappings['gdc_from_graph']['case']['_mapping'].keys()


def test_get_models_empty_definitions(remove_def_file):
    mappings = get_es_models()
    assert '_meta' not in mappings['gdc_from_graph']['case']['_mapping'].keys()


def test_get_models_missing_definitions_file(missing_def_file):
    with pytest.raises(IOError):
        definitions = load_definitions('definitions.yaml')

