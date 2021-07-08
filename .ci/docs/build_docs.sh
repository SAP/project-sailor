#!/bin/bash -e

docs_dir=$1

cd "${docs_dir}"
make apidoc
make html
# due to weird sphinx behaviour we need to "change" the apidoc and re-make the docs otherwise the
# API doc menu on the left side will not be present when viewing an API doc page
touch apidoc.rst
make html SPHINXOPTS="-a"
