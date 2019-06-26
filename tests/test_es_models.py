import pytest

from init_index import get_parser
from gdcmodels import get_es_models


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

    assert mappings.keys() == expected.keys()
    assert all(
        expected[name]['settings'] == mappings[name]['_settings'] and
        expected[name]['mapping'] == mappings[name][name]['_mapping']
        for name in mappings
    ), mappings
