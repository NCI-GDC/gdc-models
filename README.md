[![Build Status](https://travis-ci.org/NCI-GDC/gdc-models.svg)](https://travis-ci.org/NCI-GDC/gdc-models)
[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/f71223e269e64eaaa9f6069ceab526c2)](https://www.codacy.com/manual/NCI-GDC/gdc-models?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=NCI-GDC/gdc-models&amp;utm_campaign=Badge_Grade)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

# GDC Models

Git repository centrally stores and serves GDC data models defined in static YAML files.

- [GDC Models](#gdc-models)
  - [Structure of esmodels directory](#structure-of-esmodels-directory)
  - [Update the data models](#update-the-data-models)
    - [Sync](#sync)
    - [WARNING: YAML \& Pre-Commit Hook](#warning-yaml--pre-commit-hook)
  - [Use the data models](#use-the-data-models)
    - [Import ES models into Python code](#import-es-models-into-python-code)
    - [Initialize Elasticsearch index settings and mappings using command line script](#initialize-elasticsearch-index-settings-and-mappings-using-command-line-script)

## Structure of esmodels directory
For each index, there are three files that are created and stored under the esmodels/<index_name> directory:
- mapping.yaml
  - The elasticsearch properties are declared here
- settings.yaml
  - The elasticserach index-specific settings are declared here
- vestigial.yaml
  - For properties that are removed from the graph, we do not want to break gdcapi/portal functionality if they issue an elasticsearch query with a property that is no longer in the graph. This file
contains all properties that have been removed from mappings.yaml but are still needed to maintain backwards compatibility. It is expected for elasticsearch queries to return no data for
the vestigial properties.

## Update the data models

### Sync

Within `gdcmodels` there are index mappings for two sets of indices which are often referred to by group, the graph and viz indices. The graph indices are comprised of the annotation, case, file, and project indices. As for the viz indices, these are the case_centric, cnv_centric, cnv_occurrence_centric, gene_centric, segment_cnv_centric, segment_cnv_occurrence_centric, ssm_centric, and the ssm_occurrence_centric indices. The graph and viz indices' mappings are based on several structures including statically defined properties but also pull some of their structure and properties from the GDC graph and nodes therein. Hence, these mappings need to be updated with any new properties from their associated nodes whenever the `gdcdictionary` is updated; preferably this should be done within the context of the dictionary release. This update is referred to as the `gdcmodels`'s "sync" process.

#### How it works.
As stated above, each of the graph/viz mapping structures are derived from data in the graph nodes. Specifically, properties as defined for the dictionary node's json schema. However, that is only one source of our mappings. Other portions of the mapping are completely manually maintained as static mappings. In order to better segregate the various functionality and sources for the mappings, the sync process merges several overlays each representing different components and properties which need to be combined in order to create the final mapping for a graph or viz index. Below is a high-level example of how this overlay system works.

<table>
  <tr>
    <th>Overlay 1</th>
    <th>Overlay 2</th>
    <th>Resulting Mapping</th>
  </tr>
  <tr>
    <td align="left" valign="top">
      <pre><code>properties:
  <mark>autocomplete</mark>
    <mark>lowercase:</mark>
      <mark>analyzer: lowercase_keyword</mark>
      <mark>type: text</mark>
  id:
    <mark>copy_to:</mark>
      <mark>- autocomplete</mark>
      </code></pre>
    </td>
    <td align="left" valign="top">
      <pre><code>properties:
  id:
    <mark>type: keyword</mark>
      </code></pre>
    </td>
    <td align="left" valign="top">
      <pre><code>properties:
  # From Overlay 1
  <mark>autocomplete:</mark>
    <mark>lowercase:</mark>
      <mark>analyzer: lowercase_keyword</mark>
      <mark>type: text</mark>
  id:
    # From Overlay 1
    <mark>copy_to:</mark>
      <mark>- autocomplete</mark>
    # From Overlay 2
    <mark>type: keyword</mark>
      </code></pre>
    </td>
  </tr>
</table>

#### Overlays
All of the overlays for the sync process can be found within the [src/gdcmodels/sync/overlays](src/gdcmodels/sync/overlays) directory & are generally stored as yaml files. They are further subdivided by the functionality that they add to the mapping as well as the index grouping with which they are associated. Below are the details of the various overlay categories.
- **autocomplete**: The autocomplete overlay defines the autocomplete field for each index as well as all of the properties which will be copied to that autocomplete field.
- **graph**: This overlay generates dynamically all mappings which are ultimately based on nodes and their associated properties as defined in `gdcdictionary`/`gdcdatamodel2`. This includes both `_meta` and `properties` values. For the `_meta` mapping, it supplies the `definitions` which the API's graphql functionality uses to annotate the fields within the graphql schema. Further, it adds an `arrays` value which is a list of all paths that are array values and need to be handled as such when loading and handling the data (this is not something that elasticsearch denotes in the mapping itself as it has no concept of a collection in the mapping.) This functionality is used in mutation indexer to ensure these values are loaded properly via the elasticsearch spark integration. Finally, This overlay includes all of the `properties` which are directly loaded from the graph data via its nodes. These properties are structured into their denormalized tree structures. This is the only overlay which is generated at runtime and is _not_ stored as a yaml file.
- **headers**: The headers overlay defines any static non-property fields which need to be defined for each index. This includes such things as `properties` values which will be excluded from the `_source` as well as ensuring that the elasticsearch `_size` module is configured for the index.
- **static**: This overlay defines all static `properties` for the index. These field will be generated in either esbuild or mutation-indexer when the data is built but supplemental to the data found in the graph.

#### Clinical Normalizer
The only element which works outside of the overlay system is the application of the clinical normalizer which is added after all overlays have been combined. This [normalizer](https://www.elastic.co/docs/reference/text-analysis/normalizers) is used to help standardize the searchable terms exposed by the index and is applied to basically every keyword property. Each index group however excludes a set of properties by name. In the table below, an `X` denotes that the property is _excluded_ from being normalized for that index group.

| Property | Graph | Viz |
| :------- | :---: | :-: |
| biotype | X | X |
| case_submitter_id | X |  |
| code | X | X |
| consequence_type | X | X |
| data_type | X | X |
| entity_submitter_id | X |  |
| experimental_strategy | X | X |
| gene_id | X | X |
| name | X | X |
| program | X | X |
| program_name | X | X |
| project | X | X |
| project_code | X | X |
| project_id | X | X |
| project_name | X | X |
| submitter_id | X | X |
| uuid | X | X |
| workflow_type | X | X |

#### Vestigial properties
After the entire sync process runs, including the application of the clinical normalizer, we generate the vestigial properties for a given index. These properties allow us to supplement the actual mapping with all properties which were removed during the sync process (or any previous sync if the vestigial properties file already contained data.) The models need to load these vestigial properties in places like the API for ensuring backwards compatibility for clients of the API who may be requesting the fields which were ultimately removed. These vestigial properties can be included when loading the models by setting the `vestigial_included` flag to `True`.

```python
models = gdcmodels.get_es_models(vestigial_included=True)
```

#### CLI
- Run sync for all indices.
```bash
uv run -m gdcmodels.sync
```
- Run sync for subset of indices.
```bash
uv run -m gdcmodels.sync --indices annotation case file project
```

#### After Syncing
Once the sync has been run, review and commit the generated models. These should
contain all new properties from the graph (graph indices) and all keywords should have
the clinical normalizer applied if appropriate.

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
