[![Build Status](https://travis-ci.org/NCI-GDC/gdc-models.svg)](https://travis-ci.org/NCI-GDC/gdc-models)

# GDC Models

Git repository centrally stores and serves GDC data models defined in static YAML files.

## Setup 'pre-commit' git hook

After 'git clone' this repository, you will need to run 'setup.sh' to install necessary
git hooks to edits to YAML files are valid and well formatted.

```
> ./setup.sh
```

## Update the data models

Edit the YAML files as usual, then commit changes to git. Git 'pre-commit' hook will
validate YAML and ensure it's well formatted.

If YAML validation issue is reported, you will need to resovle them before retrying commit again.

If you are prompted to format the YAML, you can just run:
```
> ./scripts/format_yaml.sh
```
Original YAML file is kept with `.bak` suffix. Before proceed with retrying `git commit`, please `diff` the two files to ensure YAML formatting did not create error.

## Use the data models

Simply clone this repository and fetch YAML files for needed data models.
