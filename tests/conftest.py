import os
import pkg_resources

import pytest
import yaml

import gdcmodels


def sample_listdir():
    es_mappings_dir = pkg_resources.resource_filename('gdcmodels', 'es-models')

    dir_structs = [
        {
            'case_centric': ['case_centric.mapping.yaml', 'settings.yaml'],
            'foo_bar': ['foo_bar.txt', 'foo_bar.py'],
            'case_set': ['case_set.mapping.yaml', 'settings.yaml'],
            'gene_centric': ['gene_centric.mapping.yaml', 'settings.yaml'],
        },
        {
            'another': ['another.mapping.yaml', 'settings.yaml'],
            'foo_bar': ['foo_bar.mapping.yaml', 'settings.yaml'],
            'case_set': ['case_set.foo.bar', 'settings.yaml'],
            'gene_centric': ['gene_centric.mapping.yaml', 'settings.yaml'],
        }
    ]

    expected = [
        {
            'case_centric': {'case_centric', '_settings'},
            'case_set': {'case_set', '_settings'},
            'gene_centric': {'gene_centric', '_settings'},
            'foo_bar': {'_settings'},
        },
        {
            'another': {'another', '_settings'},
            'foo_bar': {'foo_bar', '_settings'},
            'case_set': {'_settings'},
            'gene_centric': {'gene_centric', '_settings'},
        }
    ]

    mock_ls = []
    for ls in dir_structs:
        dir_content = {
            os.path.join(es_mappings_dir, key): value
            for key, value in ls.items()
        }
        dir_content[es_mappings_dir] = list(ls.keys())

        mock_ls.append(dir_content)

    return zip(mock_ls, expected)


@pytest.fixture(params=sample_listdir())
def mock_listdir(request, monkeypatch, mock_load_yaml):
    monkeypatch.setattr(os, 'listdir',
                        lambda path: request.param[0].get(path, []))

    return request.param[0], request.param[1]


@pytest.fixture
def mock_load_yaml(monkeypatch):
    monkeypatch.setattr(gdcmodels, 'load_yaml', lambda x: {})


def write_dict_to_yaml(sub_dir, filename, d):
    f = sub_dir / filename
    f.write_text(yaml.dump(d, default_flow_style=False))


@pytest.fixture
def mock_mappings(tmp_path):
    root = tmp_path

    foo_mapping = {
        'properties': {
            'foo': {'type': 'keyword'},
            'bar': {'type': 'long'},
        }
    }
    foo_settings = {'foo': 1, 'bar': 2}

    bar_mapping = {
        'properties': {
            'foo': {
                'type': 'nested',
                'properties': {
                    'foofoo': {'type': 'keyword'},
                    'foobar': {'type': 'keyword'},
                }
            },
            'bar': {'type': 'long'},
        }
    }
    bar_settings = {'foo': 2, 'bar': 4}

    foo_dir = root / 'foo_centric'
    foo_dir.mkdir()

    write_dict_to_yaml(foo_dir, 'foo_centric.mapping.yaml', foo_mapping)
    write_dict_to_yaml(foo_dir, 'settings.yaml', foo_settings)

    bar_dir = root / 'bar_centric'
    bar_dir.mkdir()

    write_dict_to_yaml(bar_dir, 'bar_centric.mapping.yaml', bar_mapping)
    write_dict_to_yaml(bar_dir, 'settings.yaml', bar_settings)

    expected = {
        'foo_centric': {'mapping': foo_mapping, 'settings': foo_settings},
        'bar_centric': {'mapping': bar_mapping, 'settings': bar_settings}
    }
    return root, expected
