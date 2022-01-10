# -*- coding: utf-8 -*-


import pytest

from sailor.utils.utils import warn_and_log, DataNotFoundWarning


@pytest.mark.parametrize('testdescr,input_for_custom_warning_function', [
    ('Using optional parameter stacklevel',
     {'message': DataNotFoundWarning(), 'logger_name': __name__, 'stacklevel': 2}),
    ('Only mandatory parameters', {'message': 'Minimal warning message', 'logger_name': __name__}),
    ('Using all parameters',
     {'message': 'Warning (all parameters)', 'logger_name': __name__, 'stacklevel': 1, 'category': FutureWarning}),
    ('Using optional parameter category',
     {'message': 'Warning message', 'logger_name': __name__, 'category': FutureWarning})
])
def test_warn_and_log(caplog, input_for_custom_warning_function, testdescr):
    with pytest.warns(None) as record:
        warn_and_log(**input_for_custom_warning_function)

    # check that warning was triggered
    assert len(record) == 1
    assert str(record[0].message) == str(input_for_custom_warning_function['message'])

    # check that message was logged
    assert len(caplog.records) == 1
    assert caplog.records[-1].message == str(input_for_custom_warning_function['message'])
