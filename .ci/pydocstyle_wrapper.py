#!/usr/bin/env python
"""Wrapper script for pydocstyle that is used generate a custom report for SonarCloud."""
# this file was modified from the original pydocstyle cli.py

import sys
import json

from pydocstyle import check
from pydocstyle.config import ConfigurationParser, IllegalConfiguration


conf = ConfigurationParser()


try:
    conf.parse()
except IllegalConfiguration:
    sys.exit(2)

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
    sys.stderr.write(error.args[0])
    sys.exit(2)


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

exit_code = 0
if len(errors) > 0:
    exit_code = 1

json.dump({"issues": sonar_issues}, sys.stdout)
sys.exit(exit_code)
