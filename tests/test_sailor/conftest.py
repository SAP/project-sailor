from unittest.mock import patch

import pytest

from sailor.assetcentral.indicators import Indicator, IndicatorSet, AggregatedIndicator, AggregatedIndicatorSet
from sailor.assetcentral.equipment import Equipment, EquipmentSet


@pytest.fixture()
def mock_config():
    with patch('sailor.utils.config.SailorConfig') as mock:
        yield mock


@pytest.fixture
def mock_request(mock_config):
    with patch('sailor.utils.oauth_wrapper.OAuthServiceImpl.OAuth2Client.request') as mock:
        yield mock


@pytest.fixture
def make_indicator():
    def maker(**kwargs):
        kwargs.setdefault('propertyId', 'id')
        kwargs.setdefault('pstid', 'group_id')
        kwargs.setdefault('categoryID', 'template_id')
        return Indicator(kwargs)
    return maker


@pytest.fixture
def make_indicator_set(make_indicator):
    def maker(**kwargs):
        indicator_defs = [dict() for _ in list(kwargs.values())[0]]
        for k, values in kwargs.items():
            for i, value in enumerate(values):
                indicator_defs[i][k] = value
        return IndicatorSet([make_indicator(**x) for x in indicator_defs])
    return maker


@pytest.fixture
def make_aggregated_indicator():
    def maker(aggregation_function='mean', **kwargs):
        kwargs.setdefault('propertyId', 'id')
        kwargs.setdefault('pstid', 'group_id')
        kwargs.setdefault('categoryID', 'template_id')
        return AggregatedIndicator(kwargs, aggregation_function)
    return maker


@pytest.fixture
def make_aggregated_indicator_set(make_aggregated_indicator):
    def maker(**kwargs):
        indicator_defs = [dict() for _ in list(kwargs.values())[0]]
        for k, values in kwargs.items():
            for i, value in enumerate(values):
                indicator_defs[i][k] = value
        return AggregatedIndicatorSet([make_aggregated_indicator(**x) for x in indicator_defs])
    return maker


@pytest.fixture
def make_equipment():
    def maker(**kwargs):
        kwargs.setdefault('equipmentId', 'equipment_id_1')
        return Equipment(kwargs)
    return maker


@pytest.fixture
def make_equipment_set(make_equipment):
    def maker(**kwargs):
        equipment_defs = [dict() for _ in list(kwargs.values())[0]]
        for k, values in kwargs.items():
            for i, value in enumerate(values):
                equipment_defs[i][k] = value
        return EquipmentSet([make_equipment(**x) for x in equipment_defs])
    return maker
