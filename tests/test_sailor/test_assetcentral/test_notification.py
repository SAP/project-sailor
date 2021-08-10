from unittest.mock import patch, MagicMock, call

import pytest

from sailor.assetcentral.notification import (
    Notification, create_notification, update_notification, _create_or_update_notification)
from sailor.assetcentral.constants import VIEW_NOTIFICATIONS


@pytest.fixture
def mock_url():
    with patch('sailor.assetcentral.notification._ac_application_url') as mock:
        mock.return_value = 'base_url'
        yield mock


@pytest.fixture
def mock_request(mock_config):
    with patch('sailor.utils.oauth_wrapper.OAuthServiceImpl.OAuth2Client.request') as mock:
        yield mock


# TODO: this test is a blueprint for testing create functions generically
@pytest.mark.parametrize('input_kwargs,create_function,api_path,put_id_name,get_id_name', [
    ({'abc': 1, 'def': 2}, create_notification, VIEW_NOTIFICATIONS, 'notificationID', 'notificationId'),
])
@pytest.mark.filterwarnings('ignore:Unknown name for _AssetcentralWriteRequest parameter found')
def test_generic_create_calls_and_result(mock_url, mock_request,
                                         input_kwargs, api_path, create_function, put_id_name, get_id_name):
    mock_post_response = {put_id_name: '123'}
    mock_get_response = {'some': 'result'}
    mock_request.side_effect = [mock_post_response, mock_get_response]
    expected_request_dict = input_kwargs

    # mock validate so that validation does not fail
    with patch('sailor.assetcentral.utils._AssetcentralWriteRequest.validate'):
        actual = create_function(**input_kwargs)

    mock_request.assert_has_calls([
        call('POST', 'base_url' + api_path, json=expected_request_dict),
        call('GET', 'base_url' + api_path, params={'$filter': f"{get_id_name} eq '123'",
                                                   '$format': 'json'})])
    assert type(actual) == Notification
    assert actual.raw == mock_get_response


# TODO: this test might be able to be turned into a generic test for all _create_or_update functions
@pytest.mark.parametrize('find_call_result', [
    ([]),
    ([{'notificationId': '123'}, {'notificationId': '456'}]),
])
@pytest.mark.filterwarnings('ignore::sailor.utils.utils.DataNotFoundWarning')
def test_generic_create_update_raises_when_find_has_no_single_result(mock_url, mock_request, find_call_result):
    successful_create_result = {'notificationID': '123'}
    mock_request.side_effect = [successful_create_result, find_call_result]

    with pytest.raises(RuntimeError, match='Unexpected error'):
        _create_or_update_notification(MagicMock(), '')


def test_create_notification_integration(mock_url, mock_request):
    create_kwargs = {'equipment_id': 'XYZ', 'notification_type': 'M2',
                     'short_description': 'test', 'priority': 15, 'status': 'NEW'}
    mock_post_response = {'notificationID': '123'}
    mock_get_response = {'equipmentId': 'XYZ', 'notificationId': '123', 'notificationType': 'M2',
                         'shortDescription': 'test', 'priority': 15, 'status': 'NEW'}
    mock_request.side_effect = [mock_post_response, mock_get_response]
    expected_request_dict = {
        'equipmentID': 'XYZ', 'type': 'M2', 'description': {'shortDescription': 'test'},
        'priority': 15, 'status': ['NEW']}

    actual = create_notification(**create_kwargs)

    mock_request.assert_has_calls([
        call('POST', 'base_url/services/api/v1/notification', json=expected_request_dict),
        call('GET', 'base_url/services/api/v1/notification', params={'$filter': "notificationId eq '123'",
                                                                     '$format': 'json'})])
    assert type(actual) == Notification
    for property_name, value in create_kwargs.items():
        assert getattr(actual, property_name) == value


@pytest.mark.parametrize('is_object_method', [
    (True),
    (False),
])
def test_update_notification_integration(mock_url, mock_request, is_object_method, monkeypatch):
    # we need to overwrite __eq__ for a valid equality test in this context as update_notification returns a new object
    # whereas notification.update returns the same object
    monkeypatch.setattr(Notification, '__eq__', object.__eq__)

    raw = {  # at least the keys in the mapping must exist. that's why we have a full raw dict here
        'notificationId': '123', 'shortDescription': 'test', 'status': 'IPR', 'statusDescription': 'In Process',
        'notificationType': 'M1', 'notificationTypeDescription': 'Maintenance Request', 'priority': 10,
        'priorityDescription': 'Medium', 'isInternal': '1', 'createdBy': 'First Name Last Name',
        'creationDateTime': '2021-05-27', 'lastChangedBy': 'First Name Last Name', 'lastChangeDateTime': '2021-05-27',
        'longDescription': 'test', 'startDate': '2021-05-27', 'endDate': '2021-05-28',
        'malfunctionStartDate': '2021-05-25', 'malfunctionEndDate': None, 'progressStatus': '15',
        'progressStatusDescription': 'Pending', 'equipmentId': 'eq123',
        'equipmentName': 'test', 'rootEquipmentId': 'eq123', 'rootEquipmentName': 'test',
        'locationId': None, 'breakdown': '0', 'coordinates': None, 'source': 'Test', 'operatorId': None,
        'location': None, 'assetCoreEquipmentId': 'eq123', 'operator': 'Test',
        'internalId': 'NO.TEST.680736', 'modelId': None, 'proposedFailureModeID': 'fm123',
        'proposedFailureModeDisplayID': 'FM.TEST.115', 'proposedFailureModeDesc': 'EDIT_FM_20210506165409',
        'confirmedFailureModeID': None, 'confirmedFailureModeDesc': None, 'confirmedFailureModeDisplayID': None,
        'systemProposedFailureModeID': None, 'systemProposedFailureModeDesc': None,
        'systemProposedFailureModeDisplayID': None, 'effectID': None, 'effectDisplayID': None, 'effectDesc': None,
        'causeID': None, 'causeDisplayID': None, 'causeDesc': None, 'instructionID': 'ins123',
        'instructionTitle': 'Tit-gIavIcZmXT', 'functionalLocationID': None}

    input_kwargs = {'short_description': 'NEW test', 'priority': 25, 'status': 'PBD'}

    expected_request_dict = {'notificationID': '123', 'type': 'M1',
                             'description': {'shortDescription': 'NEW test', 'longDescription': 'test'},
                             'priority': 25, 'status': ['PBD'], 'equipmentID': 'eq123', 'breakdown': '0',
                             'causeID': None, 'effectID': None, 'instructionID': 'ins123', 'operator': None,
                             'confirmedFailureModeID': None, 'endDate': '2021-05-28', 'functionalLocationID': None,
                             'locationID': None, 'malfunctionEndDate': None, 'malfunctionStartDate': '2021-05-25',
                             'startDate': '2021-05-27', 'systemProposedFailureModeID': None,
                             'proposedFailureModeID': 'fm123'}

    notification = Notification(raw)
    mock_put_response = {'notificationID': '123'}
    mock_get_response = {**raw, 'shortDescription': 'NEW test', 'priority': 25, 'status': 'PBD'}
    mock_request.side_effect = [mock_put_response, mock_get_response]

    if is_object_method:
        actual = notification.update(**input_kwargs)
    else:
        actual = update_notification(notification, **input_kwargs)

    mock_request.assert_has_calls([
        call('PUT', 'base_url/services/api/v1/notification', json=expected_request_dict),
        call('GET', 'base_url/services/api/v1/notification', params={'$filter': "notificationId eq '123'",
                                                                     '$format': 'json'})])

    assert type(actual) == Notification
    for property_name, value in input_kwargs.items():
        assert getattr(actual, property_name) == value
    if is_object_method:
        assert actual == notification
    else:
        assert actual != notification


def test_expected_public_attributes_are_present():
    expected_attributes = [
        'name', 'equipment_name', 'priority_description', 'status_text', 'short_description',
        'malfunction_start_date', 'malfunction_end_date', 'breakdown', 'confirmed_failure_mode_description',
        'cause_description', 'effect_description', 'notification_type', 'status', 'long_description',
        'id', 'priority', 'equipment_id', 'cause_id', 'cause_display_id', 'effect_id', 'effect_display_id',
        'instruction_id', 'instruction_title', 'operator_id', 'confirmed_failure_mode_id',
        'confirmed_failure_mode_name', 'end_date', 'functional_location_id', 'location_id', 'location_name',
        'model_id', 'notification_type_description', 'root_equipment_id', 'root_equipment_name', 'start_date',
        'system_failure_mode_id', 'system_failure_mode_description', 'system_failure_mode_name',
        'user_failure_mode_id', 'user_failure_mode_description', 'user_failure_mode_name',
    ]

    fieldmap_public_attributes = [
        field.our_name for field in Notification._field_map.values() if field.is_exposed
    ]

    assert expected_attributes == fieldmap_public_attributes
