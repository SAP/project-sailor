import pytest

from sailor.assetcentral.system import SystemSet, System, create_analysis_table
from tests.test_sailor.data_generators import make_dataset


# expected result of _traverse_components and input for _update_components
systemcomponents_global = {'key': ('SY0', 0),
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


# expected result of _update_components and input for _create_selection_dictionary
@pytest.fixture
def component_tree(make_indicator_set):
    ind1 = make_indicator_set(propertyId=['1', '2'])
    ind2 = make_indicator_set(propertyId=['3', '4'])
    expected_tree = {'key': ('SY0', 0),
                     'id': 'SY0id',
                     'name': 'SY0',
                     'order': None,
                     'object_type': 'SYS',
                     'child_nodes': {('SY1', 0):
                                     {'id': 'SY1-1id',
                                      'name': 'SY1-1',
                                      'order': '1',
                                      'object_type': 'SYS',
                                      'child_nodes': {('EM1', 0):
                                                      {'id': 'EM1-11id',
                                                       'name': 'EM1-11',
                                                       'order': '1',
                                                       'object_type': 'EQU',
                                                       'indicators': ind1,
                                                       'child_nodes': {}},
                                                      ('EM1', 1):
                                                      {'id': 'EM1-12id',
                                                       'name': 'EM1-12',
                                                       'order': '2',
                                                       'object_type': 'EQU',
                                                       'indicators': ind1,
                                                       'child_nodes': {}},
                                                      ('EM2', 0):
                                                      {'id': 'EM2-13id',
                                                       'name': 'EM2-13',
                                                       'order': '3',
                                                       'object_type': 'EQU',
                                                       'indicators': ind2,
                                                       'child_nodes': {}}}},
                                     ('SY1', 1):
                                     {'id': 'SY1-2id',
                                      'name': 'SY1-2',
                                      'order': '2',
                                      'object_type': 'SYS',
                                      'child_nodes': {('EM1', 0):
                                                      {'id': 'EM1-21id',
                                                       'name': 'EM1-21',
                                                       'order': '1',
                                                       'object_type': 'EQU',
                                                       'indicators': ind1,
                                                       'child_nodes': {}},
                                                      ('EM1', 1):
                                                      {'id': 'EM1-22id',
                                                       'name': 'EM1-22',
                                                       'order': '2',
                                                       'object_type': 'EQU',
                                                       'indicators': ind1,
                                                       'child_nodes': {}},
                                                      ('EM2', 0):
                                                      {'id': 'EM2-23id',
                                                       'name': 'EM2-23',
                                                       'order': '3',
                                                       'object_type': 'EQU',
                                                       'indicators': ind2,
                                                       'child_nodes': {}}}},
                                     ('EM2', 0):
                                     {'id': 'EM2-3id',
                                      'name': 'EM2-3',
                                      'order': '3',
                                      'object_type': 'EQU',
                                      'indicators': ind2,
                                      'child_nodes': {}}}}
    return expected_tree


# expected result of _create_selection_dictionary and input for _map_component_information
@pytest.fixture
def selection_dictionary(make_indicator_set):
    ind1 = make_indicator_set(propertyId=['1', '2'])
    ind2 = make_indicator_set(propertyId=['3', '4'])
    select_dictionary = {'object_type': 'SYS',
                         'child_nodes': [{'object_type': 'SYS',
                                          'child_nodes': [{'object_type': 'EQU',
                                                           'indicators': ind1,
                                                           'child_nodes': [],
                                                           'key': ('EM1', 0)},
                                                          {'object_type': 'EQU',
                                                           'indicators': ind1,
                                                           'child_nodes': [],
                                                           'key': ('EM1', 1)},
                                                          {'object_type': 'EQU',
                                                           'indicators': ind2,
                                                           'child_nodes': [],
                                                           'key': ('EM2', 0)}],
                                          'key': ('SY1', 0)},
                                         {'object_type': 'SYS',
                                          'child_nodes': [{'object_type': 'EQU',
                                                           'indicators': ind1,
                                                           'child_nodes': [],
                                                           'key': ('EM1', 0)},
                                                          {'object_type': 'EQU',
                                                           'indicators': ind1,
                                                           'child_nodes': [],
                                                           'key': ('EM1', 1)},
                                                          {'object_type': 'EQU',
                                                           'indicators': ind2,
                                                           'child_nodes': [],
                                                           'key': ('EM2', 0)}],
                                          'key': ('SY1', 1)},
                                         {'object_type': 'EQU',
                                          'indicators': ind2,
                                          'child_nodes': [],
                                          'key': ('EM2', 0)}]}
    return select_dictionary


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
    actual_components, equipment_ids, system_ids = System._traverse_components(input, 0, [], [])
    assert actual_components == systemcomponents_global
    assert equipment_ids == ['EM2-3id', 'EM1-11id', 'EM1-12id', 'EM2-13id', 'EM1-21id', 'EM1-22id', 'EM2-23id']
    assert system_ids == ['SY1-1id', 'SY1-2id']


def test_update_components(make_equipment_set, make_indicator_set, component_tree):
    system = System({'systemId': 'SY0id', 'internalId': 'SY0', 'modelID': 'SY0'})
    system1 = System({'systemId': 'SY1-1id', 'internalId': 'SY1-1', 'modelID': 'SY1'})
    system2 = System({'systemId': 'SY1-2id', 'internalId': 'SY1-2', 'modelID': 'SY1'})
    equi = make_equipment_set(equipmentId=['EM1-11id', 'EM1-12id', 'EM2-13id', 'EM1-21id', 'EM1-22id', 'EM2-23id',
                                           'EM2-3id'],
                              internalId=['EM1-11', 'EM1-12', 'EM2-13', 'EM1-21', 'EM1-22', 'EM2-23', 'EM2-3'],
                              modelId=['EM1', 'EM1', 'EM2', 'EM1', 'EM1', 'EM2', 'EM2'])
    ind1 = make_indicator_set(propertyId=['1', '2'])
    ind2 = make_indicator_set(propertyId=['3', '4'])
    system._System__hierarchy = {}
    system._System__hierarchy['component_tree'] = systemcomponents_global
    system._System__hierarchy['systems'] = SystemSet([system, system1, system2])
    system._System__hierarchy['equipment'] = equi
    system._System__hierarchy['indicators'] = {'EM1-11id': ind1, 'EM1-12id': ind1, 'EM2-13id': ind2,
                                               'EM1-21id': ind1, 'EM1-22id': ind1, 'EM2-23id': ind2, 'EM2-3id': ind2}
    system._update_components(system._System__hierarchy['component_tree'])
    assert system._System__hierarchy['component_tree'] == component_tree


def test_create_selection_dictionary(selection_dictionary, component_tree):
    actual_selection_dictionary = System._create_selection_dictionary(component_tree)
    assert actual_selection_dictionary == selection_dictionary


def test_get_leading_equipment(component_tree):

    def del_equis(component):
        # convert pieces of equipment into systems to create a tree with systems only
        if component['object_type'] == 'EQU':
            component['object_type'] = 'SYS'
        if 'child_nodes' in component.keys():
            for child in component['child_nodes']:
                del_equis(component['child_nodes'][child])

    system = System({'systemId': 'SY0id', 'internalId': 'SY0', 'modelID': 'SY0'})
    system._hierarchy = {}
    system._hierarchy['component_tree'] = component_tree
    # test 1: default behavior
    lead_equi = system.get_leading_equipment([])
    assert lead_equi == 'EM2-3id'
    # test 2: path given
    lead_equi = system.get_leading_equipment([('SY1', 1), ('EM1', 1)])
    assert lead_equi == 'EM1-22id'
    # test 3: no equipment in component tree
    del_equis(system._hierarchy['component_tree'])
    lead_equi = system.get_leading_equipment([])
    assert lead_equi == 0


def test_systemset_get_leading_equipment(make_indicator_set):
    s1 = System({'systemId': '1', 'internalId': 'SY1'})
    s2 = System({'systemId': '2', 'internalId': 'SY2'})
    s3 = System({'systemId': '3', 'internalId': 'SY3'})
    ind1 = make_indicator_set(propertyId=['1', '2'])
    ind2 = make_indicator_set(propertyId=['3', '4'])
    system_set = SystemSet([s1, s2, s3])
    s1._hierarchy = {}
    s1._hierarchy['component_tree'] = {'id': '1',
                                       'name': 'SY0-1',
                                       'order': None,
                                       'object_type': 'SYS',
                                       'child_nodes': {('SY1', 0):
                                                       {'id': '2262176B8E5F440CAEA8D2C39BC1A42C',
                                                        'name': 'SY1-1-1',
                                                        'order': '1',
                                                        'object_type': 'SYS',
                                                        'child_nodes': {('EM1', 0):
                                                                        {'id': 'DBB7885268EB41E3BF157AB890CCA1EF',
                                                                         'name': 'EM1-1-11',
                                                                         'order': '1',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM1', 1):
                                                                        {'id': '042F55EF70BE49538BB6DA3F32B8738C',
                                                                         'name': 'EM1-1-12',
                                                                         'order': '2',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM2', 0):
                                                                        {'id': 'A1ADCEA69C95454DA9FE19863804A0D6',
                                                                         'name': 'EM2-1-13',
                                                                         'order': '3',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind2,
                                                                         'child_nodes': {}}}},
                                                       ('SY1', 1):
                                                       {'id': '7788327C06844D24943AA59E2E14BB04',
                                                        'name': 'SY1-2',
                                                        'order': '2',
                                                        'object_type': 'SYS',
                                                        'child_nodes': {('EM1', 0):
                                                                        {'id': 'F988369A34404644A8DC470220FBBE34',
                                                                         'name': 'EM1-1-21',
                                                                         'order': '1',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM1', 1):
                                                                        {'id': '8C3114ACDF854084B50EB19D61C0FC9F',
                                                                         'name': 'EM1-1-22',
                                                                         'order': '2',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM2', 0):
                                                                        {'id': '4B8FB57B3F684F838F82BDDDB377AC76',
                                                                         'name': 'EM2-1-23',
                                                                         'order': '3',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind2,
                                                                         'child_nodes': {}}}},
                                                       ('EM2', 0):
                                                       {'id': '0E779D3EA3C54F379AC89A7C539EDCFE',
                                                        'name': 'EM2-1-3',
                                                        'order': '3',
                                                        'object_type': 'EQU',
                                                        'indicators': ind2,
                                                        'child_nodes': {}}}}
    s2._hierarchy = {}
    s2._hierarchy['component_tree'] = {'id': '2',
                                       'name': 'SY0-2',
                                       'order': None,
                                       'object_type': 'SYS',
                                       'child_nodes': {('SY1', 0):
                                                       {'id': '486F8199A82D4582B4718912A3A72037',
                                                        'name': 'SY1-2-1',
                                                        'order': '1',
                                                        'object_type': 'SYS',
                                                        'child_nodes': {('EM1', 0):
                                                                        {'id': 'E4790550A91A4F2EAE1055E16FD9BE34',
                                                                         'name': 'EM1-2-11',
                                                                         'order': '1',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM1', 1):
                                                                        {'id': 'C91000E01AB845E08E0CDAFF0CD84621',
                                                                         'name': 'EM1-2-12', 'order': '2',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}}}},
                                                       ('SY1', 1):
                                                       {'id': '76BD5F44CDE646E9B087574CEE9AF310',
                                                        'name': 'SY1-2-2',
                                                        'order': '2',
                                                        'object_type': 'SYS',
                                                        'child_nodes': {('EM1', 0):
                                                                        {'id': '0998250AA7AC45F0A878DB0E289FC5C1',
                                                                         'name': 'EM1-2-21',
                                                                         'order': '1',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM2', 0):
                                                                        {'id': 'E95A968289B6467CAF22DB3089F88616',
                                                                         'name': 'EM2-2-23',
                                                                         'order': '2',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind2,
                                                                         'child_nodes': {}}}}}}
    s3._hierarchy = {}
    s3._hierarchy['component_tree'] = {'id': '3',
                                       'name': 'SY0-3',
                                       'order': None,
                                       'object_type': 'SYS',
                                       'child_nodes': {('SY1', 0):
                                                       {'id': 'C0C88AB553F74980BEF53ECBB4635E4C',
                                                        'name': 'SY1-3-1',
                                                        'order': '1',
                                                        'object_type': 'SYS',
                                                        'child_nodes': {('EM1', 0):
                                                                        {'id': '0C6F06AAB482402D905F678E74E7053E',
                                                                         'name': 'EM1-3-11',
                                                                         'order': '1',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM1', 1):
                                                                        {'id': '4C29728F4D2E400B8D22145271379759',
                                                                         'name': 'EM1-3-12',
                                                                         'order': '2',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM2', 0):
                                                                        {'id': 'CDED4A4CC20C4A8A8A257540B0CAC794',
                                                                         'name': 'EM2-3-13',
                                                                         'order': '3',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind2,
                                                                         'child_nodes': {}}}},
                                                       ('EM2', 0):
                                                       {'id': 'A5E0E42A344F422C8663206E61848FBF',
                                                        'name': 'EM2-3-3',
                                                        'order': '2', 'object_type': 'EQU',
                                                        'indicators': ind2,
                                                        'child_nodes': {}}}}
    # without path
    result_df = system_set.get_leading_equipment()
    result = result_df.to_dict(orient='split')
    assert result['columns'] == ['equipment_id', 'system_id']
    assert len(result['data']) == 3
    assert ['0E779D3EA3C54F379AC89A7C539EDCFE', '1'] in result['data']
    assert ['E4790550A91A4F2EAE1055E16FD9BE34', '2'] in result['data']
    assert ['A5E0E42A344F422C8663206E61848FBF', '3'] in result['data']

    # with path
    path = [('SY1', 0), ('EM1', 1)]
    result_df = system_set.get_leading_equipment(path=path)
    result = result_df.to_dict(orient='split')
    assert result['columns'] == ['equipment_id', 'system_id']
    assert len(result['data']) == 3
    assert ['042F55EF70BE49538BB6DA3F32B8738C', '1'] in result['data']
    assert ['C91000E01AB845E08E0CDAFF0CD84621', '2'] in result['data']
    assert ['4C29728F4D2E400B8D22145271379759', '3'] in result['data']


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
    SystemSet._fill_nones(child_nodes, indicator_list, none_positions, 0)
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
    # expected results
    expected_indicators = [('DBB7885268EB41E3BF157AB890CCA1EF', ind1[0]), ('DBB7885268EB41E3BF157AB890CCA1EF', ind1[1]),
                           None, None,
                           ('A1ADCEA69C95454DA9FE19863804A0D6', ind3[0]), ('A1ADCEA69C95454DA9FE19863804A0D6', ind3[1])]
    indicator_list = []
    none_positions = set()
    SystemSet._map_comp_info(selec_nodes, system_nodes, indicator_list, none_positions, {}, 0)
    assert indicator_list == expected_indicators
    assert none_positions == {2, 3}


def test_map_component_information(make_indicator_set, selection_dictionary):
    s1 = System({'systemId': '1', 'internalId': 'SY1'})
    s2 = System({'systemId': '2', 'internalId': 'SY2'})
    s3 = System({'systemId': '3', 'internalId': 'SY3'})
    ind1 = make_indicator_set(propertyId=['1', '2'])
    ind2 = make_indicator_set(propertyId=['3', '4'])
    system_set = SystemSet([s1, s2, s3])
    s1._hierarchy = {}
    s1._hierarchy['component_tree'] = {'id': '1',
                                       'name': 'SY0-1',
                                       'order': None,
                                       'object_type': 'SYS',
                                       'child_nodes': {('SY1', 0):
                                                       {'id': '2262176B8E5F440CAEA8D2C39BC1A42C',
                                                        'name': 'SY1-1-1',
                                                        'order': '1',
                                                        'object_type': 'SYS',
                                                        'child_nodes': {('EM1', 0):
                                                                        {'id': 'DBB7885268EB41E3BF157AB890CCA1EF',
                                                                         'name': 'EM1-1-11',
                                                                         'order': '1',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM1', 1):
                                                                        {'id': '042F55EF70BE49538BB6DA3F32B8738C',
                                                                         'name': 'EM1-1-12',
                                                                         'order': '2',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM2', 0):
                                                                        {'id': 'A1ADCEA69C95454DA9FE19863804A0D6',
                                                                         'name': 'EM2-1-13',
                                                                         'order': '3',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind2,
                                                                         'child_nodes': {}}}},
                                                       ('SY1', 1):
                                                       {'id': '7788327C06844D24943AA59E2E14BB04',
                                                        'name': 'SY1-2',
                                                        'order': '2',
                                                        'object_type': 'SYS',
                                                        'child_nodes': {('EM1', 0):
                                                                        {'id': 'F988369A34404644A8DC470220FBBE34',
                                                                         'name': 'EM1-1-21',
                                                                         'order': '1',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM1', 1):
                                                                        {'id': '8C3114ACDF854084B50EB19D61C0FC9F',
                                                                         'name': 'EM1-1-22',
                                                                         'order': '2',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM2', 0):
                                                                        {'id': '4B8FB57B3F684F838F82BDDDB377AC76',
                                                                         'name': 'EM2-1-23',
                                                                         'order': '3',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind2,
                                                                         'child_nodes': {}}}},
                                                       ('EM2', 0):
                                                       {'id': '0E779D3EA3C54F379AC89A7C539EDCFE',
                                                        'name': 'EM2-1-3',
                                                        'order': '3',
                                                        'object_type': 'EQU',
                                                        'indicators': ind2,
                                                        'child_nodes': {}}}}
    s2._hierarchy = {}
    s2._hierarchy['component_tree'] = {'id': '2',
                                       'name': 'SY0-2',
                                       'order': None,
                                       'object_type': 'SYS',
                                       'child_nodes': {('SY1', 0):
                                                       {'id': '486F8199A82D4582B4718912A3A72037',
                                                        'name': 'SY1-2-1',
                                                        'order': '1',
                                                        'object_type': 'SYS',
                                                        'child_nodes': {('EM1', 0):
                                                                        {'id': 'E4790550A91A4F2EAE1055E16FD9BE34',
                                                                         'name': 'EM1-2-11',
                                                                         'order': '1',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM1', 1):
                                                                        {'id': 'C91000E01AB845E08E0CDAFF0CD84621',
                                                                         'name': 'EM1-2-12', 'order': '2',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}}}},
                                                       ('SY1', 1):
                                                       {'id': '76BD5F44CDE646E9B087574CEE9AF310',
                                                        'name': 'SY1-2-2',
                                                        'order': '2',
                                                        'object_type': 'SYS',
                                                        'child_nodes': {('EM1', 0):
                                                                        {'id': '0998250AA7AC45F0A878DB0E289FC5C1',
                                                                         'name': 'EM1-2-21',
                                                                         'order': '1',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM2', 0):
                                                                        {'id': 'E95A968289B6467CAF22DB3089F88616',
                                                                         'name': 'EM2-2-23',
                                                                         'order': '2',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind2,
                                                                         'child_nodes': {}}}}}}
    s3._hierarchy = {}
    s3._hierarchy['component_tree'] = {'id': '3',
                                       'name': 'SY0-3',
                                       'order': None,
                                       'object_type': 'SYS',
                                       'child_nodes': {('SY1', 0):
                                                       {'id': 'C0C88AB553F74980BEF53ECBB4635E4C',
                                                        'name': 'SY1-3-1',
                                                        'order': '1',
                                                        'object_type': 'SYS',
                                                        'child_nodes': {('EM1', 0):
                                                                        {'id': '0C6F06AAB482402D905F678E74E7053E',
                                                                         'name': 'EM1-3-11',
                                                                         'order': '1',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM1', 1):
                                                                        {'id': '4C29728F4D2E400B8D22145271379759',
                                                                         'name': 'EM1-3-12',
                                                                         'order': '2',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind1,
                                                                         'child_nodes': {}},
                                                                        ('EM2', 0):
                                                                        {'id': 'CDED4A4CC20C4A8A8A257540B0CAC794',
                                                                         'name': 'EM2-3-13',
                                                                         'order': '3',
                                                                         'object_type': 'EQU',
                                                                         'indicators': ind2,
                                                                         'child_nodes': {}}}},
                                                       ('EM2', 0):
                                                       {'id': 'A5E0E42A344F422C8663206E61848FBF',
                                                        'name': 'EM2-3-3',
                                                        'order': '2', 'object_type': 'EQU',
                                                        'indicators': ind2,
                                                        'child_nodes': {}}}}
    # expected result
    exp_sys_inds = {'2': [('E4790550A91A4F2EAE1055E16FD9BE34', ind1[0]),
                    ('E4790550A91A4F2EAE1055E16FD9BE34', ind1[1]),
                    ('C91000E01AB845E08E0CDAFF0CD84621', ind1[0]),
                    ('C91000E01AB845E08E0CDAFF0CD84621', ind1[1]),
                    None, None,
                    ('0998250AA7AC45F0A878DB0E289FC5C1', ind1[0]),
                    ('0998250AA7AC45F0A878DB0E289FC5C1', ind1[1]),
                    None, None,
                    ('E95A968289B6467CAF22DB3089F88616', ind2[0]),
                    ('E95A968289B6467CAF22DB3089F88616', ind2[1]),
                    None, None],
                    '1': [('DBB7885268EB41E3BF157AB890CCA1EF', ind1[0]),
                          ('DBB7885268EB41E3BF157AB890CCA1EF', ind1[1]),
                          ('042F55EF70BE49538BB6DA3F32B8738C', ind1[0]),
                          ('042F55EF70BE49538BB6DA3F32B8738C', ind1[1]),
                          ('A1ADCEA69C95454DA9FE19863804A0D6', ind2[0]),
                          ('A1ADCEA69C95454DA9FE19863804A0D6', ind2[1]),
                          ('F988369A34404644A8DC470220FBBE34', ind1[0]),
                          ('F988369A34404644A8DC470220FBBE34', ind1[1]),
                          ('8C3114ACDF854084B50EB19D61C0FC9F', ind1[0]),
                          ('8C3114ACDF854084B50EB19D61C0FC9F', ind1[1]),
                          ('4B8FB57B3F684F838F82BDDDB377AC76', ind2[0]),
                          ('4B8FB57B3F684F838F82BDDDB377AC76', ind2[1]),
                          ('0E779D3EA3C54F379AC89A7C539EDCFE', ind2[0]),
                          ('0E779D3EA3C54F379AC89A7C539EDCFE', ind2[1])],
                    '3': [('0C6F06AAB482402D905F678E74E7053E', ind1[0]),
                          ('0C6F06AAB482402D905F678E74E7053E', ind1[1]),
                          ('4C29728F4D2E400B8D22145271379759', ind1[0]),
                          ('4C29728F4D2E400B8D22145271379759', ind1[1]),
                          ('CDED4A4CC20C4A8A8A257540B0CAC794', ind2[0]),
                          ('CDED4A4CC20C4A8A8A257540B0CAC794', ind2[1]),
                          None, None, None, None, None, None,
                          ('A5E0E42A344F422C8663206E61848FBF', ind2[0]),
                          ('A5E0E42A344F422C8663206E61848FBF', ind2[1])]}
    exp_equipment = {'1': {'DBB7885268EB41E3BF157AB890CCA1EF': 0,
                           '042F55EF70BE49538BB6DA3F32B8738C': 1,
                           'A1ADCEA69C95454DA9FE19863804A0D6': 2,
                           'F988369A34404644A8DC470220FBBE34': 3,
                           '8C3114ACDF854084B50EB19D61C0FC9F': 4,
                           '4B8FB57B3F684F838F82BDDDB377AC76': 5,
                           '0E779D3EA3C54F379AC89A7C539EDCFE': 6},
                     '2': {'E4790550A91A4F2EAE1055E16FD9BE34': 0,
                           'C91000E01AB845E08E0CDAFF0CD84621': 1,
                           '0998250AA7AC45F0A878DB0E289FC5C1': 3,
                           'E95A968289B6467CAF22DB3089F88616': 5},
                     '3': {'0C6F06AAB482402D905F678E74E7053E': 0,
                           '4C29728F4D2E400B8D22145271379759': 1,
                           'CDED4A4CC20C4A8A8A257540B0CAC794': 2,
                           'A5E0E42A344F422C8663206E61848FBF': 6}}
    act_sys_inds, act_equipment = system_set._map_component_information(selection_dictionary)
    assert act_sys_inds == exp_sys_inds
    assert act_equipment == exp_equipment
    act_sys_inds, act_equipment = system_set._map_component_information({})
    exp_equipment = {'1': {'DBB7885268EB41E3BF157AB890CCA1EF': 0, '042F55EF70BE49538BB6DA3F32B8738C': 1},
                     '2': {'E4790550A91A4F2EAE1055E16FD9BE34': 0, 'C91000E01AB845E08E0CDAFF0CD84621': 1},
                     '3': {'0C6F06AAB482402D905F678E74E7053E': 0, '4C29728F4D2E400B8D22145271379759': 1}}
    assert act_equipment == exp_equipment


def test_create_analysis_table(make_indicator_set, make_equipment_set):
    indicator_set = make_indicator_set(propertyId=('0', '1', '2'))
    indicator_set0 = make_indicator_set(propertyId=('0'))
    indicator_set1 = make_indicator_set(propertyId=('1'))
    indicator_set2 = make_indicator_set(propertyId=('2'))
    equipment_set = make_equipment_set(equipmentId=('equi1', 'equi2', 'equi3'),
                                       modelId=('model', 'model', 'model'))
    system = System({'systemId': 'SY0id', 'internalId': 'SY0', 'modelID': 'SY0'})
    system._hierarchy = {}
    system._hierarchy['component_tree'] = {'id': '1',
                                           'name': 'SY0',
                                           'order': None,
                                           'object_type': 'SYS',
                                           'child_nodes': {('EQU', 0):
                                                           {'id': 'equi1',
                                                            'name': 'equi1',
                                                            'order': '1',
                                                            'object_type': 'EQU',
                                                            'indicators': indicator_set0,
                                                            'child_nodes': {}},
                                                           ('EQU', 1):
                                                           {'id': 'equi2',
                                                            'name': 'equi2',
                                                            'order': '2',
                                                            'object_type': 'EQU',
                                                            'indicators': indicator_set1,
                                                            'child_nodes': {}},
                                                           ('EQU', 2):
                                                           {'id': 'equi3',
                                                            'name': 'equi3',
                                                            'order': '3',
                                                            'object_type': 'EQU',
                                                            'indicators': indicator_set2,
                                                            'child_nodes': {}}}}
    system._hierarchy['equipment'] = equipment_set
    system_set = SystemSet([system])
    dataset = make_dataset(indicator_set, equipment_set)
    analysis_table = create_analysis_table(system_set, dataset)
    assert len(analysis_table.as_df()) == 300


def test_expected_public_attributes_are_present():
    expected_attributes = ['name', 'model_name', 'status_text', 'short_description',
                           'class_name', 'id', 'model_id', 'template_id']

    fieldmap_public_attributes = [
        field.our_name for field in System._field_map.values() if field.is_exposed
    ]

    assert expected_attributes == fieldmap_public_attributes
