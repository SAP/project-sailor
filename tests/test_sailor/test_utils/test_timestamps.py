import datetime

import pytest
import pandas as pd

from sailor.utils.timestamps import _any_to_timestamp, _calculate_nice_sub_intervals


@pytest.mark.parametrize('testdescription,input,expected', [
    ('iso8601 string',
        '2021-01-01 18:00:00+02:00',
        pd.Timestamp(year=2021, month=1, day=1, hour=16, minute=0, second=0, tz='UTC')),
    ('datetime.datetime',
        datetime.datetime(year=2021, month=1, day=1, hour=16, minute=0, second=0),
        pd.Timestamp(year=2021, month=1, day=1, hour=16, minute=0, second=0, tz='UTC')),
    ('pd.Timestamp',
        pd.Timestamp(year=2021, month=1, day=1, hour=16, minute=0, second=0),
        pd.Timestamp(year=2021, month=1, day=1, hour=16, minute=0, second=0, tz='UTC')),
    ('datetime.date',
        datetime.date(year=2021, month=1, day=1),
        pd.Timestamp(year=2021, month=1, day=1, tz='UTC'))
])
@pytest.mark.filterwarnings('ignore:Trying to parse non-timezone-aware timestamp, assuming UTC.')
def test_any_to_timestamp_types(input, expected, testdescription):
    actual = _any_to_timestamp(input)
    assert actual == expected


def test_calculate_nice_sub_intervals_short_interval_does_not_raise():
    _calculate_nice_sub_intervals(pd.Timedelta('500ms'), 10)


def test_calculate_nice_sub_intervals_single_break_does_not_raise():
    _calculate_nice_sub_intervals(pd.Timedelta('1D'), 1)
    
def test_add_timestampoffset_prefix_added():
    datetime = '2021-01-01 18:00:00'
    expected = "datetimeoffset'2021-01-01T18:00:00Z'"
    actual = _add_timestampoffset(datetime)
    assert actual == expected
