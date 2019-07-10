import re
import yaml
from os import listdir
import pkg_resources
from os.path import isfile, dirname, join as pj


def load_yaml(filename):
    """Return contents of yaml file as dict"""
    with open(filename, 'r') as f:
        return yaml.safe_load(f)


def process_ref(name, reference, path):
    ref = reference['$ref']
    filename, key = ref.split('#/')
    filedata = load_yaml(pj(path, filename))
    return filedata[key] 


def load_definitions(filename):
    definitions = load_yaml(filename)
    meta = process_ref('_meta', definitions['_meta'], dirname(filename))
    return {'_meta': meta}


def get_es_models():
    """
    Return ES settings and mappings as dict with contents from yaml file,
    dict is structured similarly as Elasticsearch's '_settings', '_mapping' return
    """

    es_model_dir = pkg_resources.resource_filename('gdcmodels', 'es-models')

    es_models = {}

    for es_index in listdir(es_model_dir):
        if isfile(pj(es_model_dir, es_index)): continue

        for f in listdir(pj(es_model_dir, es_index)):
            if not es_index in es_models:
                es_models[es_index] = {
                    '_settings': {}
                }

            if f.endswith('.mapping.yaml'):
                es_type = re.sub(r'\.mapping\.yaml$', '', f)
                es_models[es_index][es_type] = {
                        '_mapping': load_yaml(pj(es_model_dir, es_index, f))
                    }
                defs_name = pj(es_model_dir, es_index,es_type+".".join(['_definitions', 'yaml']))
                if isfile(defs_name):
                    definitions = load_definitions(defs_name)
                    es_models[es_index][es_type]['_mapping'].update(definitions)
            elif f == 'settings.yaml':
                es_models[es_index]['_settings'] = load_yaml(pj(es_model_dir, es_index, f))

    return es_models
