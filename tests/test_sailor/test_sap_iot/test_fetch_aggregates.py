from unittest.mock import call, patch

import pandas as pd
import pytest

from sailor.sap_iot.fetch_aggregates import _compose_query_params, get_indicator_aggregates
from sailor.assetcentral.indicators import AggregatedIndicatorSet
from sailor.utils.utils import DataNotFoundWarning


@pytest.fixture(autouse=True)
def mock_aggregates_url():
    with patch('sailor.sap_iot.fetch_aggregates.request_aggregates_url', lambda *args: args[0]) as mock:
        yield mock


@pytest.fixture()
def prepare_setup(make_equipment_set, make_indicator_set):
    def maker():
        start, end = '2020-01-01 00:00:00+00:00', '2020-02-01 00:00:00+00:00'
        equipment_set = make_equipment_set(equipmentId=['equipment_id_1', 'equipment_id_2'],
                                           modelId=['equi_model', 'equi_model'])
        indicator_set = make_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'])
        aggregated_indicator_set = AggregatedIndicatorSet._from_indicator_set_and_aggregation_functions(indicator_set,
                                                                                                        ['MIN', 'MAX'])
        return start, end, equipment_set, indicator_set, aggregated_indicator_set
    return maker


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


def test_get_indicator_aggregates_happy_path(mock_config, mock_request, prepare_setup):
    start, end, equipment_set, indicator_set, aggregated_indicator_set = prepare_setup()
    timestamps = ['2020-01-02T00:00:00Z', '2020-01-03T00:00:00Z', '2020-01-04T00:00:00Z']

    test_response = make_sample_response(equipment_set, aggregated_indicator_set, timestamps, '1D')
    mock_request.side_effect = [test_response]

    result = get_indicator_aggregates(start, end, indicator_set, equipment_set, ['MIN', 'MAX'], 'P1D')

    assert all([equipment.id in result._df['equipment_id'].values for equipment in equipment_set])
    assert all([indicator._unique_id in result._df.columns for indicator in aggregated_indicator_set])
    assert len(result._df) == len(timestamps) * len(equipment_set)


def test_get_indicator_aggregates_with_pagination(mock_config, mock_request, prepare_setup):
    start, end, equipment_set, indicator_set, aggregated_indicator_set = prepare_setup()
    timestamps = ['2020-01-02T00:00:00Z', '2020-01-03T00:00:00Z', '2020-01-04T00:00:00Z',
                  '2020-01-05T00:00:00Z', '2020-01-06T00:00:00Z', '2020-01-07T00:00:00Z']
    first_resp = make_sample_response(equipment_set, aggregated_indicator_set, timestamps[:3], '1D')
    first_resp['nextLink'] = 'NEXT_LINK_URL'
    second_resp = make_sample_response(equipment_set, aggregated_indicator_set, timestamps[3:], '1D')

    mock_request.side_effect = [first_resp, second_resp]

    result = get_indicator_aggregates(start, end, indicator_set, equipment_set, ['MIN', 'MAX'], 'P1D')

    mock_request.assert_has_calls([call('GET', 'NEXT_LINK_URL')])
    assert all([equipment.id in result._df['equipment_id'].values for equipment in equipment_set])
    assert all([indicator._unique_id in result._df.columns for indicator in aggregated_indicator_set])
    assert len(result._df) == len(timestamps) * len(equipment_set)


@pytest.mark.parametrize('requested_interval,returned_interval,warning', [
    (pd.Timedelta('P1D'), '1D', False),
    (pd.Timedelta('PT24H'), '1D', False),
    (pd.Timedelta('P1D'), 'T24H', False),
    (pd.Timedelta('P14D'), 'T336H', False),
    ('P1D', '1D', False),
    ('PT24H', '1D', False),
    ('P1D', 'T24H', False),
    ('P14D', 'T336H', False),
    (pd.Timedelta('PT3H'), 'T1H', True),
    (pd.Timedelta('P15D'), 'T336H', True),
    ('PT3H', 'T1H', True),
    ('P15D', 'T336H', True),
    (None, 'ALL(T3H)', False)
])
def test_get_indicator_aggregates_timestamp_warning(requested_interval, returned_interval, warning,
                                                    prepare_setup, mock_config, mock_request):
    start, end, equipment_set, indicator_set, aggregated_indicator_set = prepare_setup()
    timestamps = ['2020-01-02T00:00:00Z', '2020-01-03T00:00:00Z', '2020-01-04T00:00:00Z']
    test_response = make_sample_response(equipment_set, aggregated_indicator_set, timestamps, returned_interval)
    mock_request.side_effect = [test_response]

    with pytest.warns(None) as record:
        get_indicator_aggregates(start, end, indicator_set, equipment_set, ['MIN', 'MAX'], requested_interval)

    if warning:
        assert len(record) == 1
        assert str(record[0].message).startswith('The aggregation interval returned by the query')
    else:
        assert not record, record[0].message


def test_get_indicator_aggregates_two_groups(mock_config, make_indicator_set, prepare_setup):
    start, end, equipment_set, _, _ = prepare_setup()
    indicator_set = make_indicator_set(propertyId=['indicator_id_1', 'indicator_id_2'], pstid=['group_1', 'group_2'])
    aggregated_indicator_set = AggregatedIndicatorSet._from_indicator_set_and_aggregation_functions(indicator_set,
                                                                                                    ['MIN', 'MAX'])
    timestamps = ['2020-01-02T00:00:00Z', '2020-01-03T00:00:00Z', '2020-01-04T00:00:00Z']

    first_resp = make_sample_response(equipment_set, aggregated_indicator_set.filter(indicator_group_id='group_1'),
                                      timestamps, '1D')
    second_resp = make_sample_response(equipment_set, aggregated_indicator_set.filter(indicator_group_id='group_2'),
                                       timestamps, '1D')

    def mock_request(self, method, endpoint, params):
        if endpoint == 'IG_group_1':
            return first_resp
        return second_resp

    with patch('sailor.utils.oauth_wrapper.OAuthServiceImpl.OAuth2Client.request', mock_request):
        result = get_indicator_aggregates(start, end, indicator_set, equipment_set, ['MIN', 'MAX'], 'P1D')

    assert all([equipment.id in result._df['equipment_id'].values for equipment in equipment_set])
    assert all([indicator._unique_id in result._df.columns for indicator in aggregated_indicator_set])
    assert len(result._df) == len(timestamps) * len(equipment_set)


def test_get_indicator_aggregates_empty_response(mock_config, mock_request, prepare_setup):
    start, end, equipment_set, indicator_set, aggregated_indicator_set = prepare_setup()
    timestamps = []

    test_response = make_sample_response(equipment_set, aggregated_indicator_set, timestamps, '1D')
    mock_request.side_effect = [test_response]

    with pytest.warns(DataNotFoundWarning, match='Could not find any data for the requested period.'):
        dataset = get_indicator_aggregates(start, end, indicator_set, equipment_set, ['MIN', 'MAX'], 'P1D')

    dataset.as_df()
