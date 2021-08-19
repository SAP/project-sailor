from unittest.mock import patch

import pytest

from sailor.sap_iot.write import upload_indicator_data
from ..data_generators import make_dataset


@pytest.fixture(autouse=True)
def mock_upload_url():
    with patch('sailor.sap_iot.write.request_upload_url') as mock:
        yield mock


def test_upload_is_split_by_indicator_group_and_template(mock_oauth, make_indicator_set, make_equipment_set):
    indicator_set = make_indicator_set(
        propertyId=['indicator_id_A', 'indicator_id_B', 'indicator_id_A'],
        pstid=['indicator_group_A', 'indicator_group_A', 'indicator_group_B'],
        categoryID=['first_template', 'second_template', 'first_template']
    )
    equipment_set = make_equipment_set(
        equipmentId=['equipment_A']
    )
    dataset = make_dataset(indicator_set, equipment_set)

    upload_indicator_data(dataset)

    assert mock_oauth.call_count == 3
    assert all(args[0][0] == 'POST' for args in mock_oauth.call_args_list)
    assert all(args[0][1].endswith('equipment_A') for args in mock_oauth.call_args_list)

    payloads = [args[-1]['json'] for args in mock_oauth.call_args_list]
    for indicator in indicator_set:
        # find matching payload
        matching_payload_candidates = [
            payload for payload in payloads if
            payload['Tags']['indicatorGroupId'] == indicator._liot_group_id and
            payload['Tags']['templateId'] == indicator.template_id
        ]
        assert len(matching_payload_candidates) == 1
        matching_payload = matching_payload_candidates[0]
        assert all(value.keys() == {'_time', indicator._liot_id} for value in matching_payload['Values'])


def test_upload_one_group_in_one_request(mock_oauth, make_indicator_set, make_equipment_set):
    indicator_set = make_indicator_set(
        propertyId=['indicator_id_A', 'indicator_id_B', 'indicator_id_A'],
        pstid=['indicator_group_A', 'indicator_group_A', 'indicator_group_B'],
    )
    equipment_set = make_equipment_set(
        equipmentId=['equipment_A']
    )
    dataset = make_dataset(indicator_set, equipment_set)

    upload_indicator_data(dataset)

    assert mock_oauth.call_count == 2
    assert all(args[0][0] == 'POST' for args in mock_oauth.call_args_list)
    assert all(args[0][1].endswith('equipment_A') for args in mock_oauth.call_args_list)

    payloads = [args[-1]['json'] for args in mock_oauth.call_args_list]
    for indicator_group in {indicator._liot_group_id for indicator in indicator_set}:
        # find matching payload
        matching_payload_candidates = [
            payload for payload in payloads if
            payload['Tags']['indicatorGroupId'] == indicator_group
        ]
        assert len(matching_payload_candidates) == 1
        matching_payload = matching_payload_candidates[0]

        matching_indicators = indicator_set.filter(_liot_group_id=indicator_group)
        expected_keys = {'_time'} | {indicator._liot_id for indicator in matching_indicators}

        assert all(value.keys() == expected_keys for value in matching_payload['Values'])


def test_each_equipment_one_request(mock_oauth, mock_upload_url, make_indicator_set, make_equipment_set):
    indicator_set = make_indicator_set(propertyId=['indicator_id_A', 'indicator_id_B'])
    equipment_set = make_equipment_set(equipmentId=['equipment_A', 'equipment_B'])
    dataset = make_dataset(indicator_set, equipment_set)
    request_base = 'UPLOAD_BASE_URL/Timeseries/extend/Measurements/equipmentId/'
    mock_upload_url.side_effect = lambda x: f'{request_base}{x}'

    upload_indicator_data(dataset)
    urls = {args[0][1] for args in mock_oauth.call_args_list}

    assert mock_oauth.call_count == 2
    assert urls == {request_base + equipment.id for equipment in equipment_set}


def test_aggregate_indicators_in_dataset_raise(make_aggregated_indicator_set, make_equipment_set):
    equipment_set = make_equipment_set(equipmentId=['equipment_A', 'equipment_B'])
    aggregated_indicator_set = make_aggregated_indicator_set(propertyId=['indicator_id_A'])
    dataset = make_dataset(aggregated_indicator_set, equipment_set)

    with pytest.raises(RuntimeError, match='aggregated indicators may not be uploaded to SAP IoT'):
        upload_indicator_data(dataset)
