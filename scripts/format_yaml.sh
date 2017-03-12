#!/usr/bin/env sh

BASEDIR=$(dirname "$0")

$BASEDIR/git-hooks/pre-commit format
