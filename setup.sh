#!/usr/bin/env sh

set -efu

printf "Install Python library for PyYAML ... "
pip install PyYAML
printf "done!\n"

printf "Setting up pre-commit git hook ... "
cd .git/hooks/
ln -s ../../scripts/git-hooks/pre-commit .
cd ../../
printf "done!\n"
