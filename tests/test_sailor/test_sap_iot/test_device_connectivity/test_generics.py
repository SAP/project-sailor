from unittest.mock import patch

import pytest

from sailor.sap_iot import device_connectivity
from sailor.sap_iot.device_connectivity import constants

test_params = {
    'device': {
        'function': device_connectivity.find_devices,
        'set_class': device_connectivity.device.DeviceSet,
        'id_field': 'id',
        'endpoint': constants.VIEW_DEVICES
    },
    'sensor_type': {
        'function': device_connectivity.find_sensor_types,
        'set_class': device_connectivity.sensor_type.SensorTypeSet,
        'id_field': 'id',
        'endpoint': constants.VIEW_SENSOR_TYPES
    },
    'capability': {
        'function': device_connectivity.find_capabilities,
        'set_class': device_connectivity.capability.CapabilitySet,
        'id_field': 'id',
        'endpoint': constants.VIEW_CAPABILITIES
    },
}


@pytest.mark.filterwarnings('ignore:Following parameters are not in our terminology')
@pytest.mark.parametrize('test_object', list(test_params))
def test_find_functions_expect_fetch_call_args(test_object):
    find_params = dict(extended_filters=['unknown_integer_param < 10'], unknown_string_param=["'Type A'", "'Type F'"])
    expected_call_args = (['unknown_integer_param lt 10'],
                          [["unknown_string_param eq 'Type A'", "unknown_string_param eq 'Type F'"]])

    params = test_params[test_object]
    instance_class = params['set_class']._element_type
    objects = [instance_class({params['id_field']: x}) for x in ['test_id1', 'test_id2']]
    expected_result = params['set_class'](objects)

    with patch(f'sailor.sap_iot.device_connectivity.{test_object}._device_connectivity_api_url') as mock:
        mock.return_value = 'base_url'
        with patch(f'sailor.sap_iot.device_connectivity.{test_object}._dc_fetch_data') as mock_fetch:
            mock_fetch.return_value = [{params['id_field']: 'test_id1'}, {params['id_field']: 'test_id2'}]
            actual_result = params['function'](**find_params)

    assert params['endpoint'] in mock_fetch.call_args.args[0]
    assert mock_fetch.call_args.args[1:] == expected_call_args
    assert actual_result == expected_result
