"""Module for various utility functions, in particular those related to fetching data from remote oauth endpoints."""


from sailor import _base
from ..utils.config import SailorConfig


def _pai_fetch_data(endpoint_url, unbreakable_filters=(), breakable_filters=()):
    return _base.fetch_data('predictive_asset_insights', _pai_response_handler,
                            endpoint_url, unbreakable_filters, breakable_filters)


def _pai_application_url():
    """Return the PredictiveAssetInsights (PAI) application URL from the SailorConfig."""
    return SailorConfig.get('predictive_asset_insights', 'application_url')


def _pai_response_handler(result_list, endpoint_data):
    for element in endpoint_data['d']['results']:
        result_list.append(element)
    return result_list


class _PredictiveAssetInsightsField(_base.MasterDataField):
    pass


class PredictiveAssetInsightsEntity(_base.MasterDataEntity):
    """Common base class for PAI entities."""

    pass


class PredictiveAssetInsightsEntitySet(_base.MasterDataEntitySet):
    """Common base class for PAI entity collections."""

    pass
