#!/bin/bash -e

docs_dir=$1

trigger_commit=$(git rev-parse --short HEAD)

git config --global user.name "${GIT_CONFIG_USER_NAME}"
git config --global user.email "${GIT_CONFIG_USER_MAIL}"

git clone --branch gh-pages "${GIT_URL}" ../DOCS
rm -rf ../DOCS/*
cp -r "${docs_dir}"/_build/* ../DOCS
cd ../DOCS
git add .
if git commit -m "[CI] Updated documentation (ref: ${trigger_commit})."; then
    git push origin gh-pages
fi
