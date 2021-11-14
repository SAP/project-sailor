import pytest

from sailor.dmc.utils import _dmc_fetch_data
from sailor.utils.utils import DataNotFoundWarning


def test_dmc_fetch_data_expected_filter_processing(mock_request):
    filters = {
        'scenario_id': '123',
        'scenario_version': 1,
        'plant': 'Example_Plant',
        'expected_parameter': 'Expected_Value',
    }
    filter_fields = {
        'scenario_id': 'scenarioID',
        'scenario_version': 'scenarioVersion',
        'plant': 'plant',
        'expected_parameter': 'expectedParameter',
    }
    expected_parameters = {
        'scenarioID': '123',
        'scenarioVersion': '1',
        'plant': 'Example_Plant',
        'expectedParameter': 'Expected_Value',
    }
    expected = mock_request.return_value = ['expected_result']

    with pytest.warns(None) as record:
        actual = _dmc_fetch_data('', filters, filter_fields)

    mock_request.assert_called_once_with('GET', '', params=expected_parameters)
    assert expected == actual
    assert len(record) == 0


def test_dmc_fetch_data_unknown_filter_processing(mock_request):
    filters = {
        'scenario_id': '123',
        'scenario_version': 1,
        'plant': 'Example_Plant',
        'expected_parameter': 'Expected_Value',
        'unexpected_parameter': 'Unexpected_Value',
    }
    filter_fields = {
        'scenario_id': 'scenarioID',
        'scenario_version': 'scenarioVersion',
        'plant': 'plant',
        'expected_parameter': 'expectedParameter',
    }
    expected_parameters = {
        'scenarioID': '123',
        'scenarioVersion': '1',
        'plant': 'Example_Plant',
        'expectedParameter': 'Expected_Value',
        'unexpected_parameter': 'Unexpected_Value',
    }
    expected = mock_request.return_value = ['expected_result']

    with pytest.warns(UserWarning,
                      match=r'^Following parameters are not in our terminology: \[\'unexpected_parameter\'\]$'):
        actual = _dmc_fetch_data('', filters, filter_fields)

    mock_request.assert_called_once_with('GET', '', params=expected_parameters)
    assert expected == actual


def test_dmc_fetch_data_raises_warning_for_empty_result(mock_request):
    filters = {
        'scenario_id': '123',
        'scenario_version': 1,
    }
    filter_fields = {
        'scenario_id': 'scenarioID',
        'scenario_version': 'scenarioVersion',
    }

    mock_request.return_value = []

    with pytest.warns(DataNotFoundWarning, match='No data found for given parameters.'):
        _dmc_fetch_data('', filters, filter_fields)
