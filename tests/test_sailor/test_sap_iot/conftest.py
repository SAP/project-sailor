from unittest.mock import patch

import pytest


@pytest.fixture()
def mock_gzip():
    with patch('sailor.sap_iot.fetch.gzip.GzipFile') as mock:
        yield mock


@pytest.fixture()
def mock_zipfile():
    with patch('sailor.sap_iot.fetch.zipfile') as mock:
        yield mock
