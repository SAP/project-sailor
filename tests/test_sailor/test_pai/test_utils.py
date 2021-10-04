from unittest.mock import patch

import pytest

from sailor.pai.utils import _pai_fetch_data, _pai_resulthandler


@pytest.fixture
def fetch_mock(mock_config):
    with patch('sailor.utils.oauth_wrapper.OAuthServiceImpl.OAuth2Client.request') as mock:
        yield mock


def test_pai_resulthandler():
    result_list = ['dummy']
    endpoint_data = {'d': {'results': ['result1', 'result2']}}
    expected = ['dummy', 'result1', 'result2']
    actual = _pai_resulthandler(result_list, endpoint_data)
    assert actual == expected


def test_pai_fetch_data_integration(fetch_mock):
    unbreakable_filters = ["location eq 'Walldorf'"]
    breakable_filters = [["manufacturer eq 'abcCorp'"]]
    expected_parameters = {'$filter': "location eq 'Walldorf' and (manufacturer eq 'abcCorp')",
                           '$format': 'json'}
    expected = ['result1', 'result2']
    fetch_mock.return_value = {'d': {'results': expected}}

    actual = _pai_fetch_data('', unbreakable_filters, breakable_filters)

    fetch_mock.assert_called_once_with('GET', '', params=expected_parameters)
    assert actual == expected
