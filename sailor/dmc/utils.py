"""Module for various utility functions, in particular those related to fetching data from remote oauth endpoints."""

import logging
import warnings

from sailor import _base
from ..utils.config import SailorConfig
from ..utils.oauth_wrapper.clients import get_oauth_client
from ..utils.utils import DataNotFoundWarning

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


def _dmc_application_url():
    """Return the Digital Manufacturing Cloud application URL from the SailorConfig."""
    return SailorConfig.get('dmc', 'application_url')


def _dmc_fetch_data(endpoint_url, filters={}, filter_fields={}):
    """Fetch data from the Digital Manufacturing Cloud API."""
    oauth_client = get_oauth_client('dmc')

    query_params = {}
    not_our_term = []

    for k, v in filters.items():
        if k in filter_fields.keys():
            key = filter_fields[k]
        else:
            key = k
            not_our_term.append(key)

        query_params[key] = str(v)

    if len(not_our_term) > 0:
        warnings.warn(f'Following parameters are not in our terminology: {not_our_term}', stacklevel=3)

    result = oauth_client.request('GET', endpoint_url, params=query_params)

    if len(result) == 0:
        warnings.warn(DataNotFoundWarning(), stacklevel=2)

    return result


class _DigitalManufacturingCloudField(_base.MasterDataField):
    """Specify a field in Digital Manufacturing Cloud."""

    pass


class DigitalManufacturingCloudEntity(_base.MasterDataEntity):
    """Common base class for DMC entities."""

    pass


class DigitalManufacturingCloudEntitySet(_base.MasterDataEntitySet):
    """Baseclass to be used in all Sets of DMC objects."""

    pass
