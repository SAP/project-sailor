from unittest.mock import patch, Mock, call

import pytest

from sailor.assetcentral.location import Location, LocationSet
from sailor.assetcentral.equipment import Equipment, EquipmentSet, find_equipments
from sailor.assetcentral.indicators import Indicator, IndicatorSet
from sailor.assetcentral import constants


@pytest.fixture(scope='module', autouse=True)
def mock_config():
    with patch('sailor.utils.config.SailorConfig') as mock:
        yield mock


@pytest.fixture
def mock_url():
    with patch('sailor.assetcentral.equipment.ac_application_url') as mock:
        mock.return_value = 'base_url'
        yield mock


class TestEquipment:

    @pytest.fixture()
    def eq_obj(self):
        return Equipment(
            {'equipmentId': 'D2602147691E463DA91EA2B4C3998C4B', 'name': 'testEquipment', 'location': 'USA'})

    @patch('sailor.assetcentral.equipment.apply_filters_post_request')
    @patch('sailor.assetcentral.equipment.fetch_data')
    def test_find_equipment_indicators_fetch_and_apply(self, mock_fetch, mock_apply, mock_url, eq_obj):
        object_list = Mock(name='raw_object_list')
        mock_fetch.return_value = object_list
        mock_apply.return_value = [{'propertyId': 'indicator_1'}, {'propertyId': 'indicator_2'}]
        filter_kwargs = {'param1': 'one'}
        extended_filters = ['other_param > 22']
        expected_result = IndicatorSet([Indicator({'propertyId': 'indicator_1'}),
                                        Indicator({'propertyId': 'indicator_2'})])

        actual = eq_obj.find_equipment_indicators(**filter_kwargs, extended_filters=extended_filters)

        assert constants.VIEW_EQUIPMENT in mock_fetch.call_args.args[0]
        assert mock_apply.call_args.args[:-1] == (object_list, filter_kwargs, extended_filters)
        assert actual == expected_result

    @patch('sailor.assetcentral.equipment.fetch_data')
    def test_find_failure_modes(self, mock_fetch, eq_obj):
        mock_fetch.return_value = [{'ID': 'fm_id1'}, {'ID': 'fm_id2'}]
        expected = 'expected return value is the value returned by the delegate function "find_failure_modes"'

        with patch('sailor.assetcentral.equipment.find_failure_modes', return_value=expected) as mock_delegate:
            actual = eq_obj.find_failure_modes(extended_filters=['some_param > some_value'], param='123')

            mock_delegate.assert_called_once_with(['some_param > some_value'], id=['fm_id1', 'fm_id2'], param='123')
            assert actual == expected

    @pytest.mark.parametrize('function_name', [
        'find_notifications', 'find_workorders'
    ])
    def test_delegate_called_with_filters(self, eq_obj, function_name):
        expected = f'expected return value is the value returned by the delegate function "{function_name}"'
        function_under_test = getattr(eq_obj, function_name)

        with patch(f'sailor.assetcentral.equipment.{function_name}', return_value=expected) as mock_delegate:
            actual = function_under_test(extended_filters=['some_param > some_value'], param='123')

            mock_delegate.assert_called_once_with(['some_param > some_value'], param='123', equipment_id=eq_obj.id)
            assert actual == expected

    @patch('sailor.assetcentral.location.fetch_data')
    def test_location_returns_location(self, mock_fetch):
        equipment = Equipment({'equipmentId': '123', 'location': 'Walldorf'})
        mock_fetch.return_value = [{'locationId': '456', 'name': 'Walldorf'}]
        expected_result = Location({'locationId': '456', 'name': 'Walldorf'})

        actual = equipment.location

        assert type(actual) == Location
        assert actual == expected_result

    @patch('sailor.assetcentral.equipment.find_locations')
    def test_location_fetches_only_once(self, mock_find):
        mock_find.return_value = LocationSet([Location({'locationId': '456', 'name': 'Walldorf'})])
        equipment = Equipment({'equipmentId': '123', 'location': 'Walldorf'})

        equipment.location
        equipment.location

        mock_find.assert_called_once()

    @patch('sailor.assetcentral.equipment.find_locations')
    def test_location_different_instances_always_fetch(self, mock_find):
        mock_find.return_value = LocationSet([Location({'locationId': '456', 'name': 'Walldorf'})])
        equipment = Equipment({'equipmentId': '123', 'location': 'Walldorf'})
        equipment2 = Equipment({'equipmentId': '123', 'location': 'Walldorf'})
        expected_calls = [call(name='Walldorf'), call(name='Walldorf')]

        equipment.location
        equipment2.location

        mock_find.assert_has_calls(expected_calls)


class TestEquipmentSet:

    @pytest.fixture()
    def eq_set(self):
        return EquipmentSet([Mock(Equipment), Mock(Equipment)])

    @pytest.mark.parametrize('function_name', [
        'find_notifications', 'find_workorders',
    ])
    def test_delegate_called_with_filters(self, eq_set, function_name):
        expected = f'expected return value is the value returned by the delegate function "{function_name}"'
        function_under_test = getattr(eq_set, function_name)

        with patch(f'sailor.assetcentral.equipment.{function_name}', return_value=expected) as mock_delegate:
            actual = function_under_test(extended_filters=['some_param > some_value'], param='123')

            mock_delegate.assert_called_once_with(['some_param > some_value'], param='123',
                                                  equipment_id=[equipment.id for equipment in eq_set])
            assert actual == expected

    def test_find_common_indicators(self):
        eq1 = Mock(Equipment)
        eq1.find_equipment_indicators.return_value = IndicatorSet([
            Indicator({'propertyId': '3'}), Indicator({'propertyId': '2'}), Indicator({'propertyId': '1'})])
        eq2 = Mock(Equipment)
        eq2.find_equipment_indicators.return_value = IndicatorSet([
            Indicator({'propertyId': '1'}), Indicator({'propertyId': '3'})])
        eq3 = Mock(Equipment)
        eq3.find_equipment_indicators.return_value = IndicatorSet([
            Indicator({'propertyId': '3'}), Indicator({'propertyId': '1'})])
        equipment_set = EquipmentSet([eq1, eq2, eq3])
        expected_result = IndicatorSet([Indicator({'propertyId': '3'}), Indicator({'propertyId': '1'})])

        actual_result = equipment_set.find_common_indicators()

        assert expected_result == actual_result


@pytest.mark.parametrize('testdescription,find_params,expected_call_args', [
    ('without filters', {}, ([], [])),
    ('with filters',
     dict(extended_filters=['integer_param1 < 10'], location_name=['Paris', 'London']),
     (['integer_param1 lt 10'], [["location eq 'Paris'", "location eq 'London'"]])),
])
@pytest.mark.filterwarnings('ignore:Following parameters are not in our terminology')
@patch('sailor.assetcentral.equipment.fetch_data')
def test_find_equipments_expect_fetch_call_args(mock_fetch, find_params, expected_call_args, testdescription, mock_url):
    mock_fetch.return_value = [{'equipmentId': 'eq_id1'}, {'equipmentId': 'eq_id2'}]
    expected_result = EquipmentSet([Equipment({'equipmentId': 'eq_id1'}), Equipment({'equipmentId': 'eq_id2'})])

    actual_result = find_equipments(**find_params)

    assert constants.VIEW_EQUIPMENT in mock_fetch.call_args.args[0]
    assert mock_fetch.call_args.args[1:] == expected_call_args
    assert actual_result == expected_result
