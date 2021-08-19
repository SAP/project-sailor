"""Module for various utility functions, in particular those related to fetching data from remote oauth endpoints."""


from sailor import _base
from ..utils.config import SailorConfig


def _pai_application_url():
    """Return the PredictiveAssetInsights (PAI) application URL from the SailorConfig."""
    return SailorConfig.get('predictive_asset_insights', 'application_url')


class _PredictiveAssetInsightsField(_base.MasterDataField):
    pass


class PredictiveAssetInsightsEntity(_base.MasterDataEntity):
    """Common base class for PAI entities."""

    def __repr__(self) -> str:
        """Return a very short string representation."""
        return f'"{self.__class__.__name__}(id="{self.id}")'


class PredictiveAssetInsightsEntitySet(_base.MasterDataEntitySet):
    """Common base class for PAI entity collections."""

    pass
