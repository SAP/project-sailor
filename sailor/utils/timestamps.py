"""Utility functions for timestamp parsing."""

import datetime
import warnings

import pandas as pd


def _odata_to_timestamp_parser(name):
    return lambda self: pd.Timestamp(float(self.raw[name][6:-2])/1000, tz='UTC') if self.raw[name] else None


def _string_to_timestamp_parser(name, unit=None):
    return lambda self: pd.Timestamp(self.raw[name], unit=unit, tz='UTC') if self.raw[name] else None


def _any_to_timestamp(value, default: pd.Timestamp = None):
    """Try to parse a timestamp provided in a variety of formats into a uniform representation as pd.Timestamp."""
    if value is None:
        return default

    if isinstance(value, str):
        timestamp = pd.Timestamp(value)
    elif isinstance(value, datetime.datetime):
        timestamp = pd.Timestamp(value)
    elif isinstance(value, datetime.date):
        timestamp = pd.Timestamp(value)
    elif isinstance(value, pd.Timestamp):
        timestamp = value
    else:
        raise RuntimeError('Can only parse ISO 8601 strings, pandas timestamps or python native timestamps.')

    if timestamp.tzinfo:
        timestamp = timestamp.tz_convert('UTC')
    else:
        warnings.warn('Trying to parse non-timezone-aware timestamp, assuming UTC.', stacklevel=2)
        timestamp = timestamp.tz_localize('UTC', ambiguous='NaT', nonexistent='NaT')

    return timestamp


def _timestamp_to_isoformat(timestamp: pd.Timestamp):
    """Return an iso-format string of a timestamp after conversion to UTC and without the timezone information."""
    if timestamp.tzinfo:
        timestamp = timestamp.tz_convert('UTC')
    return timestamp.tz_localize(None).isoformat()


def _timestamp_to_date_string(timestamp: pd.Timestamp):
    """Return a date-string (YYYY-MM-DD) from a pandas Timestamp."""
    if timestamp.tzinfo:
        timestamp = timestamp.tz_convert('UTC')
    timestamp = timestamp.tz_localize(None)
    if timestamp.date() != timestamp:
        warnings.warn('Casting timestamp to date, this operation will loose time-of-day information.')
    return str(timestamp.date())


def _calculate_nice_sub_intervals(interval, n_breaks):
    # helper to calculate 'nice' intervals breaking a given interval into *at least* n_breaks sub-intervals.
    # it would be nice to have weeks/months rather than the 7d/30d but that seems tricky --
    # see eg https://github.com/pandas-dev/pandas/issues/15303
    good_intervals = ['1s', '5s', '15s', '1min', '5min', '15min', '1h', '4h', '12h', '1d', '3d', '7d', '30d']
    good_intervals = [pd.Timedelta(x) for x in good_intervals]

    target_break_interval = interval / n_breaks
    target_break_interval = max(target_break_interval, min(good_intervals))
    freq = max(filter(lambda x: x <= target_break_interval, good_intervals))
    return freq
