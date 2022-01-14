# -*- coding: utf-8 -*-

import logging

import pytest

from sailor.utils.utils import WarningAdapter, DataNotFoundWarning


@pytest.mark.parametrize('testdescr,input_for_custom_warning_function', [
    ('Using optional parameter stacklevel', {'msg': DataNotFoundWarning(), 'warning_stacklevel': 2}),
    ('Only mandatory parameters', {'msg': 'Minimal warning message'}),
    ('Using optional parameter category', {'msg': 'Warning message', 'warning_category': FutureWarning}),
    ('Using all parameters',
     {'msg': 'Warning (all parameters)', 'warning_stacklevel': 1, 'warning_category': FutureWarning})
])
def test_log_and_warning_from_adapter(caplog, recwarn, input_for_custom_warning_function, testdescr):
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())
    logger = WarningAdapter(logger)
    logger.log_with_warning(**input_for_custom_warning_function)

    # check that warning was triggered
    assert len(recwarn) == 1
    assert str(recwarn[-1].message) == str(input_for_custom_warning_function['msg'])

    # check that message was logged
    assert len(caplog.records) == 1
    assert caplog.records[-1].message == str(input_for_custom_warning_function['msg'])
