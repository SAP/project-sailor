# -*- coding: utf-8 -*-

from unittest.mock import patch, Mock

import jwt
import pytest

from sailor.utils.oauth_wrapper.OAuthServiceImpl import OAuthFlow


@pytest.fixture(autouse=True, scope='module')
def mock_config():
    with patch('sailor.utils.config.SailorConfig') as mock:
        yield mock


def test_fetch_endpoint_data_url_parameters():
    mock_session = Mock()
    mock_session.request.return_value = Mock(headers={'Content-Type': 'application/json'})
    oauth_flow = OAuthFlow('test_service', {})

    current_url = 'https://some-service-url.to/api/resource?hello=world&old=true'
    parameters = {'old': 'false', 'new': 'true'}

    expected_url = 'https://some-service-url.to/api/resource?hello=world&old=false&new=true&%24format=json'

    with patch.object(oauth_flow, '_get_session', return_value=mock_session):
        oauth_flow.fetch_endpoint_data(current_url, 'GET', parameters)
    mock_session.request.assert_called_once_with('GET', expected_url)


def test_fetch_endpoint_data():
    expected_data = {'a': 1, 'b': True, 'c': '42'}

    class MockResponse:
        ok = True
        headers = {'Content-Type': 'application/json'}

        def json(self):
            return expected_data

    scope_config = {
        'test_service': ['scope1', 'scope2', 'scope3']
    }

    full_scopes = ['foo!scope1', 'bar!scope2', 'foobar!scope3']
    encoded_token = jwt.encode({'scope': full_scopes}, 'some_secret')

    oauth_flow = OAuthFlow('test_service', scope_config)

    with patch.object(oauth_flow, '_get_session') as get_session_mock:
        get_session_mock.return_value.access_token_response.json.return_value = {'access_token': encoded_token}
        get_session_mock.return_value.request.return_value = MockResponse()
        result_data = oauth_flow.fetch_endpoint_data('https://some-service-url.to/api/resource', 'GET')

    assert expected_data == result_data
    params = get_session_mock.call_args[0][0]
    assert params['scope'] == ' '.join(full_scopes), 'Wrong scopes provided to oauth session'


def test_scopes_config_not_available():
    scope_config = {}

    oauth_flow = OAuthFlow('test_service', scope_config)
    oauth_flow._resolve_configured_scopes()
    assert oauth_flow.resolved_scopes == [], 'OAuthFlow must not have scopes'


def test_scopes_config_available_token_available():
    scope_config = {
        'test_service': ['scope1', 'scope2', 'scope3']
    }

    encoded_token = jwt.encode({
        'scope': ['foo!scope1', 'bar!scope2', 'foobar!scope3']
    }, 'some_secret')

    oauth_flow = OAuthFlow('test_service', scope_config)

    with patch('rauth.OAuth2Service.get_auth_session') as mock_method:
        mock_method.return_value.access_token_response.json.return_value = {'access_token': encoded_token}
        oauth_flow._resolve_configured_scopes()

    assert oauth_flow.resolved_scopes == ['foo!scope1', 'bar!scope2', 'foobar!scope3'], (
        'Scopes have been resolved incorrectly')
    mock_method.assert_called_once()


def test_scopes_config_available_getting_token_fails():
    scope_config = {
        'test_service': ['scope1', 'scope2', 'scope3']
    }

    oauth_flow = OAuthFlow('test_service', scope_config)

    with patch.object(oauth_flow, '_get_session', side_effect=Exception) as mock_method:
        with pytest.raises(Exception):
            oauth_flow._resolve_configured_scopes()

    assert oauth_flow.resolved_scopes == [], 'Scopes must be empty'
    mock_method.assert_called_once()


@patch('jwt.decode', return_value={'scope': []})
def test_scopes_config_available_decoding_token_fails(jwt_decode_mock):
    scope_config = {
        'test_service': ['scope1', 'scope2', 'scope3']
    }
    invalid_encoded_token = 'xxxxxxxxxx'  # nosec
    oauth_flow = OAuthFlow('test_service', scope_config)

    with patch('rauth.OAuth2Service.get_auth_session') as mock_method:
        mock_method.return_value.access_token_response.json.return_value = {'access_token': invalid_encoded_token}
        with pytest.warns(UserWarning, match=r'Could not resolve all scopes'):
            oauth_flow._resolve_configured_scopes()

    assert oauth_flow.resolved_scopes == [], 'Scopes must be empty'
    mock_method.assert_called_once()
