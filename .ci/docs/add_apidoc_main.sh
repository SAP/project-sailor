#!/bin/bash -e

docs_dir=$1

trigger_commit=$(git rev-parse --short HEAD)

git add "${docs_dir}"/apidoc
if git commit -m "[CI] Updated apidoc rst files (ref: ${trigger_commit})."; then
    git push origin HEAD:main
fi
