from unittest.mock import patch

import pytest

from sailor.assetcentral.system import find_systems, SystemSet, System
from sailor.assetcentral import constants


@pytest.mark.filterwarnings('ignore:Following parameters are not in our terminology')
def test_find_functions_expect_fetch_call_args():
    find_params = dict(extended_filters=['integer_param1 < 10'], string_parameter=['Type A', 'Type F'])
    expected_call_args = (['integer_param1 lt 10'], [["string_parameter eq 'Type A'", "string_parameter eq 'Type F'"]])

    # with patch.object(System, '_prepare_components'):
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


def test_traverse_components():
    input = {'id': 'SY0id',
             'name': 'SY0',
             'objectType': 'SYS',
             'childNodes': [{'id': 'SY1-2id',
                             'name': 'SY1-2',
                             'objectType': 'SYS',
                             'childNodes': [{'id': 'EM1-22id',
                                             'name': 'EM1-22',
                                             'objectType': 'EQU',
                                             'childNodes': [],
                                             'model': 'EM1',
                                             'order': '2'},
                                            {'id': 'EM1-21id',
                                             'name': 'EM1-21',
                                             'objectType': 'EQU',
                                             'childNodes': [],
                                             'model': 'EM1',
                                             'order': '1'},
                                            {'id': 'EM2-23id',
                                             'name': 'EM2-23',
                                             'objectType': 'EQU',
                                             'model': 'EM2',
                                             'order': '3'}],
                             'model': 'SY1',
                             'order': '2'},
                            {'id': 'SY1-1id',
                             'name': 'SY1-1',
                             'objectType': 'SYS',
                             'childNodes': [{'id': 'EM1-12id',
                                             'name': 'EM1-12',
                                             'objectType': 'EQU',
                                             'model': 'EM1',
                                             'order': '2'},
                                            {'id': 'EM1-11id',
                                             'name': 'EM1-11',
                                             'objectType': 'EQU',
                                             'model': 'EM1',
                                             'order': '1'},
                                            {'id': 'EM2-13id',
                                             'name': 'EM2-13',
                                             'objectType': 'EQU',
                                             'childNodes': [],
                                             'model': 'EM2',
                                             'order': '3'}],
                             'model': 'SY1',
                             'order': '1'},
                            {'id': 'EM2-3id',
                             'name': 'EM2-3',
                             'objectType': 'EQU',
                             'childNodes': [],
                             'model': 'EM2',
                             'order': '3'}],
             'model': 'SY0',
             'order': None}
    expected_components = {'key': ('SY0', 0),
                           'id': 'SY0id',
                           'name': 'SY0',
                           'order': None,
                           'object_type': 'SYS',
                           'child_list': [{'key': ('SY1', 0),
                                           'id': 'SY1-1id',
                                           'name': 'SY1-1',
                                           'order': '1',
                                           'object_type': 'SYS',
                                           'child_list': [{'key': ('EM1', 0),
                                                           'id': 'EM1-11id',
                                                           'name': 'EM1-11',
                                                           'order': '1',
                                                           'object_type': 'EQU'},
                                                          {'key': ('EM1', 1),
                                                           'id': 'EM1-12id',
                                                           'name': 'EM1-12',
                                                           'order': '2',
                                                           'object_type': 'EQU'},
                                                          {'key': ('EM2', 0),
                                                           'id': 'EM2-13id',
                                                           'name': 'EM2-13',
                                                           'order': '3',
                                                           'object_type': 'EQU',
                                                           'child_list': []}]},
                                          {'key': ('SY1', 1),
                                           'id': 'SY1-2id',
                                           'name': 'SY1-2',
                                           'order': '2',
                                           'object_type': 'SYS',
                                           'child_list': [{'key': ('EM1', 0),
                                                           'id': 'EM1-21id',
                                                           'name': 'EM1-21',
                                                           'order': '1',
                                                           'object_type': 'EQU',
                                                           'child_list': []},
                                                          {'key': ('EM1', 1),
                                                           'id': 'EM1-22id',
                                                           'name': 'EM1-22',
                                                           'order': '2',
                                                           'object_type': 'EQU',
                                                           'child_list': []},
                                                          {'key': ('EM2', 0),
                                                           'id': 'EM2-23id',
                                                           'name': 'EM2-23',
                                                           'order': '3',
                                                           'object_type': 'EQU'}]},
                                          {'key': ('EM2', 0),
                                           'id': 'EM2-3id',
                                           'name': 'EM2-3',
                                           'order': '3',
                                           'object_type': 'EQU',
                                           'child_list': []}]}
    actual_components, equipment_ids, system_ids = System._traverse_components(input, 0, [], [])
    assert actual_components == expected_components
    assert equipment_ids == ['EM2-3id', 'EM1-11id', 'EM1-12id', 'EM2-13id', 'EM1-21id', 'EM1-22id', 'EM2-23id']
    assert system_ids == ['SY1-1id', 'SY1-2id']
