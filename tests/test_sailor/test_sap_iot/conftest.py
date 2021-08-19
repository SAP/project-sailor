from unittest.mock import patch

import pytest


@pytest.fixture()
def mock_oauth(mock_config):
    with patch('sailor.utils.oauth_wrapper.OAuthServiceImpl.OAuth2Client.request') as mock:
        yield mock


@pytest.fixture
def mock_fetch(mock_config):
    with patch('sailor.utils.oauth_wrapper.OAuthServiceImpl.OAuth2Client.request') as mock:
        yield mock


@pytest.fixture()
def mock_gzip():
    with patch('sailor.sap_iot.fetch.gzip.GzipFile') as mock:
        yield mock


@pytest.fixture()
def mock_zipfile():
    with patch('sailor.sap_iot.fetch.zipfile') as mock:
        yield mock
