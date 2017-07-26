#!/usr/bin/env python

import os
import sys
import addict
from addict import Dict
import ruamel.yaml
import fire
import yaml

from collections import OrderedDict
from ruamel.yaml.util import load_yaml_guess_indent

class YamlUpdater(object):
    """ A class to update various Yaml Files within gdc_from_graph"""

    def elastic_sort(self, items):
        sorted_items = sorted(items)
        # priority
        if 'properties' in sorted_items:
            sorted_items.remove('properties')
            sorted_items.insert(0, 'properties')
        if 'type' in sorted_items:
            sorted_items.remove('type')
            sorted_items.insert(0, 'type')
        return sorted_items

    def sortOD(self, od):
        res = OrderedDict()
        for k, v in self.elastic_sort(od.items()):
            if isinstance(v, dict):
                res[k] = self.sortOD(v)
            else:
                res[k] = v
        return res

    def update_fields(self, yaml_file):
        input_yaml, indent, block_seq = load_yaml_guess_indent(open(yaml_file))

        writeable = Dict(input_yaml)
        writeable.properties.days_to_lost_to_followup.type = 'long'
        writeable.properties.demographic.properties.cause_of_death.type = 'keyword'
        writeable.properties.demographic.properties.days_to_birth.type = 'long'
        writeable.properties.demographic.properties.days_to_death.type = 'long'
        writeable.properties.demographic.properties.vital_status.type = 'keyword'
        writeable.properties.diagnoses.properties.best_overall_response.type = 'keyword'
        writeable.properties.diagnoses.properties.days_to_best_overall_response.type = 'long'
        writeable.properties.diagnoses.properties.days_to_diagnosis.type = 'long'
        writeable.properties.diagnoses.properties.iss_stage.type = 'keyword'
        writeable.properties.diagnoses.properties.overall_survival.type = 'long'
        writeable.properties.diagnoses.properties.progression_free_survival.type = 'long'
        writeable.properties.diagnoses.properties.progression_free_survival_event.type = 'keyword'
        writeable.properties.diagnoses.properties.treatments.properties.regimen_or_line_of_therapy.type = 'keyword'
        writeable.properties.files.properties.cases.properties.days_to_lost_to_followup.type = 'long'
        writeable.properties.files.properties.cases.properties.demographic.properties.cause_of_death.type = 'keyword'
        writeable.properties.files.properties.cases.properties.demographic.properties.days_to_birth.type = 'long'
        writeable.properties.files.properties.cases.properties.demographic.properties.days_to_death.type = 'long'
        writeable.properties.files.properties.cases.properties.demographic.properties.vital_status.type = 'keyword'
        writeable.properties.files.properties.cases.properties.diagnoses.properties.best_overall_response.type = 'keyword'
        writeable.properties.files.properties.cases.properties.diagnoses.properties.days_to_best_overall_response.type = 'long'
        writeable.properties.files.properties.cases.properties.diagnoses.properties.days_to_diagnosis.type = 'long'
        writeable.properties.files.properties.cases.properties.diagnoses.properties.iss_stage.type = 'keyword'
        writeable.properties.files.properties.cases.properties.diagnoses.properties.overall_survival.type = 'long'
        writeable.properties.files.properties.cases.properties.diagnoses.properties.progression_free_survival.type = 'long'
        writeable.properties.files.properties.cases.properties.diagnoses.properties.progression_free_survival_event.type = 'keyword'
        writeable.properties.files.properties.cases.properties.diagnoses.properties.treatments.properties.regimen_or_line_of_therapy.type = 'keyword'
        writeable.properties.files.properties.cases.properties.index_date.type = 'keyword'
        writeable.properties.files.properties.cases.properties.lost_to_followup.type = 'keyword'
        writeable.properties.index_date.type = 'keyword'
        writeable.properties.lost_to_followup.type = 'keyword'



        ruamel.yaml.round_trip_dump(self.sortOD(writeable.to_dict()), open(yaml_file, 'w'),
                            indent=indent, block_seq_indent=block_seq)

if __name__ == '__main__':
    fire.Fire(YamlUpdater)
