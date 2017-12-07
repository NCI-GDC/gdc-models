import re
import yaml
from os import listdir
import pkg_resources
from os.path import isfile, join as pj


def load_yaml(filename):
    """Return contents of yaml file as dict"""
    with open(filename, 'r') as f:
        return yaml.safe_load(f)


def get_es_models():
    """
    Return ES settings and mappings as dict with contents from yaml file,
    dict is structured similarly as Elasticsearch's '_settings', '_mapping' return
    """

    es_model_dir = pkg_resources.resource_filename('gdcmodels', 'gdcmodels/data')

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

            elif f == 'settings.yaml':
                es_models[es_index]['_settings'] = load_yaml(pj(es_model_dir, es_index, f))

    return es_models
