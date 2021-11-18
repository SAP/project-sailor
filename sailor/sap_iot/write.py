"""
Timeseries module can be used to write timeseries data to the SAP iot extension timeseries api.

Currently only a single function to upload a `TimeseriesDataset` is exposed. It will upload the full dataset,
indicator and equipment information is taken from the TimeseriesDataset.
"""


from functools import partial
from collections import defaultdict
import logging

import numpy as np

import sailor.assetcentral.indicators as ac_indicators
from ..utils.timestamps import _timestamp_to_isoformat
from ..utils.oauth_wrapper import get_oauth_client
from .wrappers import TimeseriesDataset
from ._common import request_upload_url

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


# Unfortunately there is no guidance from SAP IoT yet on how much data can be uploaded at once.
# The value of _MAX_PAGE_SIZE below was chosen based on local experiments where data ingestion seemed to work well.
_MAX_PAGE_SIZE = 100000


def _upload_data_single_equipment(data_subset, equipment_id, tags):
    LOG.debug('Uploading data for equipment %s', equipment_id)

    request_url = request_upload_url(equipment_id)
    oauth_iot = get_oauth_client('sap_iot')

    # shape[1] is the number of columns, we want to divide the page size by the number of columns as each column
    # contributes to the payload size
    page_size = max(_MAX_PAGE_SIZE // data_subset.shape[1], 1)
    LOG.debug('Uploading %d rows with page size %d', len(data_subset), page_size)

    for page in (data_subset.iloc[i:i + page_size, :] for i in range(0, len(data_subset), page_size)):
        LOG.debug('Uploading page with size %d', len(page))
        payload = {
            'Tags': tags,
            'Values': page.to_dict(orient='records')
        }
        oauth_iot.request('POST', request_url, json=payload)


def _upload_data_single_indicator_group(dataset, indicator_set, group_id, template_id):
    LOG.debug('Starting upload for %s, %s', group_id, template_id)

    df = dataset.filter(indicator_set=indicator_set).as_df(include_model=False).reset_index()
    df = df.replace({np.nan: None})
    df = (
        df.assign(_time=df['timestamp'].apply(partial(_timestamp_to_isoformat, with_zulu=True)))
          .drop(columns='timestamp')
          .rename(columns={indicator._unique_id: indicator._liot_id for indicator in indicator_set})
    )
    for equipment in dataset.equipment_set:
        data_subset = df.query('equipment_id == @equipment.id').drop(columns=['equipment_id'])
        tags = {
            'indicatorGroupId': group_id,
            'templateId': template_id,
            'equipmentId': equipment.id,
            'modelId': equipment.model_id
        }
        _upload_data_single_equipment(data_subset, equipment.id, tags)


def upload_indicator_data(dataset: TimeseriesDataset):
    """
    Upload a `TimeseriesDataset` to SAP IoT.

    This functionality is currently in BETA. Please report any bugs at https://github.com/SAP/project-sailor/issues.
    The entire dataset will be uploaded. It may not contain any AggregatedIndicators.
    Please note that only some indicators from an IndicatorGroup are present in the dataset, SAP IoT will delete
    any values for the missing indicators for the uploaded timestamps.
    """
    if isinstance(dataset.indicator_set, ac_indicators.AggregatedIndicatorSet):
        raise RuntimeError('TimeseriesDatasets containing aggregated indicators may not be uploaded to SAP IoT')

    query_groups = defaultdict(list)
    for indicator in dataset.indicator_set:
        query_groups[(indicator._liot_group_id, indicator.template_id)].append(indicator)

    for (group_id, template_id), group_indicators in query_groups.items():
        selected_indicator_set = ac_indicators.IndicatorSet(group_indicators)
        _upload_data_single_indicator_group(dataset, selected_indicator_set, group_id, template_id)
