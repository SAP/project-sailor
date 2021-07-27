#!/bin/bash -e

linter=$1
args=$2

# open new descriptor(3) and make it the only one descriptor to write to stdout. point regular stdout to stderr.
# => only the linting program will write to stdout when we point its output to descriptor(3), everything else goes to stderr.
# => now you can do "./run_lint.sh pydocstyle > pydocstyle.out" and get only the linter output.
exec 3>&1
exec 1>&2

GIT_REMOTE="$(git remote show | head -n 1)"
GIT_MASTER_COMMIT=$(git log -n 1 --pretty=format:"%H" "${GIT_REMOTE}"/main)
GIT_LAST_COMMIT=$(git rev-parse HEAD)

file_filter='\.py$'
# exclude tests directory when linting with pydocstyle
if [[ "${linter}" == *pydocstyle* ]]; then
  file_filter='^(?!tests/).*\.py$'
fi
pyfiles=$(git --no-pager diff --diff-filter=ACMRTUXB --name-only "${GIT_MASTER_COMMIT}" "${GIT_LAST_COMMIT}" | grep -P "${file_filter}" | tr '\n' ' ') || true

ret_code=0
if [[ -n "${pyfiles}" ]]; then
  # write the run-command to descriptor(3) which was set up to write to stdout
  run_command="${linter} ${args} ${pyfiles}"
  eval "${run_command}" >&3 || ret_code=1
else
  echo 'No py file changes detected. Skipping linting.'
fi

if [ ${ret_code} -eq 0 ]; then
  echo "RUN SUCCESSFUL for ${linter}."
else
  echo "RUN FAILED for ${linter}."
  echo "You need to fix the issues, before you can merge your PR."
fi

exit "${ret_code}"
