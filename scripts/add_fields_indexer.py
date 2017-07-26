#!/usr/bin/env python

import os
import sys
import addict
import ruamel.yaml
import fire

from ruamel.yaml.util import load_yaml_guess_indent

class YamlUpdater(object):
    """ A class to update various Yaml Files within gdc_from_graph"""

    def update_fields(self, yaml_file):
        file_name = yaml_file;
        input_yaml, indent, block_seq = load_yaml_guess_indent(open(file_name))

        writeable = input_yaml['properties']
        writeable['days_to_lost_to_followup']['type'] = 'long'
        writeable['demographic']['properties']['cause_of_death']['type'] = 'keyword'
        writeable['demographic']['properties']['days_to_birth']['type'] = 'long'
        writeable['demographic']['properties']['days_to_death']['type'] = 'long'
        writeable['demographic']['properties']['vital_status']['type'] = 'keyword'
        writeable['diagnoses']['properties']['best_overall_response']['type'] = 'keyword'
        writeable['diagnoses']['properties']['days_to_best_overall_response']['type'] = 'long'
        writeable['diagnoses']['properties']['days_to_diagnosis']['type'] = 'long'
        writeable['diagnoses']['properties']['iss_stage']['type'] = 'keyword'
        writeable['diagnoses']['properties']['overall_survival']['type'] = 'long'
        writeable['diagnoses']['properties']['progression_free_survival']['type'] = 'long'
        writeable['diagnoses']['properties']['progression_free_survival_event']['type'] = 'keyword'
        writeable['diagnoses']['properties']['treatments']['properties']['regimen_or_line_of_therapy']['type'] = 'keyword'
        writeable['files']['properties']['cases']['properties']['days_to_lost_to_followup']['type'] = 'long'
        writeable['files']['properties']['cases']['properties']['demographic']['properties']['cause_of_death']['type'] = 'keyword'
        writeable['files']['properties']['cases']['properties']['demographic']['properties']['days_to_birth']['type'] = 'long'
        writeable['files']['properties']['cases']['properties']['demographic']['properties']['days_to_death']['type'] = 'long'
        writeable['files']['properties']['cases']['properties']['demographic']['properties']['vital_status']['type'] = 'keyword'
        writeable['files']['properties']['cases']['properties']['diagnoses']['properties']['best_overall_response']['type'] = 'keyword'
        writeable['files']['properties']['cases']['properties']['diagnoses']['properties']['days_to_best_overall_response']['type'] = 'long'
        writeable['files']['properties']['cases']['properties']['diagnoses']['properties']['days_to_diagnosis']['type'] = 'long'
        writeable['files']['properties']['cases']['properties']['diagnoses']['properties']['iss_stage']['type'] = 'keyword'
        writeable['files']['properties']['cases']['properties']['diagnoses']['properties']['overall_survival']['type'] = 'long'
        writeable['files']['properties']['cases']['properties']['diagnoses']['properties']['progression_free_survival']['type'] = 'long'
        writeable['files']['properties']['cases']['properties']['diagnoses']['properties']['progression_free_survival_event']['type'] = 'keyword'
        writeable['files']['properties']['cases']['properties']['diagnoses']['properties']['treatments']['properties']['regimen_or_line_of_therapy']['type'] = 'keyword'
        writeable['files']['properties']['cases']['properties']['index_date']['type'] = 'keyword'
        writeable['files']['properties']['cases']['properties']['lost_to_followup']['type'] = 'keyword'
        writeable['index_date']['type'] = 'keyword'
        writeable['lost_to_followup']['type'] = 'keyword'
        ruamel.yaml.round_trip_dump(writeable, open('output.yaml', 'w'),
                            indent=indent, block_seq_indent=block_seq)

if __name__ == '__main__':
    fire.Fire(YamlUpdater)
