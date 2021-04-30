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
                                             'childNodes': [],
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
                                             'childNodes': [],
                                             'model': 'EM1',
                                             'order': '2'},
                                            {'id': 'EM1-11id',
                                             'name': 'EM1-11',
                                             'objectType': 'EQU',
                                             'childNodes': [],
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
                                                           'object_type': 'EQU',
                                                           'child_list': []},
                                                          {'key': ('EM1', 1),
                                                           'id': 'EM1-12id',
                                                           'name': 'EM1-12',
                                                           'order': '2',
                                                           'object_type': 'EQU',
                                                           'child_list': []},
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
                                                           'object_type': 'EQU',
                                                           'child_list': []}]},
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


def test_create_selection_dictionary(make_indicator_set):
    ind11 = make_indicator_set(propertyId=['1', '2'])
    ind12 = make_indicator_set(propertyId=['3', '4'])
    ind13 = make_indicator_set(propertyId=['5', '6'])
    ind21 = make_indicator_set(propertyId=['7', '8'])
    ind22 = make_indicator_set(propertyId=['9', '10'])
    ind23 = make_indicator_set(propertyId=['11', '12'])
    ind3 = make_indicator_set(propertyId=['13', '14'])
    comp_tree = {'id': '20D9CDD669B846109CE9669BA7ABCB36',
                 'name': 'SY0',
                 'order': None,
                 'object_type': 'SYS',
                 'child_nodes': {('D5D8A6688B104C668634533ADCE341C9', 0):
                                 {'id': '2262176B8E5F440CAEA8D2C39BC1A42C',
                                  'name': 'SY1-1',
                                  'order': '1',
                                  'object_type': 'SYS',
                                  'child_nodes': {('58B68B12A92F457CA87393A87954A49C', 0):
                                                  {'id': 'DBB7885268EB41E3BF157AB890CCA1EF',
                                                   'name': 'EM1-11',
                                                   'order': '1',
                                                   'object_type': 'EQU',
                                                   'indicators': ind11,
                                                   'child_nodes': {}},
                                                  ('58B68B12A92F457CA87393A87954A49C', 1):
                                                  {'id': '042F55EF70BE49538BB6DA3F32B8738C',
                                                   'name': 'EM1-12',
                                                   'order': '2',
                                                   'object_type': 'EQU',
                                                   'indicators': ind12,
                                                   'child_nodes': {}},
                                                  ('2AD36C14827E468AB35624AD21AD18C7', 0):
                                                  {'id': 'A1ADCEA69C95454DA9FE19863804A0D6',
                                                   'name': 'EM2-13',
                                                   'order': '3',
                                                   'object_type': 'EQU',
                                                   'indicators': ind13,
                                                   'child_nodes': {}}}},
                                 ('D5D8A6688B104C668634533ADCE341C9', 1):
                                 {'id': '7788327C06844D24943AA59E2E14BB04',
                                  'name': 'SY1-2',
                                  'order': '2',
                                  'object_type': 'SYS',
                                  'child_nodes': {('58B68B12A92F457CA87393A87954A49C', 0):
                                                  {'id': 'F988369A34404644A8DC470220FBBE34',
                                                   'name': 'EM1-21',
                                                   'order': '1',
                                                   'object_type': 'EQU',
                                                   'indicators': ind21,
                                                   'child_nodes': {}},
                                                  ('58B68B12A92F457CA87393A87954A49C', 1):
                                                  {'id': '8C3114ACDF854084B50EB19D61C0FC9F',
                                                   'name': 'EM1-22',
                                                   'order': '2',
                                                   'object_type': 'EQU',
                                                   'indicators': ind22,
                                                   'child_nodes': {}},
                                                  ('2AD36C14827E468AB35624AD21AD18C7',  0):
                                                  {'id': '4B8FB57B3F684F838F82BDDDB377AC76',
                                                   'name': 'EM2-23',
                                                   'order': '3',
                                                   'object_type': 'EQU',
                                                   'indicators': ind23,
                                                   'child_nodes': {}}}},
                                 ('2AD36C14827E468AB35624AD21AD18C7', 0):
                                 {'id': '0E779D3EA3C54F379AC89A7C539EDCFE',
                                  'name': 'EM2-3',
                                  'order': '3',
                                  'object_type': 'EQU',
                                  'indicators': ind3,
                                  'child_nodes': {}}}}
    expected_sel_dict = {'object_type': 'SYS',
                         'child_nodes': [{'object_type': 'SYS',
                                          'child_nodes': [{'object_type': 'EQU',
                                                           'indicators': ind11,
                                                           'child_nodes': [],
                                                           'key': ('58B68B12A92F457CA87393A87954A49C', 0)},
                                                          {'object_type': 'EQU',
                                                           'indicators': ind12,
                                                           'child_nodes': [],
                                                           'key': ('58B68B12A92F457CA87393A87954A49C', 1)},
                                                          {'object_type': 'EQU',
                                                           'indicators': ind13,
                                                           'child_nodes': [],
                                                           'key': ('2AD36C14827E468AB35624AD21AD18C7', 0)}],
                                          'key': ('D5D8A6688B104C668634533ADCE341C9', 0)},
                                         {'object_type': 'SYS',
                                          'child_nodes': [{'object_type': 'EQU',
                                                           'indicators': ind21,
                                                           'child_nodes': [],
                                                           'key': ('58B68B12A92F457CA87393A87954A49C', 0)},
                                                          {'object_type': 'EQU',
                                                           'indicators': ind22,
                                                           'child_nodes': [],
                                                           'key': ('58B68B12A92F457CA87393A87954A49C', 1)},
                                                          {'object_type': 'EQU',
                                                           'indicators': ind23,
                                                           'child_nodes': [],
                                                           'key': ('2AD36C14827E468AB35624AD21AD18C7', 0)}],
                                          'key': ('D5D8A6688B104C668634533ADCE341C9', 1)},
                                         {'object_type': 'EQU',
                                          'indicators': ind3,
                                          'child_nodes': [],
                                          'key': ('2AD36C14827E468AB35624AD21AD18C7', 0)}]}
    actual_sel_dict = System._create_selection_dictionary(comp_tree)
    assert actual_sel_dict == expected_sel_dict


def test_fill_nones(make_indicator_set):
    ind1 = make_indicator_set(propertyId=['1', '2'])
    ind2 = make_indicator_set(propertyId=['3', '4'])
    ind3 = make_indicator_set(propertyId=['5', '6'])
    child_nodes = [{'object_type': 'SYS',
                    'child_nodes': [{'object_type': 'EQU',
                                     'indicators': ind1,
                                     'child_nodes': [],
                                     'key': ('58B68B12A92F457CA87393A87954A49C', 0)},
                                    {'object_type': 'EQU',
                                     'indicators': ind2,
                                     'child_nodes': [],
                                     'key': ('58B68B12A92F457CA87393A87954A49C', 1)},
                                    {'object_type': 'EQU',
                                     'indicators': ind3,
                                     'child_nodes': [],
                                     'key': ('2AD36C14827E468AB35624AD21AD18C7', 0)}],
                    'key': ('D5D8A6688B104C668634533ADCE341C9', 0)}]
    indicator_list = []
    none_positions = set()
    SystemSet._fill_nones(child_nodes, indicator_list, none_positions)
    assert indicator_list == [None, None, None, None, None, None]
    assert none_positions == {0, 1, 2, 3, 4, 5}


def test_map_comp_info(make_indicator_set):
    ind1 = make_indicator_set(propertyId=['1', '2'])
    ind2 = make_indicator_set(propertyId=['3', '4'])
    ind3 = make_indicator_set(propertyId=['5', '6'])
    selec_nodes = [{'object_type': 'SYS',
                    'child_nodes': [{'object_type': 'EQU',
                                     'indicators': ind1,
                                     'child_nodes': [],
                                     'key': ('58B68B12A92F457CA87393A87954A49C', 0)},
                                    {'object_type': 'EQU',
                                     'indicators': ind2,
                                     'child_nodes': [],
                                     'key': ('58B68B12A92F457CA87393A87954A49C', 1)},
                                    {'object_type': 'EQU',
                                     'indicators': ind3,
                                     'child_nodes': [],
                                     'key': ('2AD36C14827E468AB35624AD21AD18C7', 0)}],
                    'key': ('D5D8A6688B104C668634533ADCE341C9', 0)}]
    system_nodes = {('D5D8A6688B104C668634533ADCE341C9', 0):
                    {'id': '2262176B8E5F440CAEA8D2C39BC1A42C',
                     'name': 'SY1-1',
                     'order': '1',
                     'object_type': 'SYS',
                     'child_nodes': {('58B68B12A92F457CA87393A87954A49C', 0):
                                     {'id': 'DBB7885268EB41E3BF157AB890CCA1EF',
                                      'name': 'EM1-11',
                                      'order': '1',
                                      'object_type': 'EQU',
                                      'indicators': ind1,
                                      'child_nodes': {}},
                                     ('2AD36C14827E468AB35624AD21AD18C7', 0):
                                     {'id': 'A1ADCEA69C95454DA9FE19863804A0D6',
                                      'name': 'EM2-13',
                                      'order': '3',
                                      'object_type': 'EQU',
                                      'indicators': ind3,
                                      'child_nodes': {}}}}}
    expected_indicators = [('DBB7885268EB41E3BF157AB890CCA1EF', ind1[0]), ('DBB7885268EB41E3BF157AB890CCA1EF', ind1[1]),
                           None, None,
                           ('A1ADCEA69C95454DA9FE19863804A0D6', ind3[0]), ('A1ADCEA69C95454DA9FE19863804A0D6', ind3[1])]
    indicator_list = []
    none_positions = set()
    SystemSet._map_comp_info(selec_nodes, system_nodes, indicator_list, none_positions)
    print(indicator_list)
    print(indicator_list[0][1])
    print(ind1[0])
    assert indicator_list == expected_indicators
    assert none_positions == {2, 3}
