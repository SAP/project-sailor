#!/bin/bash -e

docs_dir=$1

trigger_commit=$(git rev-parse --short HEAD)

git clone --branch gh-pages "${GIT_URL}" ../DOCS
rm -rf ../DOCS/*
cp -r "${docs_dir}"/_build/* ../DOCS
pushd ../DOCS
git add .
if git commit -m "[CI] Updated documentation (ref: ${trigger_commit})."; then
    git push origin gh-pages
fi
popd
