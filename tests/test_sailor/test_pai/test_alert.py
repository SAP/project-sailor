from unittest.mock import patch

import pytest

from sailor.pai import constants
from sailor import pai
from sailor.pai.alert import Alert


def get_parameters(test_object):
    test_params = {
        'alert': {
            'function': pai.find_alerts,
            'set_class': pai.alert.AlertSet,
            'id_field': 'AlertId',
            'endpoint': constants.ALERTS_READ_PATH
        },
    }
    return test_params[test_object]


class TestAlert():

    @pytest.mark.filterwarnings('ignore:Following parameters are not in our terminology')
    def test_find_alerts_expect_fetch_call_args(self):
        params = get_parameters('alert')

        find_params = dict(extended_filters=['integer_param1 < 10'], string_parameter=['Type A', 'Type F'])
        expected_call_args = (['integer_param1 lt 10'],
                              [["string_parameter eq 'Type A'", "string_parameter eq 'Type F'"]],
                              'predictive_asset_insights')

        alert_object = {'d': {'results': [{'AlertId': 'test_id1'}, {'AlertId': 'test_id2'}]}}
        instance_class = params['set_class']._element_type

        objects = [instance_class({params['id_field']: x}) for x in ['test_id1', 'test_id2']]
        expected_result = params['set_class'](objects)

        with patch('sailor.pai.alert._pai_application_url') as mock:
            mock.return_value = 'base_url'
            with patch('sailor.pai.alert._fetch_data') as mock_fetch:
                mock_fetch.return_value = [alert_object]
                actual_result = params['function'](**find_params)

        assert params['endpoint'] in mock_fetch.call_args.args[0]
        assert mock_fetch.call_args.args[1:] == expected_call_args
        assert actual_result == expected_result

    def test_expected_public_attributes_are_present(self):
        expected_attributes = [
            'description', 'severity_code', 'category', 'equipment_name', 'model_name', 'indicator_name',
            'indicator_group_name', 'template_name', 'count', 'status_code', 'triggered_on', 'last_occured_on',
            'type_description', 'error_code_description', 'type', 'id', 'equipment_id', 'model_id', 'template_id',
            'indicator_id', 'indicator_group_id', 'notification_id',
        ]

        fieldmap_public_attributes = [
            field.our_name for field in Alert._field_map.values() if field.is_exposed
        ]

        assert expected_attributes == fieldmap_public_attributes
