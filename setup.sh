#!/usr/bin/env sh

set -efu

if [ ! -d .git ]; then
  printf "You need to run setup.sh from within the git repo\n"
  exit
fi

printf "Install Python library for PyYAML ...\n"
pip install PyYAML
printf "done!\n"

printf "Setting up pre-commit git hook ... "

mkdir -p .git/hooks/

# delete pre-commit if for whatever reason exist already
rm -f .git/hooks/pre-commit

cd .git/hooks/
ln -s ../../scripts/git-hooks/pre-commit .

cd ../../
printf "done!\n"
