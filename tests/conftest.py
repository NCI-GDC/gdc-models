import os
import pkg_resources

import pytest

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
