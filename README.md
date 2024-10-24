[![Build Status](https://travis-ci.org/NCI-GDC/gdc-models.svg)](https://travis-ci.org/NCI-GDC/gdc-models)
[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/f71223e269e64eaaa9f6069ceab526c2)](https://www.codacy.com/manual/NCI-GDC/gdc-models?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=NCI-GDC/gdc-models&amp;utm_campaign=Badge_Grade)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

# GDC Models

Git repository centrally stores and serves GDC data models defined in static YAML files.

- [GDC Models](#gdc-models)
  - [Update the data models](#update-the-data-models)
  - [Use the data models](#use-the-data-models)
    - [Import ES models into Python code](#import-es-models-into-python-code)
    - [Initialize Elasticsearch index settings and mappings using command line script](#initialize-elasticsearch-index-settings-and-mappings-using-command-line-script)
  - [Setup pre-commit hook to check for secrets](#setup-pre-commit-hook-to-check-for-secrets)


## Update the data models

### Sync

Syncing is the process of updating the models with any properties which may be derived from external sources, normalizing keywords, as well as insuring all default mapping values are set. This process should be run after the gdcdictionary is updated and when any new property is added to the viz indices.

The process can be run for any index (-i) and any of its doc-types (-d). Multiple can be specified on the command line and if none are provided for either all of the respective type are run.

#### Install
pip-compile --extra=sync \
            --index-url=https://nexus.osdc.io/repository/pypi-gdc-releases/simple \
            --output-file=requirements-sync.txt \
            --strip-extras \
            --upgrade
pip install -r requirements-sync.txt

#### Before syncing
NOTE: Certain esmodels like `case_centric` are augmented from the mappings in `gdcmodels/esmodels/gdc_from_graph/case`. The mappings from `case` are overlayed on the `case_centric` mappings. This implies that previous sync operations may have added entries into the `case_centric` mapping file. In the situation where vestigial mappings are being removed from `gdc_from_graph/case`, then `case_centric` mappings will have to be hand edited to fully remove the vestigial mappings. Similar scenarios exist for the other `gdc_from_graph` folders.

#### Examples
Run all indices/doc-types:
```bash
sync-models
```

Run all associated doc-types:
```bash
sync-models -i gdc_from_graph -i case_centric
```

Run a singular doc-type:
```bash
sync-models -i gdc_from_graph -d file
```

#### After Syncing
Once the sync has been run, review and commit the generated models. These should
contain all new properties from the graph (graph indices) and all keywords should have
the clinical normalizer applied if appropriate.

### WARNING: YAML & Pre-Commit Hook

Edit the YAML files as usual, then commit changes to git. A pre-commit hook will
validate YAML and ensure it's well formatted. It is important to keep YAML file formatted
consistently, such as using 2 whitespaces for indentation, across all revisions. This
will make change tracking much easier.

If a YAML validation issue is reported, you will need to commit again.

The pre-commit hook will automatically format all new or changed YAML files. A copy of unchanged original YAML file
is kept with `.bak` suffix. Before proceed with retrying `git commit`, please `diff` your original YAML
and the automatically formatted one to ensure YAML formatting did not create any error.

## Use the data models

### Import ES models into Python code

```
from gdcmodels import get_es_models

es_models = get_es_models()
```

### Initialize Elasticsearch index settings and mappings using command line script

```
# get usage information by: python init_index.py -h
# initialize Elasticsearch indexes: case_set and file_set, add prefix 'gdc_r52' to index name
python init_index.py --index case_set file_set --host localhost --prefix gdc_r52
```
