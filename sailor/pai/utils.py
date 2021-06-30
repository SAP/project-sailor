"""Module for various utility functions, in particular those related to fetching data from remote oauth endpoints."""

import logging
import warnings

import pandas as pd

from ..utils.oauth_wrapper import get_oauth_client
from ..utils.config import SailorConfig
from ..utils.utils import DataNotFoundWarning
from ..assetcentral.utils import _compose_queries

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


def _fetch_data(endpoint_url, unbreakable_filters=(), breakable_filters=()):
    """Retrieve data from the pai service."""
    filters = _compose_queries(unbreakable_filters, breakable_filters)
    oauth_client = get_oauth_client('pai')

    if not filters:
        filters = ['']

    result = []
    for filter_string in filters:
        params = {'$filter': filter_string} if filter_string else {}
        params['$format'] = 'json'

        endpoint_data = oauth_client.request('GET', endpoint_url, params=params)

        if isinstance(endpoint_data, list):
            result.extend(endpoint_data)
        else:
            result.append(endpoint_data)

    if len(result) == 0:
        warnings.warn(DataNotFoundWarning(), stacklevel=2)
    return result

def _pai_application_url():
    """Return the Pai application URL from the SailorConfig."""
    return SailorConfig.get('pai', 'application_url')


class PaiEntity:
    """Common base class for Pai entities."""

    def __init__(self, ac_json: dict):
        """Create a new entity."""
        self.raw = ac_json

    def __repr__(self) -> str:
        """Return a very short string representation."""
        name = getattr(self, 'name', getattr(self, 'short_description', None))
        return f'"{self.__class__.__name__}(name="{name}", id="{self.id}")'

    def __eq__(self, obj):
        """Compare two objects based on instance type and id."""
        return isinstance(obj, self.__class__) and obj.id == self.id

    def __hash__(self):
        """Hash of a pai object is the hash of it's id."""
        return self.id.__hash__()