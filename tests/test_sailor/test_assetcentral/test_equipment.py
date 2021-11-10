from unittest.mock import patch, Mock, call

import pytest

from sailor.assetcentral.equipment import Equipment
from sailor.assetcentral.location import Location, LocationSet
from sailor.assetcentral import constants


@pytest.fixture
def mock_url():
    with patch('sailor.assetcentral.equipment._ac_application_url') as mock:
        mock.return_value = 'base_url'
        yield mock


class TestEquipment:

    @pytest.fixture()
    def eq_obj(self, make_equipment):
        return make_equipment(equipmentId='D2602147691E463DA91EA2B4C3998C4B', name='testEquipment', location='USA')

    @patch('sailor._base.apply_filters_post_request')
    @patch('sailor.assetcentral.equipment._ac_fetch_data')
    def test_find_equipment_indicators_fetch_and_apply(self, mock_request, mock_apply, mock_url,
                                                       eq_obj, make_indicator_set):
        object_list = Mock(name='raw_object_list')
        mock_request.return_value = object_list
        mock_apply.return_value = [{'propertyId': 'indicator_1', 'pstid': 'group_id', 'categoryID': 'template_id'},
                                   {'propertyId': 'indicator_2', 'pstid': 'group_id', 'categoryID': 'template_id'}]
        filter_kwargs = {'param1': 'one'}
        extended_filters = ['other_param > 22']
        expected_result = make_indicator_set(propertyId=['indicator_1', 'indicator_2'])

        actual = eq_obj.find_equipment_indicators(**filter_kwargs, extended_filters=extended_filters)

        assert constants.VIEW_EQUIPMENT in mock_request.call_args.args[0]
        assert mock_apply.call_args.args[:-1] == (object_list, filter_kwargs, extended_filters)
        assert actual == expected_result

    @patch('sailor.assetcentral.equipment._ac_fetch_data')
    def test_find_failure_modes(self, mock_request, mock_config, eq_obj):
        mock_request.return_value = [{'ID': 'fm_id1'}, {'ID': 'fm_id2'}]
        expected = 'expected return value is the value returned by the delegate function "find_failure_modes"'

        with patch('sailor.assetcentral.equipment.find_failure_modes', return_value=expected) as mock_delegate:
            actual = eq_obj.find_failure_modes(extended_filters=['some_param > some_value'], param='123')

            mock_delegate.assert_called_once_with(extended_filters=['some_param > some_value'],
                                                  id=['fm_id1', 'fm_id2'], param='123')
            assert actual == expected

    @pytest.mark.parametrize('function_name', [
        'find_notifications', 'find_workorders'
    ])
    def test_delegate_called_with_filters(self, eq_obj, function_name):
        expected = f'expected return value is the value returned by the delegate function "{function_name}"'
        function_under_test = getattr(eq_obj, function_name)

        with patch(f'sailor.assetcentral.equipment.{function_name}', return_value=expected) as mock_delegate:
            actual = function_under_test(extended_filters=['some_param > some_value'], param='123')

            mock_delegate.assert_called_once_with(extended_filters=['some_param > some_value'], param='123',
                                                  equipment_id=eq_obj.id)
            assert actual == expected

    @patch('sailor.assetcentral.location._ac_fetch_data')
    def test_location_returns_location(self, mock_request, mock_config, make_equipment):
        equipment = make_equipment(equipment_id='123', location='Walldorf')
        mock_request.return_value = [{'locationId': '456', 'name': 'Walldorf'}]
        expected_result = Location({'locationId': '456', 'name': 'Walldorf'})

        actual = equipment.location

        assert type(actual) == Location
        assert actual == expected_result

    @patch('sailor.assetcentral.equipment.find_locations')
    def test_location_fetches_only_once(self, mock_find, make_equipment):
        mock_find.return_value = LocationSet([Location({'locationId': '456', 'name': 'Walldorf'})])
        equipment = make_equipment(equipment_id='123', location='Walldorf')

        equipment.location
        equipment.location

        mock_find.assert_called_once()

    @patch('sailor.assetcentral.equipment.find_locations')
    def test_location_different_instances_always_fetch(self, mock_find, make_equipment):
        mock_find.return_value = LocationSet([Location({'locationId': '456', 'name': 'Walldorf'})])
        equipment1 = make_equipment(equipment_id='123', location='Walldorf')
        equipment2 = make_equipment(equipment_id='123', location='Walldorf')
        expected_calls = [call(name='Walldorf'), call(name='Walldorf')]

        equipment1.location
        equipment2.location

        mock_find.assert_has_calls(expected_calls)

    @patch('sailor.assetcentral.equipment._create_or_update_notification')
    def test_create_notification_builds_request(self, create_update_mock, make_equipment):
        equipment = make_equipment(equipmentId='123', location='Walldorf')
        equipment._location = Location({'locationId': '456', 'name': 'Walldorf'})
        create_kwargs = {'notification_type': 'M2', 'short_description': 'test', 'priority': 15, 'status': 'NEW'}
        expected_request_dict = {
            'equipmentID': '123', 'locationID': '456', 'type': 'M2', 'description': {'shortDescription': 'test'},
            'priority': 15, 'status': ['NEW']}

        equipment.create_notification(**create_kwargs)

        create_update_mock.assert_called_once_with(expected_request_dict, 'POST')

    @pytest.mark.parametrize('create_kwargs', [
        ({'id': 123}),
        ({'notificationID': 123}),
        ({'equipment_id': 123}),
        ({'equipmentID': 123})
    ])
    def test_create_notification_forbidden_fields_raises(self, create_kwargs, make_equipment):
        equipment = make_equipment()
        equipment._location = Location({'locationId': '456', 'name': 'Walldorf'})
        expected_offender = list(create_kwargs.keys())[0]

        with pytest.raises(RuntimeError, match=f"You cannot set '{expected_offender}' in this request."):
            equipment.create_notification(**create_kwargs)

    @patch('sailor.pai.alert._create_alert')
    def test_create_alert_builds_request(self, create_mock, make_equipment):
        equipment = make_equipment(equipmentId='123')
        create_kwargs = dict(triggered_on='2020-07-31T13:23:00Z',
                             type='PUMP_TEMP_WARN', severity_code=5)
        expected_request_dict = {'equipmentId': '123', 'triggeredOn': '2020-07-31T13:23:00Z',
                                 'alertType': 'PUMP_TEMP_WARN', 'severityCode': 5}

        equipment.create_alert(**create_kwargs)

        create_mock.assert_called_once_with(expected_request_dict)

    @pytest.mark.parametrize('create_kwargs', [
        ({'id': 123}),
        ({'equipment_id': 123}),
        ({'equipmentId': 123})
    ])
    def test_create_alert_forbidden_fields_raises(self, create_kwargs, make_equipment):
        equipment = make_equipment()
        expected_offender = list(create_kwargs.keys())[0]

        with pytest.raises(RuntimeError, match=f"You cannot set '{expected_offender}' in this request."):
            equipment.create_alert(**create_kwargs)



class TestEquipmentSet:

    @pytest.mark.parametrize('function_name', [
        'find_notifications', 'find_workorders',
    ])
    def test_delegate_called_with_filters(self, make_equipment_set, function_name):
        eq_set = make_equipment_set(equipmentId=['equipment_id_1', 'equipment_id_2'])
        expected = f'expected return value is the value returned by the delegate function "{function_name}"'
        function_under_test = getattr(eq_set, function_name)

        with patch(f'sailor.assetcentral.equipment.{function_name}', return_value=expected) as mock_delegate:
            actual = function_under_test(extended_filters=['some_param > some_value'], param='123')

            mock_delegate.assert_called_once_with(extended_filters=['some_param > some_value'], param='123',
                                                  equipment_id=[equipment.id for equipment in eq_set])
            assert actual == expected

    def test_find_common_indicators(self, make_indicator, make_indicator_set, make_equipment_set):
        equipment_set = make_equipment_set(equipmentId=['equipment_id_1', 'equipment_id_2', 'equipment_id_3'])
        indicator_ids = [['1', '2', '3'], ['1', '3'], ['3', '1']]

        for i, equipment in enumerate(equipment_set):
            equipment.find_equipment_indicators = Mock()
            equipment.find_equipment_indicators.return_value = make_indicator_set(propertyId=indicator_ids[i])

        expected_result = make_indicator_set(propertyId=['3', '1'])

        actual_result = equipment_set.find_common_indicators()

        assert expected_result == actual_result

    def test_expected_public_attributes_are_present(self):
        expected_attributes = [
            'name', 'model_name', 'location_name', 'status_text', 'short_description', 'manufacturer',
            'operator', 'installation_date', 'build_date', 'criticality_description', 'id', 'model_id',
            'template_id', 'serial_number', 'batch_number',
        ]

        fieldmap_public_attributes = [
            field.our_name for field in Equipment._field_map.values() if field.is_exposed
        ]

        assert expected_attributes == fieldmap_public_attributes
