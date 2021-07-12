#!/usr/bin/env python

import sys
import json

from pydocstyle import check
from pydocstyle.config import ConfigurationParser, IllegalConfiguration

class ReturnCode:
    no_violations_found = 0
    violations_found = 1
    invalid_options = 2

conf = ConfigurationParser()

try:
    conf.parse()
except IllegalConfiguration:
    sys.exit(ReturnCode.invalid_options)

#run_conf = conf.get_user_run_configuration()

errors = []
try:
    for (filename, checked_codes, ignore_decorators) in conf.get_files_to_check():
        errors.extend(
            check(
                (filename,),
                select=checked_codes,
                ignore_decorators=ignore_decorators,
            )
        )
except IllegalConfiguration as error:
    # An illegal configuration file was found during file generation.
    sys.stderr.write(error.args[0])
    sys.exit(ReturnCode.invalid_options)


count = 0

sonar_issues = []

for error in errors:
    if hasattr(error, 'code'):
        sonar_issues.append(
            {
                "engineId": "pydocstyle",
                "ruleId": error.code,
                "severity": "MINOR",
                "type": "CODE_SMELL",
                "primaryLocation": {
                    "message": error.message,
                    "filePath": error.filename,
                    "textRange": {
                        "startLine": error.line,
                        "startColumn": 1,
                    }
                },
                "effortMinutes": 5,
            }
        )
    count += 1


if count == 0:
    exit_code = ReturnCode.no_violations_found
else:
    exit_code = ReturnCode.violations_found

json.dump({"issues": sonar_issues}, sys.stdout)

sys.exit(exit_code)
