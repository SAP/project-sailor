from unittest.mock import call, patch

import pytest

from sailor.sap_iot.fetch_aggregates import _compose_query_params, get_indicator_aggregates
from sailor.assetcentral.indicators import AggregatedIndicatorSet


@pytest.fixture(autouse=True)
def mock_aggregates_url():
    with patch('sailor.sap_iot.fetch_aggregates.request_aggregates_url', lambda *args: args[0]) as mock:
        yield mock


def make_sample_response(equipment_set, indicator_set, timestamps, duration):
    # modeled on the response of the sap iot extensibility read aggregates api
    # retrieved on 2021-10-07
    # timestamps format should be like '2020-01-01T00:00:00Z'
    # all indicators in the indicator_set must be from one template and group

    def make_row(equipment_id, model_id, indicator_set, timestamp):
        tags = {'modelId': model_id, 'templateId': indicator_set[0].template_id,
                'equipmentId': equipment_id, 'indicatorGroupId': indicator_set[0]._liot_group_id}
        identifiers = {'indicatorGroupId': indicator_set[0]._liot_group_id, 'objectId': equipment_id}
        properties = {'duration': duration, 'time': timestamp}

        for indicator in indicator_set:
            properties[indicator._iot_column_header] = 1
        row = {'tags': tags, 'identifiers': identifiers, 'properties': properties}
        return row

    response = {'results': []}
    for equipment in equipment_set:
        for timestamp in timestamps:
            response['results'].append(make_row(equipment.id, equipment.model_id, indicator_set, timestamp))
    return response


def test_compose_query_params(make_equipment_set, make_aggregated_indicator_set):
    template_id = 'TEMPLATE_ID'
    equipment_set = make_equipment_set(equipmentId=['equipment_id_1', 'equipment_id_2'])
    indicator_set = make_aggregated_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'])
    duration = 'PT2H'

    result = _compose_query_params(template_id, equipment_set, indicator_set, duration)

    assert result['duration'] == duration
    assert result['select'] == ','.join(f'{i._liot_id}_{i.aggregation_function}' for i in indicator_set)
    assert f'"templateId" = \'{template_id}\'' in result['tagsFilter']
    assert all(f'"equipmentId"=\'{equipment.id}\'' in result['tagsFilter'] for equipment in equipment_set)


def test_get_indicator_aggregates_happy_path(make_equipment_set, make_indicator_set, mock_config, mock_fetch):
    start, end = '2020-01-01 00:00:00+00:00', '2020-02-01 00:00:00+00:00'
    equipment_set = make_equipment_set(equipmentId=['equipment_id_1', 'equipment_id_2'],
                                       modelId=['equi_model', 'equi_model'])
    indicator_set = make_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'])
    aggregated_indicator_set = AggregatedIndicatorSet._from_indicator_set_and_aggregation_functions(indicator_set,
                                                                                                    ['MIN', 'MAX'])
    interval = 'PT1D'
    timestamps = ['2020-01-02T00:00:00Z', '2020-01-03T00:00:00Z', '2020-01-04T00:00:00Z']

    test_response = make_sample_response(equipment_set, aggregated_indicator_set, timestamps, interval)
    mock_fetch.side_effect = [test_response]

    result = get_indicator_aggregates(start, end, indicator_set, equipment_set, ['MIN', 'MAX'], interval)

    assert all([equipment.id in result._df['equipment_id'].values for equipment in equipment_set])
    assert all([indicator._unique_id in result._df.columns for indicator in aggregated_indicator_set])
    assert len(result._df) == len(timestamps) * len(equipment_set)


def test_get_indicator_aggregates_with_pagination(make_equipment_set, make_indicator_set, mock_config, mock_fetch):
    start, end = '2020-01-01 00:00:00+00:00', '2020-02-01 00:00:00+00:00'
    equipment_set = make_equipment_set(equipmentId=['equipment_id_1', 'equipment_id_2'],
                                       modelId=['equi_model', 'equi_model'])
    indicator_set = make_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'])
    aggregated_indicator_set = AggregatedIndicatorSet._from_indicator_set_and_aggregation_functions(indicator_set,
                                                                                                    ['MIN', 'MAX'])
    interval = 'PT1D'
    timestamps = ['2020-01-02T00:00:00Z', '2020-01-03T00:00:00Z', '2020-01-04T00:00:00Z',
                  '2020-01-05T00:00:00Z', '2020-01-06T00:00:00Z', '2020-01-07T00:00:00Z']
    first_resp = make_sample_response(equipment_set, aggregated_indicator_set, timestamps[:3], interval)
    first_resp['nextLink'] = 'NEXT_LINK_URL'
    second_resp = make_sample_response(equipment_set, aggregated_indicator_set, timestamps[3:], interval)

    mock_fetch.side_effect = [first_resp, second_resp]

    result = get_indicator_aggregates(start, end, indicator_set, equipment_set, ['MIN', 'MAX'], interval)

    mock_fetch.assert_has_calls([call('GET', 'NEXT_LINK_URL')])
    assert all([equipment.id in result._df['equipment_id'].values for equipment in equipment_set])
    assert all([indicator._unique_id in result._df.columns for indicator in aggregated_indicator_set])
    assert len(result._df) == len(timestamps) * len(equipment_set)


def test_get_indicator_aggregates_two_groups(make_equipment_set, make_indicator_set, mock_config):
    start, end = '2020-01-01 00:00:00+00:00', '2020-02-01 00:00:00+00:00'
    equipment_set = make_equipment_set(equipmentId=['equipment_id_1', 'equipment_id_2'],
                                       modelId=['equi_model', 'equi_model'])
    indicator_set = make_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'], pstid=['group_1', 'group_2'])
    aggregated_indicator_set = AggregatedIndicatorSet._from_indicator_set_and_aggregation_functions(indicator_set,
                                                                                                    ['MIN', 'MAX'])
    interval = 'PT1D'
    timestamps = ['2020-01-02T00:00:00Z', '2020-01-03T00:00:00Z', '2020-01-04T00:00:00Z']

    first_resp = make_sample_response(equipment_set, aggregated_indicator_set.filter(indicator_group_id='group_1'),
                                      timestamps, interval)
    second_resp = make_sample_response(equipment_set, aggregated_indicator_set.filter(indicator_group_id='group_2'),
                                       timestamps, interval)

    def mock_request(self, method, endpoint, params):
        if endpoint == 'IG_group_1':
            return first_resp
        return second_resp

    with patch('sailor.utils.oauth_wrapper.OAuthServiceImpl.OAuth2Client.request', mock_request):
        result = get_indicator_aggregates(start, end, indicator_set, equipment_set, ['MIN', 'MAX'], interval)

    assert all([equipment.id in result._df['equipment_id'].values for equipment in equipment_set])
    assert all([indicator._unique_id in result._df.columns for indicator in aggregated_indicator_set])
    assert len(result._df) == len(timestamps) * len(equipment_set)
