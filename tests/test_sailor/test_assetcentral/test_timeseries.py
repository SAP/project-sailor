from unittest.mock import patch

import pytest

from sailor.assetcentral import timeseries
from sailor.assetcentral.equipment import Equipment, EquipmentSet
from sailor.assetcentral.indicators import Indicator, IndicatorSet


@pytest.fixture(scope='module', autouse=True)
def mock_config():
    with patch('sailor.utils.config.SailorConfig') as mock:
        yield mock


@pytest.fixture()
def equi_set():
    equi1 = Equipment({'equipmentId': 'equi_id_1'})
    equi2 = Equipment({'equipmentId': 'equi_id_2'})
    equi_set = EquipmentSet([equi1, equi2])
    return equi_set


class TestFeatureDetails:

    @pytest.fixture
    def indicators(self):
        return [Indicator({'propertyId': 'indicator1', 'categoryID': 'template1', 'pstid': 'group_id1',
                           'indicatorName': 'indicator ONE', 'indicatorGroupName': 'group ONE'}),
                Indicator({'propertyId': 'indicator2', 'categoryID': 'template1', 'pstid': 'group_id1',
                           'indicatorName': 'indicator TWO', 'indicatorGroupName': 'group ONE'})]

    def test_put_with_overwrite(self):
        fd = timeseries.FeatureDetails()
        expected = {
            'column1': {
                'indicator': 'indicator3',
                'aggregation_function': 'aggregation_function3'
            },
            'column2': {
                'indicator': 'indicator2',
                'aggregation_function': 'aggregation_function2'
            }
        }

        fd.put('column1', 'indicator1', 'aggregation_function1')
        fd.put('column2', 'indicator2', 'aggregation_function2')
        fd.put('column1', 'indicator3', 'aggregation_function3')

        assert fd._details == expected

    def test_magic_add_two_instances(self):
        fd1 = timeseries.FeatureDetails()
        fd1.put('column1', 'indicator1', 'aggregation_function1')
        fd2 = timeseries.FeatureDetails()
        fd2.put('column2', 'indicator2', 'aggregation_function2')
        expected = {
            'column1': {
                'indicator': 'indicator1',
                'aggregation_function': 'aggregation_function1'
            },
            'column2': {
                'indicator': 'indicator2',
                'aggregation_function': 'aggregation_function2'
            }
        }

        fd = fd1 + fd2

        assert fd._details == expected

    def test_magic_add_two_instances_with_common_columns(self):
        fd1 = timeseries.FeatureDetails()
        fd1.put('column1', 'indicator1', 'aggregation_function1')
        fd1.put('column2', 'indicator2', 'aggregation_function2')
        fd2 = timeseries.FeatureDetails()
        fd2.put('column2', 'indicator33', 'aggregation_function33')

        with pytest.raises(ValueError):
            fd1 + fd2

    def test_get_name_mapping(self, indicators):
        fd = timeseries.FeatureDetails()
        fd.put('column1', indicators[0], 'aggregation_function1')
        fd.put('column2', indicators[0], 'aggregation_function2')
        expected = {'column1': ('template1', 'group ONE', 'indicator ONE', 'aggregation_function1'),
                    'column2': ('template1', 'group ONE', 'indicator ONE', 'aggregation_function2')}

        actual = fd.get_name_mapping()

        assert actual == expected

    def test_get_id_mapping(self, indicators):
        fd = timeseries.FeatureDetails()
        fd.put('column1', indicators[0], 'aggregation_function1')
        fd.put('column2', indicators[0], 'aggregation_function2')
        expected = {'column1': ('template1', 'group_id1', 'indicator1', 'aggregation_function1'),
                    'column2': ('template1', 'group_id1', 'indicator1', 'aggregation_function2')}

        actual = fd.get_id_mapping()

        assert actual == expected

    def test_filter_positive(self, indicators):
        fd = timeseries.FeatureDetails()
        fd.put('column1', indicators[0], 'aggregation_function1')
        fd.put('column2', indicators[0], 'aggregation_function2')
        fd.put('column3', indicators[1], 'aggregation_function2')
        expected = {
            'column1': {
                'indicator': indicators[0],
                'aggregation_function': 'aggregation_function1'
            }
        }

        actual = fd.filter(IndicatorSet([indicators[0]]), 'aggregation_function1')

        assert actual._details == expected

    def test_filter_empty(self, indicators):
        fd = timeseries.FeatureDetails()
        fd.put('column1', indicators[0], 'aggregation_function1')
        fd.put('column2', indicators[0], 'aggregation_function2')
        fd.put('column3', indicators[1], 'aggregation_function2')
        expected = {}

        actual = fd.filter(IndicatorSet([indicators[1]]), 'aggregation_function1')

        assert actual._details == expected
