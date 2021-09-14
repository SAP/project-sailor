from unittest.mock import patch

import pytest

from sailor import _base
from sailor.assetcentral import constants
from sailor import assetcentral


test_params = {
    'equipment': {
        'function': assetcentral.find_equipment,
        'set_class': assetcentral.equipment.EquipmentSet,
        'id_field': 'equipmentId',
        'endpoint': constants.VIEW_EQUIPMENT
    },
    'failure_mode': {
        'function': assetcentral.find_failure_modes,
        'set_class': assetcentral.failure_mode.FailureModeSet,
        'id_field': 'ID',
        'endpoint': constants.VIEW_FAILUREMODES
    },
    'location': {
        'function': assetcentral.find_locations,
        'set_class': assetcentral.location.LocationSet,
        'id_field': 'locationId',
        'endpoint': constants.VIEW_LOCATIONS
    },
    'model': {
        'function': assetcentral.find_models,
        'set_class': assetcentral.model.ModelSet,
        'id_field': 'modelId',
        'endpoint': constants.VIEW_MODELS
    },
    'notification': {
        'function': assetcentral.find_notifications,
        'set_class': assetcentral.notification.NotificationSet,
        'id_field': 'notificationId',
        'endpoint': constants.VIEW_NOTIFICATIONS
    },
    'system': {
        'function': assetcentral.find_systems,
        'set_class': assetcentral.system.SystemSet,
        'id_field': 'systemId',
        'endpoint': constants.VIEW_SYSTEMS
    },
    'workorder': {
        'function': assetcentral.find_workorders,
        'set_class': assetcentral.workorder.WorkorderSet,
        'id_field': 'workOrderID',
        'endpoint': constants.VIEW_WORKORDERS
    },
}


@pytest.mark.filterwarnings('ignore:Following parameters are not in our terminology')
@pytest.mark.parametrize('test_object', list(test_params))
def test_find_functions_expect_fetch_call_args(test_object, monkeypatch):
    find_params = dict(extended_filters=['known_integer_param < 10'], unknown_string_param=['\'Type A\'', '\'Type F\''])
    expected_call_args = (['known_integer_param lt 10'], 
                         [["unknown_string_param eq 'Type A'", "unknown_string_param eq 'Type F'"]])

    params = test_params[test_object]
    instance_class = params['set_class']._element_type
    objects = [instance_class({params['id_field']: x}) for x in ['test_id1', 'test_id2']]
    expected_result = params['set_class'](objects)

    monkeypatch.setitem(instance_class._field_map,
                        'known_integer_param', _base.MasterDataField('known_integer_param', 'known_integer_param',
                                                                query_transformer=lambda x: str(x)))

    with patch(f'sailor.assetcentral.{test_object}._ac_application_url') as mock:
        mock.return_value = 'base_url'
        with patch(f'sailor.assetcentral.{test_object}._fetch_data') as mock_fetch:
            mock_fetch.return_value = [{params['id_field']: 'test_id1'}, {params['id_field']: 'test_id2'}]
            actual_result = params['function'](**find_params)

    assert params['endpoint'] in mock_fetch.call_args.args[0]
    assert mock_fetch.call_args.args[1:] == expected_call_args
    assert actual_result == expected_result
