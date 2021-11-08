"""Module for various utility functions, in particular those related to fetching data from remote oauth endpoints."""

import json
import warnings
import pandas as pd

from sailor import _base
from ...utils.config import SailorConfig
from ...utils.oauth_wrapper import get_oauth_client
from ...utils.utils import DataNotFoundWarning

def _dc_fetch_data(endpoint_url, unbreakable_filters=(), breakable_filters=()) -> list:
    """Retrieve data from a supported REST service (The IoT device connectivity API).

    A response_handler function needs to be passed which must extract the results
    returned from the odata service endpoint response into a list.
    """
    filters = _base._compose_queries(unbreakable_filters, breakable_filters)
    oauth_client = get_oauth_client('sap_iot')

    if not filters:
        filters = ['']

    result = []
    for filter_string in filters:
        result_filter = []

        # device connectivity api requires 'filter' and not '$filter', which is why the base fetch_data method cannot be called
        params = {'filter': filter_string} if filter_string else {}

        endpoint_data = oauth_client.request('GET', endpoint_url, params=params)
        result_filter = _dc_response_handler(result_filter, endpoint_data)

        result.extend(result_filter)

    if len(result) == 0:
        warnings.warn(DataNotFoundWarning(), stacklevel=2)

    return result

def _dc_response_handler(result_list, endpoint_data) -> list:
    """
    Converting the API response into a list representation.
    """
    if isinstance(endpoint_data, bytes):
        endpoint_data = json.loads(endpoint_data.decode('utf-8')) # why do i get a byte string? ac request returns a dict object here
    if isinstance(endpoint_data, list):
        result_list.extend(endpoint_data)
    else:
        result_list.append(endpoint_data)
    return result_list

def _device_connectivity_api_url():
    """Return the SAP IoT Device Connectivity API URL from the SailorConfig."""
    return SailorConfig.get('sap_iot', 'device_connectivity_url')

class _DeviceConnectivityField(_base.MasterDataField):
    """Specify a field in Device Connectivity."""

    pass

class DeviceConnectivityEntity(_base.MasterDataEntity):
    """Common base class for Device Connectivity entities."""

    pass

class DeviceConnectivityEntitySet(_base.MasterDataEntitySet):
    """Baseclass to be used in all Sets of Device Connectivity objects."""

    def as_df(self, columns=None, explode:list=None, expand_dict:bool=False) -> pd.DataFrame:
        """
        Return all information on the objects stored in the DeviceConnectivityEntitySet as a pandas dataframe.

        Overwriting the base method and support exploding nested lists and expanding nested json objects in the dataframe.

        Parameters
        ----------
        columns 
            Columns to include in the dataframe. Defaults to None. If no columns provided, include all.
        explode
            Explode columns in the dataframe, which contain a list value. Specify the column names to explode. Defaults to None.
        expand_dict 
            Whether to expand nested objects in the dataframe into multiple columns. Each object key will be a new column. Defaults to False.
        """
        df = super().as_df(columns=columns)
        if explode:
            for column in explode:
                df = df.explode(column, ignore_index=True)
                if expand_dict:
                    df = pd.concat([df.drop(column, axis=1), pd.json_normalize(df[column]).add_prefix(column + '_')], axis=1)
        return df
