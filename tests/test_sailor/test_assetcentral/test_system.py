from unittest.mock import patch

import pytest

from sailor.assetcentral.system import find_systems, SystemSet, System
from sailor.assetcentral import constants


@pytest.mark.filterwarnings('ignore:Following parameters are not in our terminology')
def test_find_functions_expect_fetch_call_args():
    find_params = dict(extended_filters=['integer_param1 < 10'], string_parameter=['Type A', 'Type F'])
    expected_call_args = (['integer_param1 lt 10'], [["string_parameter eq 'Type A'", "string_parameter eq 'Type F'"]])

    with patch.object(System, '_prepare_components'):
        objects = [System({'systemId': x}) for x in ['test_id1', 'test_id2']]
        expected_result = SystemSet(objects)
        with patch('sailor.assetcentral.system._ac_application_url') as mock:
            mock.return_value = 'base_url'
            with patch('sailor.assetcentral.system._fetch_data') as mock_fetch:
                mock_fetch.return_value = [{'systemId': 'test_id1'}, {'systemId': 'test_id2'}]
                actual_result = find_systems(**find_params)

    assert constants.VIEW_SYSTEMS in mock_fetch.call_args.args[0]
    assert mock_fetch.call_args.args[1:] == expected_call_args
    assert actual_result == expected_result
