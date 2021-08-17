"""Module for various utility functions, in particular those related to fetching data from remote oauth endpoints."""


from ..utils.config import SailorConfig
from .._base.masterdata import MasterDataField, MasterDataEntity, MasterDataEntityCollection


def _pai_application_url():
    """Return the PredictiveAssetInsights (PAI) application URL from the SailorConfig."""
    return SailorConfig.get('predictive_asset_insights', 'application_url')


class _PredictiveAssetInsightsField(MasterDataField):
    pass


class PredictiveAssetInsightsEntity(MasterDataEntity):
    """Common base class for PAI entities."""

    def __repr__(self) -> str:
        """Return a very short string representation."""
        return f'"{self.__class__.__name__}(id="{self.id}")'


class PredictiveAssetInsightsEntityCollection(MasterDataEntityCollection):
    """Common base class for PAI entity collections."""

    pass
