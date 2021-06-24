from unittest.mock import patch

import pytest

from sailor.assetcentral.notification import Notification, create_notification, update_notification
from sailor.assetcentral import constants


@pytest.fixture
def mock_url():
    with patch('sailor.assetcentral.equipment._ac_application_url') as mock:
        mock.return_value = 'base_url'
        yield mock


@pytest.fixture
def mock_request(mock_config):
    with patch('sailor.utils.oauth_wrapper.OAuthServiceImpl.OAuth2Client.request') as mock:
        yield mock


@pytest.mark.parametrize('input_args,input_kwargs', [
    ([{'abc': 1, 'def': 2}], {}),
    ([], {'abc': 1, 'def': 2}),
    ([{'ghi': 3}], {'abc': 1, 'def': 2})
])
@pytest.mark.filterwarnings('ignore:Unknown name for .* parameter found')
def test_generic_create(mock_url, mock_request, input_args, input_kwargs):
    request_dict = dict(*input_args)
    request_dict.update(input_kwargs)
    expected_raw = {'notificationID': '123', **request_dict}
    mock_request.return_value = expected_raw

    with patch('sailor.assetcentral.utils._AssetcentralWriteRequest.validate'):
        actual = create_notification(*input_args, **input_kwargs)

    mock_request.calls[0] == ('POST', mock_url + constants.VIEW_NOTIFICATIONS, {'json': request_dict})
    mock_request.calls[1] == ('GET', mock_url + constants.VIEW_NOTIFICATIONS, {'params': {'notificationId': '123'}})
    assert type(actual) == Notification
    assert actual.raw == expected_raw


@pytest.mark.parametrize('input_args,input_kwargs', [
    ([{'abc': 1, 'def': 2}], {}),
    ([], {'abc': 1, 'def': 2}),
    ([{'ghi': 3}], {'abc': 1, 'def': 2})
])
@pytest.mark.parametrize('object_method', [
    (True),
    (False),
])
@pytest.mark.filterwarnings('ignore:Unknown name for .* parameter found')
def test_update_notification(mock_url, mock_request, input_args, input_kwargs, object_method, monkeypatch):
    # we need to overwrite this for a valid equality test in this context as update_notification returns a new object
    # while notification.update returns the same object
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
    notification = Notification(raw)
    request_dict = dict(*input_args)
    request_dict.update(input_kwargs)
    expected_put_response = {'notificationID': '123'}
    expected_get_response = {**raw, **request_dict}
    mock_request.side_effect = [expected_put_response, expected_get_response]

    if object_method:
        actual = notification.update(*input_args, **input_kwargs)
    else:
        actual = update_notification(notification, *input_args, **input_kwargs)

    mock_request.calls[0] == ('PUT', mock_url + constants.VIEW_NOTIFICATIONS, {'json': request_dict})
    mock_request.calls[1] == ('GET', mock_url + constants.VIEW_NOTIFICATIONS, {'params': {'notificationId': '123'}})
    assert type(actual) == Notification
    assert actual.raw == expected_get_response
    if object_method:
        assert actual == notification
    else:
        assert actual != notification