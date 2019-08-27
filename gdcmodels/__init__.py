import copy
import os
import pkg_resources
import re
from os.path import isfile, join as pj

import yaml


def load_yaml(filename):
    """Return contents of yaml file as dict"""
    with open(filename, 'r') as f:
        return yaml.safe_load(f)


def load_descriptions(filename):
    descriptions = load_yaml(filename)
    result = {}
    # we can select what properties to add in the future
    if '_meta' in descriptions:
        result['_meta'] = descriptions.get('_meta')
    return result


def get_es_models(es_model_dir=None):
    """
    Return ES settings and mappings as dict with contents from yaml file,
    dict is structured similarly as Elasticsearch's '_settings', '_mapping'
    return

    :param es_model_dir: root directory for gdc ES mappings
    :type es_model_dir: str
    :return: loaded mappings
    """

    if es_model_dir is None:
        es_model_dir = pkg_resources.resource_filename('gdcmodels', 'es-models')

    es_models = {}

    for es_index in os.listdir(es_model_dir):
        if os.path.isfile(os.path.join(es_model_dir, es_index)):
            continue

        for f in os.listdir(os.path.join(es_model_dir, es_index)):
            if es_index not in es_models:
                es_models[es_index] = {
                    '_settings': {}
                }

            if f.endswith('.mapping.yaml'):
                es_type = re.sub(r'\.mapping\.yaml$', '', f)
                es_models[es_index][es_type] = {
                        '_mapping': load_yaml(pj(es_model_dir, es_index, f))
                    }
                desc_path = pj(es_model_dir, es_index, 'descriptions.yaml')
                if isfile(desc_path):
                    descriptions = load_descriptions(desc_path)
                    es_models[es_index][es_type]['_mapping'].update(descriptions)
            elif f == 'settings.yaml':
                es_models[es_index]['_settings'] = load_yaml(
                    os.path.join(es_model_dir, es_index, f)
                )

    return es_models


def comparator(a, b):
    """
    Compare two objects. Override the logic of comparing numeric types, so that
    float and long are treated the same.
    """
    if a == b:
        return True

    number_types = ['long', 'float']

    if a in number_types and b in number_types:
        return True

    return False


def models_diff(mappings_a, mappings_b, ignore_keys=('normalizer',), cmp=None):
    """
    Compare mappings and return their difference. Nested dictionaries that are
    considered "the same" will be removed completely, i.e. if two mappings are
    exactly the same, the result will be an empty dict.

    A custom comparator can be passed in to determine what to treat as the same

    :param mappings_a: input mappings A
    :param mappings_b: input mappings B
    :param ignore_keys: keys to ignore when doing comparison
    :param cmp: callable or None to provide a custom comparator
    :return: Dict - result mappings
    """
    cmp = cmp or comparator

    result = copy.deepcopy(mappings_a)

    for key in ignore_keys:
        result.pop(key, None)

    for key, value in mappings_b.items():
        if key not in result:
            continue

        if cmp(value, result[key]):
            result.pop(key)
            continue

        if isinstance(value, dict):
            nested = models_diff(result[key], value, ignore_keys)
            if not nested:
                result.pop(key)
            else:
                result[key] = nested

    return result
