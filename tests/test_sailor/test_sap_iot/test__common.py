import pytest

from sailor.sap_iot._common import _request_extension_url, request_aggregates_url, request_upload_url


def test__request_extension_url_is_cached(mock_request):
    mock_request.return_value = {
        'Extensions': [
            {'Description': 'Write time-series data', 'Service URL': 'some_path'},
        ]
    }

    _request_extension_url('upload', 'ASSETCNTRL')
    _request_extension_url('upload', 'ASSETCNTRL')

    assert mock_request.call_count == 1


def test__request_extension_url_matches_on_description(mock_request):
    expected_path = 'http://upload_service_url'
    other_path = 'http://wrong_service_url'

    mock_request.return_value = {
        'Extensions': [
            {'Description': 'Write time-series data', 'Service URL': expected_path},
            {'Description': 'Unknown desciprtion', 'Service URL': other_path},
            {'Description': 'Read time-series analytics aggregates', 'Service URL': other_path}
        ]
    }

    _request_extension_url.cache_clear()
    path = _request_extension_url('upload', 'ASSETCNTRL')

    assert path == expected_path


def test__request_extension_url_different_services_caching(mock_request):
    first_expected_path = 'http://upload_service_url'
    second_expected_path = 'http://aggregate_service_url'
    other_path = 'http://wrong_service_url'

    mock_request.return_value = {
        'Extensions': [
            {'Description': 'Write time-series data', 'Service URL': first_expected_path},
            {'Description': 'Unknown desciprtion', 'Service URL': other_path},
            {'Description': 'Read time-series analytics aggregates', 'Service URL': second_expected_path}
        ]
    }

    _request_extension_url.cache_clear()
    first_path = _request_extension_url('upload', 'ASSETCNTRL')
    second_path = _request_extension_url('read_aggregates', 'ASSETCNTRL')

    assert first_path == first_expected_path
    assert second_path == second_expected_path


def test__request_extension_url_raises_on_missing_description(mock_request):
    mock_request.return_value = {
        'Extensions': [
            {'Description': 'Write time-series data', 'Service URL': 'http://upload_service_url'},
            {'Description': 'Unknown desciprtion', 'Service URL': 'http://wrong_service_url'},
        ]
    }

    _request_extension_url.cache_clear()
    with pytest.raises(RuntimeError, match='Could not find extension url for service read_aggregates'):
        _request_extension_url('read_aggregates', 'ASSETCNTRL')


def test_request_upload_url_happy_path(mock_request):
    mock_request.return_value = {
        'Extensions': [
            {'Description': 'Write time-series data', 'Service URL': 'http://upload_service_url/{ID}'},
        ]
    }

    url = request_upload_url('equipment_id')

    assert url == 'http://upload_service_url/equipment_id'


def test_request_aggregates_url_happy_path(mock_request):
    service_url = 'http://aggregate_service_url/{indicatorGroupId}/aggregates?fromTime={timestamp}&toTime={timestamp}'
    mock_request.return_value = {
        'Extensions': [
            {'Description': 'Read time-series analytics aggregates', 'Service URL': service_url}
        ]
    }

    url = request_aggregates_url('indicator_group_id', 'start', 'end')

    assert url == 'http://aggregate_service_url/indicator_group_id/aggregates?fromTime=start&toTime=end'


def test_replace_is_independent_of_format_arg_name(mock_request):
    mock_request.return_value = {
        'Extensions': [
            {'Description': 'Write time-series data', 'Service URL': 'http://upload_service_url/{arg_name}'},
        ]
    }

    url = request_upload_url('equipment_id')

    assert url == 'http://upload_service_url/equipment_id'
