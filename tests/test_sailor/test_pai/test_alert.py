from unittest.mock import patch, call

import pytest
from pandas import Timestamp
from plotnine import ggplot

from sailor.pai import constants
from sailor import pai
from sailor.pai.utils import _PredictiveAssetInsightsField
from sailor.pai.alert import Alert, AlertSet, _AlertWriteRequest, create_alert
from sailor._base.fetch import fetch_data
import sailor._base


@pytest.fixture
def make_alert():
    def maker(**kwargs):
        kwargs.setdefault('AlertId', 'id')
        kwargs.setdefault('AlertType', 'alert_type')
        return Alert(kwargs)
    return maker


@pytest.fixture
def make_alert_set(make_alert):
    def maker(**kwargs):
        alert_defs = [dict() for _ in list(kwargs.values())[0]]
        for k, values in kwargs.items():
            for i, value in enumerate(values):
                alert_defs[i][k] = value
        return AlertSet([make_alert(**x) for x in alert_defs])
    return maker


@pytest.fixture
def mock_ac_url():
    with patch('sailor.assetcentral.utils._ac_application_url') as mock:
        mock.return_value = 'ac_base_url'
        yield mock


@pytest.fixture
def mock_pai_url():
    with patch('sailor.pai.alert._pai_application_url') as mock:
        mock.return_value = 'pai_base_url'
        yield mock


@pytest.fixture
def mock_fetch_data_paginate_false(monkeypatch):
    def fetch_data_paginate_false(*args, **kwargs):
        kwargs.update({'paginate': False})
        return fetch_data(*args, **kwargs)
    monkeypatch.setattr(sailor._base, 'fetch_data', fetch_data_paginate_false)
    yield


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

        find_params = dict(extended_filters=['unknown_integer_param < 10'],
                           unknown_string_param=["'Type A'", "'Type F'"])
        expected_call_args = (['unknown_integer_param lt 10'],
                              [["unknown_string_param eq 'Type A'", "unknown_string_param eq 'Type F'"]])

        fetch_result = [{'AlertId': 'test_id1'}, {'AlertId': 'test_id2'}]
        instance_class = params['set_class']._element_type

        objects = [instance_class({params['id_field']: x}) for x in ['test_id1', 'test_id2']]
        expected_result = params['set_class'](objects)

        with patch('sailor.pai.alert._pai_application_url') as mock:
            mock.return_value = 'base_url'
            with patch('sailor.pai.alert._pai_fetch_data') as mock_fetch:
                mock_fetch.return_value = fetch_result
                actual_result = params['function'](**find_params)

        assert params['endpoint'] in mock_fetch.call_args.args[0]
        assert mock_fetch.call_args.args[1:] == expected_call_args
        assert actual_result == expected_result

    def test_expected_public_attributes_are_present(self):
        expected_attributes = [
            'triggered_on', 'last_occured_on', 'count', 'type', 'category', 'severity_code', 'equipment_name',
            'model_name', 'indicator_name', 'indicator_group_name', 'template_name', 'status_code',  'type_description',
            'error_code_description',  'source', 'description', 'id', 'equipment_id', 'model_id', 'template_id',
            'indicator_id', 'indicator_group_id', 'notification_id', 'error_code_id',
        ]

        fieldmap_public_attributes = [
            field.our_name for field in Alert._field_map.values() if field.is_exposed
        ]

        assert expected_attributes == fieldmap_public_attributes

    def test_custom_properties_uses_startswith_z(self):
        alert = Alert({'AlertId': 'id',
                       'Z_mycustom': 'mycustom', 'z_another': 'another'})
        assert alert._custom_properties == {'Z_mycustom': 'mycustom', 'z_another': 'another'}

    def test_custom_properties_are_set_as_attributes(self):
        alert = Alert({'AlertId': 'id',
                       'Z_mycustom': 'mycustom', 'z_another': 'another'})
        assert alert.id == 'id'
        assert alert.Z_mycustom == 'mycustom'
        assert alert.z_another == 'another'


class TestAlertSet:
    @pytest.mark.parametrize('testdesc,kwargs,expected_cols', [
        ('default=all noncustom properties',
            dict(), ['id', 'type']),
        ('only specified columns',
            dict(columns=['id', 'Z_mycustom']), ['id', 'Z_mycustom']),
        ('all properties AND all custom properties',
            dict(include_all_custom_properties=True), ['id', 'type', 'Z_mycustom', 'z_another']),
        ('specified AND all custom properties',
            dict(columns=['id', 'Z_mycustom'], include_all_custom_properties=True), ['id', 'Z_mycustom', 'z_another'])
    ])
    def test_as_df_expects_columns(self, make_alert_set, monkeypatch,
                                   kwargs, expected_cols, testdesc):
        monkeypatch.setattr(Alert, '_field_map', {
            'id': _PredictiveAssetInsightsField('id', 'AlertId'),
            'type': _PredictiveAssetInsightsField('type', 'AlertType'),
        })
        alert_set = make_alert_set(AlertId=['id1', 'id2', 'id3'],
                                   Z_mycustom=['cust1', 'cust2', 'cust3'],
                                   z_another=['ano1', 'ano2', 'ano3'])
        actual = alert_set.as_df(**kwargs)
        assert actual.columns.to_list() == expected_cols

    def test_as_df_raises_on_custom_properties_with_multiple_types(self, make_alert_set, monkeypatch):
        monkeypatch.setattr(Alert, '_field_map', {
            'id': _PredictiveAssetInsightsField('id', 'AlertId'),
            'type': _PredictiveAssetInsightsField('type', 'AlertType'),
        })
        alert_set = make_alert_set(AlertId=['id1', 'id2', 'id3'],
                                   AlertType=['type', 'type', 'DIFFERENT_TYPE'],
                                   Z_mycustom=['cust1', 'cust2', 'cust3'],
                                   z_another=['ano1', 'ano2', 'ano3'])
        with pytest.raises(RuntimeError, match='More than one alert type present in result'):
            alert_set.as_df(include_all_custom_properties=True)

    def test_plot_overview_returns_plot(self, make_alert_set):
        alert_set = make_alert_set(AlertId=['id1'],
                                   LastOccuredOn=['1234567890'],
                                   Count=['1'])
        plot = alert_set.plot_overview()
        assert type(plot) == ggplot


@pytest.mark.filterwarnings('ignore:Unknown name for _AlertWriteRequest parameter found')
def test_create_alert_create_calls_and_result(mock_ac_url, mock_pai_url, mock_request, mock_fetch_data_paginate_false):
    input_kwargs = {'param1': 'abc123', 'param2': 'def456'}
    mock_post_response = b'12345678-1234-1234-1234-1234567890ab'
    mock_get_response = {'d': {'results': [{'some': 'result'}]}}
    mock_request.side_effect = [mock_post_response, mock_get_response]
    expected_request_dict = input_kwargs

    # mock validate so that validation does not fail
    with patch('sailor.assetcentral.utils._AssetcentralWriteRequest.validate'):
        actual = create_alert(**input_kwargs)

    mock_request.assert_has_calls([
        call('POST', 'ac_base_url' + constants.ALERTS_WRITE_PATH, json=expected_request_dict),
        call('GET', 'pai_base_url' + constants.ALERTS_READ_PATH,
             params={'$filter': "AlertId eq '12345678-1234-1234-1234-1234567890ab'", '$format': 'json'})])
    assert type(actual) == Alert
    assert actual.raw == {'some': 'result'}


@pytest.mark.parametrize('find_call_result', [
    ({'d': {'results': []}}),
    ({'d': {'results': [{'AlertId': '123'}, {'AlertId': '456'}]}}),
])
@pytest.mark.filterwarnings('ignore::sailor.utils.utils.DataNotFoundWarning')
@patch('sailor.pai.alert._AlertWriteRequest')
def test_create_alert_raises_when_find_has_no_single_result(mock_wr, mock_pai_url, mock_ac_url, mock_request,
                                                            find_call_result, mock_fetch_data_paginate_false):
    successful_create_result = b'12345678-1234-1234-1234-1234567890ab'
    mock_request.side_effect = [successful_create_result, find_call_result]

    with pytest.raises(RuntimeError, match='Unexpected error'):
        create_alert()


def test_create_alert_integration(mock_pai_url, mock_ac_url, mock_request, mock_fetch_data_paginate_false):
    create_kwargs = {
        'triggered_on': '2020-07-31T13:23:02Z',
        'description': 'Test alert',
        'type': 'Centrifuge_Overheating',
        'severity_code': 5,
        'equipment_id': 'EQUI_ID_001',
        'template_id': 'TEMPLATE_ID_002',
        'indicator_group_id': 'IGROUP_ID_003',
        'indicator_id': 'INDICATOR_ID_004',
        'source': 'Machine'}
    expected_request_dict = {
        'triggeredOn': '2020-07-31T13:23:02Z',
        'description': 'Test alert',
        'alertType': 'Centrifuge_Overheating',
        'severityCode': 5,
        'equipmentId': 'EQUI_ID_001',
        'templateId': 'TEMPLATE_ID_002',
        'indicatorGroupId': 'IGROUP_ID_003',
        'indicatorId': 'INDICATOR_ID_004',
        'source': 'Machine'}
    mock_post_response = b'12345678-1234-1234-1234-1234567890ab'
    mock_get_response = {'d': {'results': [{
        '__metadata': {},
        'EquipmentID': 'EQUI_ID_001',
        'TriggeredOn': '/Date(1596201782000)/',
        'SeverityCode': 5,
        'TemplateID': 'TEMPLATE_ID_002',
        'Description': 'Test alert',
        'IndicatorID': 'INDICATOR_ID_004',
        'Source': 'Machine',
        'AlertType': 'Centrifuge_Overheating',
        'IndicatorGroupID': 'IGROUP_ID_003',
        'AlertId': '12345678-1234-1234-1234-1234567890ab'}
        ]}}
    mock_request.side_effect = [mock_post_response, mock_get_response]

    actual = create_alert(**create_kwargs)

    mock_request.assert_has_calls([
        call('POST', 'ac_base_url/ain/services/api/v1/alerts', json=expected_request_dict),
        call('GET', 'pai_base_url/alerts/odata/v1/Alerts', params={
            '$filter': "AlertId eq '12345678-1234-1234-1234-1234567890ab'", '$format': 'json'})])
    assert type(actual) == Alert
    assert actual.id == '12345678-1234-1234-1234-1234567890ab'
    assert actual.triggered_on == Timestamp('2020-07-31T13:23:02Z')
    create_kwargs.pop('triggered_on')
    for property_name, value in create_kwargs.items():
        assert getattr(actual, property_name) == value


def test_alertwriterequest_custom_properties():
    create_kwargs = {
        'triggered_on': '2020-07-31T13:23:02Z',
        'type': 'Centrifuge_Overheating',
        'severity_code': 5,
        'equipment_id': 'EQUI_ID_001',
        'Z_mycustom': 'some custom value',
        'z_another': 'another custom value'}
    expected_request_dict = {
        'triggeredOn': '2020-07-31T13:23:02Z',
        'alertType': 'Centrifuge_Overheating',
        'severityCode': 5,
        'equipmentId': 'EQUI_ID_001',
        'custom_properties': {'Z_mycustom': 'some custom value',
                              'z_another': 'another custom value'}
    }

    request = _AlertWriteRequest()
    request.insert_user_input(create_kwargs)

    assert request == expected_request_dict
