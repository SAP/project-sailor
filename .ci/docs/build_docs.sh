#!/bin/bash -e

docs_dir=$1

cd "${docs_dir}"
make html
touch apidoc.rst
make html SPHINXOPTS="-a"
