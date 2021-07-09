#!/bin/sh -e

linter=$1
args=$2

GIT_REMOTE="$(git remote show | head -n 1)"
GIT_MASTER_COMMIT=$(git log -n 1 --pretty=format:"%H" "${GIT_REMOTE}"/main)
GIT_LAST_COMMIT=$(git rev-parse HEAD)

file_filter='\.py$'
# exclude tests directory when linting with pydocstyle
if [ "${linter}" = "pydocstyle" ]; then
  file_filter='^(?!tests/).*\.py$'
  alias pydocstyle='python .ci/pydocstyle_wrapper.py'
fi
pyfiles=$(git --no-pager diff --diff-filter=ACMRTUXB --name-only "${GIT_MASTER_COMMIT}" "${GIT_LAST_COMMIT}" | grep -P "${file_filter}" | tr '\n' ' ') || true

ret_code=0
if [ -n "${pyfiles}" ]; then
  run_command="${linter} ${args} ${pyfiles}"
  eval "${run_command}" || ret_code=1
else
  echo 'No py file changes detected. Skipping linting.'
fi

# if [ ${ret_code} -eq 0 ]; then
#   echo "RUN SUCCESSFUL for ${linter}."
# else
#   echo "RUN FAILED for ${linter}."
#   echo "You need to fix the issues, before you can merge your PR."
# fi

exit "${ret_code}"
