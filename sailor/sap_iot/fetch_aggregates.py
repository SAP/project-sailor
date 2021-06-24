"""
Timeseries module can be used to retrieve timeseries data from the SAP iot abstract timeseries api.

This is the equivalent to sap_iot.fetch, except we're retrieving pre-aggregated data from the hot store rather than
raw data from the cold store.
"""

from __future__ import annotations

from typing import Union, Iterable, TYPE_CHECKING
from datetime import datetime
import warnings
import re
import logging
from collections import defaultdict

import pandas as pd

from sailor.utils.timestamps import _any_to_timestamp, _timestamp_to_isoformat
from sailor.assetcentral.indicators import AggregatedIndicatorSet, IndicatorSet
from sailor.sap_iot.wrappers import TimeseriesDataset
from sailor.utils.oauth_wrapper import get_oauth_client
from sailor.sap_iot._common import request_aggregates_url

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())

if TYPE_CHECKING:
    from ..assetcentral.equipment import EquipmentSet


_ALL_KNOWN_AGGREGATION_FUNCTIONS = ['MIN', 'AVG', 'FIRST', 'MAX', 'SUM', 'LAST', 'COUNT',
                                    'PERCENT_GOOD', 'TMAX', 'TLAST', 'STDDEV', 'TFIRST', 'TMIN']


def _compose_query_params(template: str, equipment_set: EquipmentSet,
                          aggregated_indicator_set: AggregatedIndicatorSet,
                          aggregation_interval: str):
    equipment_selector = ' or '.join(f"\"equipmentId\"='{equipment.id}'" for equipment in equipment_set)
    tags_filter = f"({equipment_selector}) and \"templateId\" = '{template}'"

    query_params = {
        'tagsFilter': tags_filter,
    }
    if aggregation_interval:
        query_params['duration'] = aggregation_interval

    select_query_list = [indicator._iot_column_header for indicator in aggregated_indicator_set]
    query_params['select'] = ",".join(select_query_list)

    LOG.debug('Query parameters for aggregate timeseries request: %s', query_params)
    return query_params


def get_indicator_aggregates(start: Union[str, pd.Timestamp, datetime], end: Union[str, pd.Timestamp, datetime],
                             indicator_set: IndicatorSet, equipment_set: EquipmentSet,
                             aggregation_functions: Iterable[str],
                             aggregation_interval: Union[str, pd.Timedelta, datetime.timedelta] = 'PT2M'):
    """Read aggregated indicator data for a certain time period, a set of equipments and a set of indicators."""
    # The data we get from Leonardo IoT is basically the first format below, where columns are identified by
    # indicator_id and aggregation_function, indicator_group and template_id are in a separate column.
    # That is confusing, as it's neither a purely horizonal format nor a purely vertical format.
    # Much of the code below is therefore taking care of conversion from the Leonardo IoT format to our own format
    # which is fully horizontal (ie column headers encode template, indicator group, indicator and aggregation function)
    # Leonardo IoT format is effectively:
    # time | equi - id | equi - model - id | indicator - group - id | template - id | indicator_A_value_AGG
    # x | equi - 1 | model - 1 | indi - group - 1 | template - 1 | 5
    # x | equi - 1 | model - 1 | indi - group - 2 | template - 1 | 15
    #
    # Our format is effectively:
    # time | equi - id | equi - model - id | column_id_1 | columnd_id_2
    # x | equi - 1 | model - 1 | 5 | 15
    # where the column_ids encode all unique identifiers of an aggregated sensor value here
    # column_id = hash(indicator_id + indicator_group_id + template_id + aggregation_function)

    start = _any_to_timestamp(start)
    end = _any_to_timestamp(end)

    query_groups = defaultdict(list)
    for indicator in indicator_set:
        query_groups[(indicator.template_id, indicator._liot_group_id)].append(indicator._liot_id)

    if aggregation_functions is None:
        aggregation_functions = _ALL_KNOWN_AGGREGATION_FUNCTIONS
    aggregated_indicators = AggregatedIndicatorSet._from_indicator_set_and_aggregation_functions(indicator_set,
                                                                                                 aggregation_functions)
    oauth_iot = get_oauth_client('sap_iot')
    df = None
    duration = None

    if aggregation_interval is not None and not isinstance(aggregation_interval, str):
        total_seconds = aggregation_interval.total_seconds()
        aggregation_interval = f'PT{total_seconds}S'

    params = dict(start=_timestamp_to_isoformat(start, True), end=_timestamp_to_isoformat(end, True),
                  equipment_set=equipment_set, aggregated_indicator_set=aggregated_indicators,
                  aggregation_interval=aggregation_interval)

    # doing this as the aggregates api needs to be called for each indicator group
    for (template_id, liot_group_id), group_indicators in query_groups.items():
        LOG.debug("Fetching indicator data. Indicator Group ID: %s.", liot_group_id)
        results = _fetch_aggregates(liot_group_id, template_id, oauth_iot, **params)
        results_df = _prepare_df(results, aggregated_indicators, liot_group_id, template_id)
        if results_df.empty:
            continue
        duration = results[0]['properties']['duration'] if duration is None else duration
        if df is not None:
            df = pd.merge(df, results_df, on=['timestamp', 'equipment_id'], how='outer')
        else:
            df = results_df

    if df is None:
        raise RuntimeError("No data could be found for the given parameters.")

    df['timestamp'] = pd.to_datetime(df['timestamp'])

    d_match = re.match(r'ALL\((.*)\)', duration)
    if d_match:
        duration = d_match.group(1)
    if aggregation_interval is not None and duration != aggregation_interval[1:]:
        # the returned 'duration' is missing the 'P' in front
        warnings.warn(f'The aggregation interval returned by the query ("P{duration}")' +
                      f'does not match the requested aggregation interval ("{aggregation_interval}")')

    return TimeseriesDataset(df, aggregated_indicators, equipment_set, start, end)


def _fetch_aggregates(liot_group_id, template_id, oauth_iot, start, end, **params):
    aggregates_url = request_aggregates_url(liot_group_id, start, end)
    query_params = _compose_query_params(template_id, **params)

    results = []
    response_data = oauth_iot.request("GET", aggregates_url, params=query_params)
    while response_data is not None and len(response_data['results']) > 0:
        results.extend(response_data['results'])
        if next_link := response_data.get('nextLink'):
            LOG.debug('Query incomplete, fetching next page.')
            response_data = oauth_iot.request('GET', next_link)
        else:
            break
    return results


def _prepare_df(results, aggregated_indicators, liot_group_id, template_id) \
        -> pd.DataFrame:
    key_tags = ['equipmentId', 'modelId', 'templateId', 'indicatorGroupId']
    grouped_results = defaultdict(list)
    for row in results:
        key = tuple(row['tags'][k] for k in key_tags)
        grouped_results[key].append(row['properties'])

    all_dfs = []
    for k, v in grouped_results.items():
        df = pd.DataFrame(v)
        for i, key_tag in enumerate(key_tags):
            df[key_tag] = k[i]
        all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()
    tmp = pd.concat(all_dfs)

    column_mapping = {}
    drop_columns = ['templateId', 'indicatorGroupId', 'duration', 'modelId']
    for column in tmp.columns:
        if column.startswith('I_'):
            indicator_candidates = aggregated_indicators.filter(_iot_column_header=column,
                                                                template_id=template_id,
                                                                _liot_group_id=liot_group_id)
            if len(indicator_candidates) == 0:
                LOG.warning('No matching indicator found for %s, ignoring data.', column)
                drop_columns.append(column)
                continue
            assert len(indicator_candidates) == 1, f'More than one indicator matching column {column} found!'
            aggregated_indicator = indicator_candidates[0]
            column_mapping[column] = aggregated_indicator._unique_id

            # this typecasting based on the name of the column is pretty wild...
            # should refactor to do it based on indicator data type
            # but need to somehow combine that with the aggregation function
            if aggregated_indicator.aggregation_function in ['TMIN', 'TMAX', 'TFIRST', 'TLAST']:
                tmp[column] = pd.to_datetime(tmp[column])
            else:  # should always be an aggregated indicator, since we're filtering on 'I_' above.
                tmp[column] = tmp[column].astype('double', errors='ignore')

    results_df = (
        tmp.drop(columns=drop_columns, errors='ignore')
           .rename(columns=column_mapping)
           .rename(columns={'time': 'timestamp', 'equipmentId': 'equipment_id'})
    )

    return results_df
