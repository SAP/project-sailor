"""
Timeseries module can be used to retrieve timeseries data from the SAP iot abstract timeseries api.

Interfaces for retrieval are aligned with AssetCentral objects such as equipment_set and indicator_set.
Timeseries data is generally stored in a pandas dataframe, wrapped in a convenience class to make it easier
to interact with the data in AssetCentral terms (see wrappers.py for the convenience class).
"""
from __future__ import annotations

from collections import defaultdict
from functools import partial
from datetime import datetime
from typing import TYPE_CHECKING, Union, BinaryIO
import logging
import warnings
import time
import json
import zipfile
import gzip
from io import BytesIO

import pandas as pd

import sailor.assetcentral.indicators as ac_indicators
from ..utils.oauth_wrapper import get_oauth_client, RequestError
from ..utils.timestamps import _any_to_timestamp, _timestamp_to_date_string
from ..utils.config import SailorConfig
from ..utils.utils import DataNotFoundWarning
from .wrappers import TimeseriesDataset

if TYPE_CHECKING:
    from ..assetcentral.indicators import IndicatorSet
    from ..assetcentral.equipment import EquipmentSet

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())

fixed_timeseries_columns = {
    '_TIME': 'timestamp',
    'modelId': 'model_id',
    'equipmentId': 'equipment_id'
}


def _start_bulk_timeseries_data_export(start_date: str, end_date: str, liot_indicator_group: str) -> str:
    LOG.debug("Triggering raw indicator data export for indicator group: %s.", liot_indicator_group)
    oauth_iot = get_oauth_client('sap_iot')
    base_url = SailorConfig.get('sap_iot', 'export_url')  # todo: figure out what to do about these urls
    request_url = f'{base_url}/v1/InitiateDataExport/{liot_indicator_group}?timerange={start_date}-{end_date}'

    resp = oauth_iot.request('POST', request_url)
    return resp['RequestId']


def _check_bulk_timeseries_export_status(export_id: str) -> bool:
    LOG.debug("Checking export status for export id: %s.", export_id)
    oauth_iot = get_oauth_client('sap_iot')
    base_url = SailorConfig.get('sap_iot', 'export_url')  # todo: figure out what to do about these urls
    request_url = f'{base_url}/v1/DataExportStatus?requestId={export_id}'

    resp = oauth_iot.request('GET', request_url)

    if resp['Status'] == 'The file is available for download.':
        return True
    elif resp['Status'] in ['Request for data download is submitted.', 'Request for data download is initiated.']:
        return False
    else:
        raise RuntimeError(resp['Status'])


def _process_one_file(ifile: BinaryIO, indicator_set: IndicatorSet, equipment_set: EquipmentSet) -> pd.DataFrame:
    # each processed file contains data for some time range (one day it seems), one indicator group and all
    # equipment holding any data for that group in that time period.
    # Since the user might not have requested all indicators in the group we'll filter out any results that were not
    # requested. This is complicated by the fact that it's possible that the same indicator_id is present in the
    # indicator_group through two different templates. If it is requested only through one template it needs to be
    # filtered out after parsing the csv into a pandas dataframe, and converting to a
    # columnar format (one column for each (indicator_id, indicator_group_id, template_id)).

    float_types = ['numeric', 'numericflexible']

    selected_equipment_ids = [equipment.id for equipment in equipment_set]  # noqa: F841
    dtypes = {indicator._liot_id: float for indicator in indicator_set if indicator.datatype in float_types}
    dtypes.update({'equipmentId': 'object', 'indicatorGroupId': 'object', 'templateId': 'object'})
    df = pd.read_csv(ifile,
                     usecols=lambda x: x != 'modelId',
                     parse_dates=['_TIME'], date_parser=partial(pd.to_datetime, utc=True, unit='ms', errors='coerce'),
                     dtype=dtypes)

    df = df.pivot(index=['_TIME', 'equipmentId'], columns=['indicatorGroupId', 'templateId'])

    columns_to_keep = {}
    columns_flat = df.columns.to_flat_index()
    for indicator in indicator_set:
        id_tuple = (indicator._liot_id, indicator._liot_group_id, indicator.template_id)
        if id_tuple in columns_flat:
            columns_to_keep[id_tuple] = indicator._unique_id

    df.columns = columns_flat
    df = (
        df.filter(items=columns_to_keep.keys())
          .reset_index()
          .rename(columns=columns_to_keep)
          .rename(columns=fixed_timeseries_columns)
          .query('equipment_id in @selected_equipment_ids')
    )
    return df


def _get_exported_bulk_timeseries_data(export_id: str,
                                       indicator_set: IndicatorSet,
                                       equipment_set: EquipmentSet) -> pd.DataFrame:
    oauth_iot = get_oauth_client('sap_iot')
    base_url = SailorConfig.get('sap_iot', 'download_url')  # todo: figure out what to do about these urls
    request_url = f"{base_url}/v1/DownloadData('{export_id}')"

    resp = oauth_iot.request('GET', request_url, headers={'Accept': 'application/octet-stream'})
    ifile = BytesIO(resp)
    try:
        zip_content = zipfile.ZipFile(ifile)
    except zipfile.BadZipFile:
        raise RuntimeError('Downloaded file is corrupted, can not process contents.')

    frames = []
    for i, inner_file in enumerate(zip_content.filelist):
        # the end marker below allows us to keep updating the current line for a nicer 'progress update'
        print(f'processing compressed file {i + 1}/{len(zip_content.filelist)}', end='\x1b[2K\r')
        gzip_file = zip_content.read(inner_file)
        if not gzip_file:
            continue

        try:
            gzip_content = gzip.GzipFile(fileobj=BytesIO(gzip_file))
            frames.append(_process_one_file(gzip_content, indicator_set, equipment_set))
        except gzip.BadGzipFile:
            raise RuntimeError('Downloaded file is corrupted, can not process contents.')

    if frames:
        return pd.concat(frames)
    else:
        raise RuntimeError('Downloaded File did not have any content.')


def get_indicator_data(start_date: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                       end_date: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                       indicator_set: IndicatorSet, equipment_set: EquipmentSet) -> TimeseriesDataset:
    """
    Read indicator data for a certain time period, a set of equipments and a set of indicators.

    Parameters
    ----------
    start_date:
        Date of beginning of requested timeseries data. Time components of the date will be ignored.
    end_date:
        Date of end of requested timeseries data. Time components of the date will be ignored.
    indicator_set:
        IndicatorSet for which timeseries data is returned.
    equipment_set:
        Equipment set for which the timeseries data is read.

    Example
    -------
    Get the indicator set 'my_indicator_set' timeseries data for equipments in
    the equipment set 'my_equipment_set' for a period from '2020-07-02' to '2021-01-10'::

        get_indicator_data('2020-07-02','2021-01-10', my_indicator_set, my_equipment_set)
    """
    # some notes:
    # the bulk export api *only* works on indicator groups. No filtering for equipment_set or indicator_set.
    # so we always need to download data for the whole group. We filter on individual indicator-template combinations
    # as well as individual equipment in `_process_one_file`.
    if start_date is None or end_date is None:
        raise ValueError("Time parameters must be specified")

    start_date = _any_to_timestamp(start_date)
    end_date = _any_to_timestamp(end_date)

    query_groups = defaultdict(list)
    for indicator in indicator_set:
        query_groups[indicator._liot_group_id].append(indicator)

    request_ids = {}
    for indicator_group, indicator_subset in sorted(query_groups.items()):  # sorted to make query order reproducable
        formatted_start_date = _timestamp_to_date_string(start_date)
        formatted_end_date = _timestamp_to_date_string(end_date)
        try:
            request_id = _start_bulk_timeseries_data_export(formatted_start_date, formatted_end_date, indicator_group)
            request_ids[request_id] = indicator_subset
        except RequestError as e:
            try:
                error_message = json.loads(e.error_text)['message']
            except (json.JSONDecodeError, KeyError):
                raise e

            if error_message == 'Data not found for the requested date range':
                warning = DataNotFoundWarning(
                    f'No data for indicator group {indicator_group} found in the requested time interval!')
                warnings.warn(warning)
                continue
            else:
                raise e

    LOG.info('Data export triggered for %s indicator group(s).', len(query_groups))
    print(f'Data export triggered for {len(query_groups)} indicator group(s).')

    # string (or really uuid?) might be better data types for equipment_id
    # unfortunately, support for native string datatypes in pandas is still experimental
    # and if we cast to string right when reading the csv files it gets 'upcast' back to object
    # in `pivot` and `merge`. Hence we'll just stick with object for now.
    schema = {'equipment_id': 'object', 'timestamp': pd.DatetimeTZDtype(tz='UTC')}
    results = pd.DataFrame(columns=schema.keys()).astype(schema)

    print('Waiting for data export:')
    while request_ids:
        for request_id in list(request_ids):
            if _check_bulk_timeseries_export_status(request_id):
                indicator_subset = ac_indicators.IndicatorSet(request_ids.pop(request_id))

                print(f'\nNow downloading export for indicator group {indicator_subset[0].indicator_group_name}.')
                data = _get_exported_bulk_timeseries_data(request_id, indicator_subset, equipment_set)
                print('\nDownload complete')

                for indicator in indicator_subset:
                    if indicator._unique_id not in data.columns:
                        warning = DataNotFoundWarning(f'Could not find any data for indicator {indicator}')
                        warnings.warn(warning)

                results = pd.merge(results, data, on=['equipment_id', 'timestamp'], how='outer')

        if request_ids:
            time.sleep(5)
            print('.', end='')
    print()

    wrapper = TimeseriesDataset(results, indicator_set, equipment_set, start_date, end_date)
    return wrapper
