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
    """
    Test that arguments are parsed correctly
    """
    with pytest.raises(SystemExit):
        parser.parse_args(input_args)


def test_get_es_models_standard_behavior():
    """
    Test that correct number of index mappings are loaded
    """
    models = get_es_models()

    assert len(models) == 12

    for dtype in ['case', 'project', 'file', 'annotation']:
        dtype_mapping = models['gdc_from_graph'][dtype]['_mapping']
        assert '_meta' in dtype_mapping, dtype_mapping.keys()
        assert 'descriptions' in dtype_mapping['_meta']
        # The description field below is somewhat random, but something that
        # will most likely preserve during dictionary updates, if this is not
        # the case at some point, update it
        assert 'cases.case.project_id' in dtype_mapping['_meta']['descriptions']


def test_get_es_models_parametrized(mock_listdir):
    """
    Test that correct mappings are created
    """
    _, expected = mock_listdir
    models = get_es_models()

    expected_indices = set(expected.keys())

    assert set(models.keys()) == expected_indices
    assert all(set(models[ind].keys()) == expected[ind]
               for ind in models)


def test_get_es_models_from_directory(foo_bar_mappings):
    """
    Test that content of mappings and settings is correct
    """
    root, expected = foo_bar_mappings

    mappings = get_es_models(str(root))
    assert set(mappings.keys()) == set(expected.keys())
    for name in mappings:
        assert expected[name]['settings'] == mappings[name]['_settings']
        assert expected[name]['mapping'] == mappings[name][name]['_mapping']


def test_get_models_with_descriptions(descriptions_mappings):
    """
    Test that descriptions are being loaded as expected
    """
    root, expected = descriptions_mappings
    mappings = get_es_models(str(root))
    for name, mapping in mappings.items():
        assert expected[name]['mapping'] == mapping[name]['_mapping']


def test_get_models_no_descriptions(no_descriptions_mappings):
    """
    Test that default behavior without descriptions is preserved
    """
    root, expected = no_descriptions_mappings
    mappings = get_es_models(str(root))
    for name, mapping in mappings.items():
        assert expected[name]['mapping'] == mapping[name]['_mapping']


def test_get_models_empty_descriptions(empty_descriptions_mappings):
    """
    Test that empty _meta descriptions are picked up as expected
    """
    root, expected = empty_descriptions_mappings
    mappings = get_es_models(str(root))
    for name, mapping in mappings.items():
        assert expected[name]['mapping'] == mapping[name]['_mapping']


def test_get_models_descriptions_with_other_data(non_meta_descriptions_mappings):
    """
    Test that non _meta descriptions are not being picked up
    """
    root, expected = non_meta_descriptions_mappings
    mappings = get_es_models(str(root))
    for name, mapping in mappings.items():
        assert expected[name]['mapping'] == mapping[name]['_mapping']
