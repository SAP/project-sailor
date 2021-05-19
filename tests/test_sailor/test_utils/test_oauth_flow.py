# -*- coding: utf-8 -*-

from unittest.mock import patch, MagicMock
from datetime import datetime

from rauth import OAuth2Session
import jwt
import pytest

from sailor.utils.oauth_wrapper.OAuthServiceImpl import OAuth2Client, RequestError


@pytest.fixture(autouse=True, scope='module')
def mock_config():
    with patch('sailor.utils.config.SailorConfig') as mock:
        yield mock


def test_request_sets_json_by_default():
    oauth_client = OAuth2Client('test_client')
    session_mock = MagicMock(OAuth2Session)

    with patch.object(oauth_client, '_get_session', return_value=session_mock):
        oauth_client.request('METHOD', 'http://testurl.com')

    session_mock.request.assert_called_once_with('METHOD', 'http://testurl.com', headers={'Accept': 'application/json'})


@pytest.mark.parametrize('headers,expected_headers', [
    (None, None),
    ({}, {}),
    ({'Accept': 'application/octet-stream'}, {'Accept': 'application/octet-stream'}),
    ({'some-header': 'value'}, {'some-header': 'value'})])
def test_request_does_not_modify_headers_if_specified(headers, expected_headers):
    oauth_client = OAuth2Client('test_client')
    session_mock = MagicMock(OAuth2Session)

    with patch.object(oauth_client, '_get_session', return_value=session_mock):
        oauth_client.request('METHOD', 'http://testurl.com', headers=headers)

    session_mock.request.assert_called_once_with('METHOD', 'http://testurl.com', headers=expected_headers)


def test_request_converts_params_to_odata_url_on_get():
    oauth_client = OAuth2Client('test_client')
    session_mock = MagicMock(OAuth2Session)
    current_url = 'https://some-service-url.to/api/resource?hello=world&old=true'
    params = {'old': 'false', 'new': 'true', '$format': 'json'}
    expected_url = 'https://some-service-url.to/api/resource?hello=world&old=false&new=true&%24format=json'

    with patch.object(oauth_client, '_get_session', return_value=session_mock):
        oauth_client.request('GET', current_url, params=params)

    session_mock.request.assert_called_once_with('GET', expected_url, headers={'Accept': 'application/json'})


def test_request_raises_error_when_response_not_ok():
    mock_response = MagicMock()
    mock_response.ok = False
    session_mock = MagicMock(OAuth2Session)
    session_mock.request.return_value = mock_response
    oauth_client = OAuth2Client('test_service')

    with patch.object(oauth_client, '_get_session', return_value=session_mock):
        with pytest.raises(RequestError):
            oauth_client.request('GET', 'some_url')


def test_scopes_config_not_available():
    scope_config = {}

    oauth_flow = OAuth2Client('test_service', scope_config)
    oauth_flow._resolve_configured_scopes()
    assert oauth_flow.resolved_scopes == [], 'OAuthFlow must not have scopes'


def test_scopes_config_available_token_available():
    scope_config = {
        'test_service': ['scope1', 'scope2', 'scope3']
    }

    encoded_token = jwt.encode({
        'scope': ['foo!scope1', 'bar!scope2', 'foobar!scope3']
    }, 'some_secret')

    oauth_flow = OAuth2Client('test_service', scope_config)

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

    oauth_flow = OAuth2Client('test_service', scope_config)

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
    oauth_flow = OAuth2Client('test_service', scope_config)

    with patch('rauth.OAuth2Service.get_auth_session') as mock_method:
        mock_method.return_value.access_token_response.json.return_value = {'access_token': invalid_encoded_token}
        with pytest.warns(UserWarning, match=r'Could not resolve all scopes'):
            oauth_flow._resolve_configured_scopes()

    assert oauth_flow.resolved_scopes == [], 'Scopes must be empty'
    mock_method.assert_called_once()


@patch('jwt.decode', return_value={'exp': datetime(9999, 12, 31).timestamp()})
@patch('rauth.OAuth2Service.get_auth_session')
def test_get_session_returns_active_session_on_repeated_calls(get_auth_mock, decode_mock):
    expected_session = MagicMock()
    get_auth_mock.return_value = expected_session
    oauth_flow = OAuth2Client('test_service')

    oauth_flow._get_session()
    actual = oauth_flow._get_session()

    get_auth_mock.assert_called_once()
    assert actual == expected_session


@patch('jwt.decode', return_value={'exp': datetime(9999, 12, 31).timestamp(),
                                   'scope': ['test']})
@patch('rauth.OAuth2Service.get_auth_session')
def test_get_session_returns_new_session_if_scopes_are_different(get_auth_mock, decode_mock):
    new_scopes_requested = 'abc def'
    expected_session = MagicMock()
    get_auth_mock.return_value = expected_session
    oauth_flow = OAuth2Client('test_service')
    oauth_flow._active_session = MagicMock()

    actual = oauth_flow._get_session(scope=new_scopes_requested)

    get_auth_mock.assert_called_once()
    assert actual == expected_session


@patch('time.time', return_value=6*60)
@patch('jwt.decode', return_value={'exp': 10*60})
@patch('rauth.OAuth2Service.get_auth_session')
def test_get_session_returns_new_session_if_about_to_expire(get_auth_mock, decode_mock, time_mock):
    expected_session = MagicMock()
    get_auth_mock.return_value = expected_session
    oauth_flow = OAuth2Client('test_service')
    oauth_flow._active_session = MagicMock()

    actual = oauth_flow._get_session()

    get_auth_mock.assert_called_once()
    assert actual == expected_session
