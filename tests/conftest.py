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
    try:
        from builtins import str
    except ImportError:
        str = unicode

    f = sub_dir / filename
    f.write_text(str(yaml.dump(d, default_flow_style=False)))

@pytest.fixture
def foo_bar_mappings(tmp_path):
    foo_mapping = {
        'properties': {
            'foo': {'type': 'keyword'},
            'bar': {'type': 'long'},
        }
    }
    foo_settings = {'foo': 1, 'bar': 2}
    foo_dir_name = 'foo_centric'
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
    bar_dir_name = 'bar_centric'
    

    mapps = {'foo': {'mapping': foo_mapping,
                     'settings': foo_settings,
                     'dir': foo_dir_name,
                     'expected': {'mapping': foo_mapping, 'settings': foo_settings}},
             'bar': {'mapping': bar_mapping,
                     'settings': bar_settings,
                     'dir': bar_dir_name,
                     'expected': {'mapping': bar_mapping, 'settings': bar_settings}}
            } 
    root = tmp_path
    return mock_mappings(root, mapps)

def mock_mappings(tmp_path, mappings):
    root = tmp_path
    expected = {}
    for mapping_name, data in mappings.items():
        mapp_dir = root/data['dir']
        mapp_dir.mkdir()
        write_dict_to_yaml(mapp_dir, data['dir']+'.mapping.yaml', data.get('mapping', {}))
        if data.get('settings'):
            write_dict_to_yaml(mapp_dir, 'settings.yaml', data.get('settings',{}))
        if data.get('definitions'):
            write_dict_to_yaml(mapp_dir, 'definitions.yaml', data.get('definitions',{}))
        expected[data['dir']] = {'mapping': data.get('mapping', {}), 'settings': data.get('settings',{})}
    return root, expected


def foo_mapp():
    foo_mapping = {
        'properties': {
            'foo': {'type': 'keyword'},
            'bar': {'type': 'long'},
        }
    }
    foo_dir_name = 'foor_defs'
    return  foo_mapping, foo_dir_name


@pytest.fixture
def defs_mappings(tmp_path):
    
    foo_mapping, foo_dir_name = foo_mapp()
    foo_definitions = {'_meta': 'expected_result'} 
    mapps = {'foo': {'mapping': foo_mapping,
                     'dir': foo_dir_name,
                     'definitions': foo_definitions,
                     'expected': {'mapping': foo_mapping.update(foo_definitions)}}}
    root = tmp_path
    return mock_mappings(root, mapps)


@pytest.fixture
def no_defs_mappings(tmp_path):
    
    foo_mapping, foo_dir_name = foo_mapp()
    mapps = {'foo': {'mapping': foo_mapping,
                     'dir': foo_dir_name,
                     'expected': {'mapping': foo_mapping}}}
    root = tmp_path
    return mock_mappings(root, mapps)

@pytest.fixture
def empty_defs_mappings(tmp_path):
    
    foo_mapping, foo_dir_name = foo_mapp()
    foo_definitions = {} 
    mapps = {'foo': {'mapping': foo_mapping,
                     'dir': foo_dir_name,
                     'definitions': foo_definitions,
                     'expected': {'mapping': foo_mapping}}}
    root = tmp_path
    return mock_mappings(root, mapps)


@pytest.fixture
def other_properties_defs_mappings(tmp_path):
    
    foo_mapping, foo_dir_name = foo_mapp()
    foo_definitions = {'this_property': 'something'} 
    mapps = {'foo': {'mapping': foo_mapping,
                     'dir': foo_dir_name,
                     'definitions': foo_definitions,
                     'expected': {'mapping': foo_mapping}}}
    root = tmp_path
    return mock_mappings(root, mapps)


