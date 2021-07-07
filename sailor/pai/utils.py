"""Module for various utility functions, in particular those related to fetching data from remote oauth endpoints."""

import logging
import warnings

from ..utils.oauth_wrapper import get_oauth_client
from ..utils.config import SailorConfig
from ..utils.utils import DataNotFoundWarning
from ..assetcentral.utils import AssetcentralEntity, _compose_queries

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


def _pai_application_url():
    """Return the PredictiveAssetInsights (PAI) application URL from the SailorConfig."""
    return SailorConfig.get('predictive_asset_insights', 'application_url')


class PredictiveAssetInsightsEntity(AssetcentralEntity):
    """Common base class for Pai entities."""

    def __repr__(self) -> str:
        """Return a very short string representation."""
        return f'"{self.__class__.__name__}(id="{self.id}")'
