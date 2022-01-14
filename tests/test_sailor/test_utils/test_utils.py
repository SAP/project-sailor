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


def call_adapter_directly(logger, msg, stacklevel):
    logger.warning(msg, stacklevel=stacklevel)
    logger.error(msg, stacklevel=stacklevel)
    logger.info(msg, stacklevel=stacklevel)
    with pytest.warns(UserWarning):
        logger.log_with_warning(msg)


def call_adapter_indirectly(logger, msg, stacklevel):
    call_adapter_directly(logger, msg, stacklevel)


@pytest.mark.parametrize('testdescr,stacklevel,funcName_original,funcName_custom', [
    ('Call functions on adapter directly', 1, 'call_adapter_directly', 'call_adapter_directly'),
    ('Call functions on adapter indirectly', 2, 'call_adapter_indirectly', 'call_adapter_directly')
])
def test_stacklevel_for_logging_adapter(caplog, stacklevel, funcName_original, funcName_custom, testdescr):
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.INFO)
    logger = WarningAdapter(logger)

    call_adapter_indirectly(logger, "Message text", stacklevel)

    assert caplog.records[0].funcName == funcName_original  # when logger.warning is called
    assert caplog.records[1].funcName == funcName_original  # when logger.error is called
    assert caplog.records[2].funcName == funcName_original  # when logger.info is called
    assert caplog.records[3].funcName == funcName_custom    # when logger.log_with_warning is called
