from unittest.mock import PropertyMock, patch

import pytest

from sailor.assetcentral.equipment import Equipment
from sailor.assetcentral.utils import AssetcentralEntity, ResultSet, _unify_filters, parse_filter_parameters, \
    apply_filters_post_request


class TestAssetcentralEntity:

    def test_magic_eq_true(self):
        entity1 = AssetcentralEntity({})
        entity1.id = '1'
        entity2 = AssetcentralEntity({})
        entity2.id = '1'
        assert entity1 == entity2

    def test_magic_eq_false_id(self):
        entity1 = AssetcentralEntity({})
        entity1.id = '1'
        entity2 = AssetcentralEntity({})
        entity2.id = '2'
        assert entity1 != entity2

    @patch('sailor.assetcentral.equipment.Equipment.id', new_callable=PropertyMock, return_value='1')
    def test_magic_eq_false_class(self, id_mock):
        entity1 = AssetcentralEntity({})
        entity1.id = '1'
        entity2 = Equipment({})
        assert entity1 != entity2


class TestResultSet:

    @patch('sailor.assetcentral.utils.p9')
    def test_integration_with_subclasses(self, mock_p9):
        for cls in ResultSet.__subclasses__():
            result_set_obj = cls([])
            result_set_obj.as_df()
            result_set_obj.plot_distribution()

    def test_magic_eq_type_not_equal(self):
        rs1 = ResultSet([1, 2, 3])
        rs2 = (1, 2, 3)
        assert rs1 != rs2

    @pytest.mark.parametrize('testdescription,list1,list2,expected_result', [
        ('Order not equal', [1, 2, 3], [2, 3, 1], False),
        ('Different content', [1, 2, 3], [1, 2, 4], False),
        ('Different size', [1, 2, 3, 4], [1, 2, 3], False),
        ('Equal content and order', [1, 2, 3], [1, 2, 3], True),
        ('Two empty sets are equal', [], [], True),
    ])
    def test_magic_eq_content(self, list1, list2, expected_result, testdescription):
        rs1 = ResultSet(list1)
        rs2 = ResultSet(list2)
        if expected_result:
            assert rs1 == rs2
        else:
            assert rs1 != rs2


@pytest.mark.filterwarnings('ignore:Following parameters are not in our terminology')
class TestQueryParsers:

    @pytest.mark.parametrize('test_description,value,expected_values', [
        ('single string', 'value', "'value'"),
        ('list of strings', ['value1', 'value2'], ["'value1'", "'value2'"]),
        ('single integer', 7, '7'),
        ('list of integers', [3, 6, 1], ['3', '6', '1']),
        ('single float', 3.14, '3.14'),
        ('list of floats', [3.4, 4.5], ['3.4', '4.5']),
        ('mixed type list', ['value 1', 18., 'value2', 5], ["'value 1'", '18.0', "'value2'", '5'])
    ])
    def test_unify_filters_only_equality_different_types(self, value, expected_values, test_description):
        expected_filters = [('filtered_term', 'eq', expected_values)]

        filters = _unify_filters({'filtered_term': value}, None, None)

        assert filters == expected_filters

    @pytest.mark.parametrize('test_description,equality_value,extended_value', [
        ('single string single quote', 'value', "'value'"),
        ('single string double quote', 'value', '"value"'),
        ('single integer', 7, '7'),
        ('single float', 3.14, '3.14'),
    ])
    def test_extended_equals_equality_different_types(self, equality_value, extended_value, test_description):

        equality_filters = _unify_filters({'filtered_term': equality_value}, None, None)
        extended_filters = _unify_filters(None, ['filtered_term == {}'.format(extended_value)], None)

        assert equality_filters == extended_filters

    @pytest.mark.parametrize('filter,odata_expression', [
        ('==', 'eq'), ('!=', 'ne'), ('<=', 'le'), ('>=', 'ge'), ('>', 'gt'), ('<', 'lt')
    ])
    def test_unify_filters_extended_filter_types(self, filter, odata_expression):
        expected_filters = [('filtered_term', odata_expression, "'value'")]

        filters = _unify_filters(None, ['filtered_term {} "value"'.format(filter)], None)

        assert filters == expected_filters

    @pytest.mark.parametrize('filter_term', [
        'a == b', 'a==b', 'a ==b', 'a    ==   b'
    ])
    def test_unify_filters_different_extended_formatting_unquoted(self, filter_term):
        filters = _unify_filters(None, [filter_term], None)

        assert filters == [('a', 'eq', 'b')]

    @pytest.mark.parametrize('filter_term', [
        'a == "b"', 'a=="b"', 'a =="b"', 'a    ==   "b"', "a == 'b'", "a=='b'", "a =='b'", "a    ==   'b'"
    ])
    def test_unify_filters_different_extended_formatting_quoted(self, filter_term):
        filters = _unify_filters(None, [filter_term], None)

        assert filters == [('a', 'eq', "'b'")]

    @pytest.mark.parametrize('testdescription,equality_filters,expected_unbreakable,expected_breakable', [
        ('no args returns empty', {}, [], []),
        ('single valued filters are unbreakable',
            {'location': 'Paris', 'name': 'test'}, ["location eq 'Paris'", "name eq 'test'"], []),
        ('multi valued filters are breakable',
            {'location': ['Paris', 'London']}, [], [["location eq 'Paris'", "location eq 'London'"]]),
        ('single and multi are correctly broken',
            {'location': ['Paris', 'London'], 'name': 'test'}, ["name eq 'test'"],
                                                               [["location eq 'Paris'", "location eq 'London'"]]),
    ])
    def test_parse_filter_parameters_equality_filters(self, equality_filters, expected_unbreakable, expected_breakable,
                                                      testdescription):
        actual_unbreakable, actual_breakable = parse_filter_parameters(equality_filters=equality_filters)
        assert actual_unbreakable == expected_unbreakable
        assert actual_breakable == expected_breakable

    @pytest.mark.parametrize('testdescription,extended_filters,expected_unbreakable', [
        ('no args returns empty', [], []),
        ('single param',
            ["startDate > '2020-01-01'"],
            ["startDate gt '2020-01-01'"]),
        ('multiple params',
            ["startDate > '2020-01-01'", "endDate < '2020-02-01'"],
            ["startDate gt '2020-01-01'", "endDate lt '2020-02-01'"]),
    ])
    def test_parse_filter_parameters_extended_filters_are_unbreakable(self, extended_filters, expected_unbreakable,
                                                                      testdescription):
        actual_unbreakable, actual_breakable = parse_filter_parameters(extended_filters=extended_filters)
        assert actual_unbreakable == expected_unbreakable
        assert actual_breakable == []

    def test_parse_filter_parameters_with_combined_filters(self):
        equality_filters = {'location': ['Paris', 'London']}
        extended_filters = ["startDate > '2020-01-01'", "endDate < '2020-02-01'"]

        actual_unbreakable, actual_breakable = \
            parse_filter_parameters(equality_filters=equality_filters, extended_filters=extended_filters)

        assert actual_unbreakable == ["startDate gt '2020-01-01'", "endDate lt '2020-02-01'"]
        assert actual_breakable == [["location eq 'Paris'", "location eq 'London'"]]

    def test_parse_filter_parameters_with_property_mapping(self):
        equality_filters = {'location_name': ['Paris', 'London'], 'serial_number': 1234}
        extended_filters = ["start_date > '2020-01-01'"]
        property_mapping = {'location_name': ('location', None, None, None),
                            'serial_number': ('serialNumber', None, None, None),
                            'start_date': ('startDate', None, None, None)}

        actual_unbreakable, actual_breakable = \
            parse_filter_parameters(equality_filters, extended_filters, property_mapping)

        assert actual_unbreakable == ["serialNumber eq 1234", "startDate gt '2020-01-01'"]
        assert actual_breakable == [["location eq 'Paris'", "location eq 'London'"]]


@pytest.mark.parametrize('testdescription,equality_filters,extended_filters,expected_ids', [
    ('without filters as None', None, None, ['indicator_id1', 'indicator_id2', 'indicator_id3']),
    ('without filters as dict and list', {}, [], ['indicator_id1', 'indicator_id2', 'indicator_id3']),
    ('equality filters', dict(type='yellow', dimension='zero'), None, ['indicator_id1']),
    ('equality filter list', dict(type=['yellow', 'brown']), None, ['indicator_id1', 'indicator_id2', 'indicator_id3']),
    ('extended filters', None, ['categoryID > aa'], ['indicator_id3']),
    ('both filters', dict(type='brown'), ['categoryID > a'], ['indicator_id3']),
    ('both filters yields empty result', dict(type='yellow'), ['categoryID > aa'], []),
])
@pytest.mark.filterwarnings('ignore:Following parameters are not in our terminology')
def test_apply_filters_post_request_filtering(equality_filters, extended_filters, expected_ids, testdescription):
    data = [{'id': 'indicator_id1', 'type': 'yellow', 'dimension': 'zero', 'categoryID': 'aa'},
            {'id': 'indicator_id2', 'type': 'yellow', 'dimension': 'three', 'categoryID': 'aa'},
            {'id': 'indicator_id3', 'type': 'brown', 'dimension': 'three', 'categoryID': 'aaaa'}]

    actual = apply_filters_post_request(data, equality_filters, extended_filters, property_mapping=None)

    assert [item['id'] for item in actual] == expected_ids


def test_apply_filters_post_request_property_mapping():
    data = [{'propertyId': 'indicator_id1', 'indicatorType': 'yellow', 'categoryID': 'aa'},
            {'propertyId': 'indicator_id2', 'indicatorType': 'yellow', 'categoryID': 'aa'},
            {'propertyId': 'indicator_id3', 'indicatorType': 'brown', 'categoryID': 'aaaa'}]
    property_mapping = {'type': ('indicatorType', None, None, None),
                        'template_id': ('categoryID', None, None, None)}
    equality_filters = dict(type='yellow')
    extended_filters = ['template_id > a']
    expected_result = [{'propertyId': 'indicator_id1', 'indicatorType': 'yellow', 'categoryID': 'aa'},
                       {'propertyId': 'indicator_id2', 'indicatorType': 'yellow', 'categoryID': 'aa'}]

    actual = apply_filters_post_request(data, equality_filters, extended_filters, property_mapping)

    assert actual == expected_result
