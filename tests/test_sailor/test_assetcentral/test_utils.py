from typing import Iterable
from unittest.mock import PropertyMock, patch, Mock

import pytest

from sailor.assetcentral.equipment import Equipment
from sailor.assetcentral.utils import AssetcentralEntity, ResultSet, _unify_filters, _parse_filter_parameters, \
    _apply_filters_post_request, _compose_queries, _fetch_data
from sailor.utils.oauth_wrapper import OAuthFlow


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
    @pytest.mark.parametrize('cls', ResultSet.__subclasses__())
    def test_integration_with_subclasses(self, mock_p9, cls):
        result_set_obj = cls([])
        result_set_obj.as_df()
        result_set_obj.plot_distribution()

    @pytest.mark.parametrize('cls', ResultSet.__subclasses__())
    def test_resultset_method_defaults(self, cls):
        element_properties = cls._element_type.get_property_mapping()
        assert cls._method_defaults['plot_distribution']['by'] in element_properties

    def test_magic_eq_type_not_equal(self):
        rs1 = ResultSet([1, 2, 3])
        rs2 = (1, 2, 3)
        assert rs1 != rs2

    @pytest.mark.parametrize('testdescription,list1,list2,expected_result', [
        ('Order does not matter', [1, 2, 3], [2, 3, 1], True),
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

    def test_unify_filters_property_mapping_kwargs_key_field(self):
        filters = _unify_filters({'my_term': 'some_value'}, None, {'my_term': ['their_term']})
        assert filters[0][0] == 'their_term'

    def test_unify_filters_property_mapping_extended_key_field(self):
        filters = _unify_filters(None, ['my_term == "foo"'], {'my_term': ['their_term']})
        assert filters[0][0] == 'their_term'

    def test_unify_filters_property_mapping_extended_value_field(self):
        filters = _unify_filters(None, ['some_field == my_term'], {'my_term': ['their_term']})
        assert filters[0][2] == 'their_term'

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
        actual_unbreakable, actual_breakable = _parse_filter_parameters(equality_filters=equality_filters)
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
        actual_unbreakable, actual_breakable = _parse_filter_parameters(extended_filters=extended_filters)
        assert actual_unbreakable == expected_unbreakable
        assert actual_breakable == []

    def test_parse_filter_parameters_with_combined_filters(self):
        equality_filters = {'location': ['Paris', 'London']}
        extended_filters = ["startDate > '2020-01-01'", "endDate < '2020-02-01'"]

        actual_unbreakable, actual_breakable = \
            _parse_filter_parameters(equality_filters=equality_filters, extended_filters=extended_filters)

        assert actual_unbreakable == ["startDate gt '2020-01-01'", "endDate lt '2020-02-01'"]
        assert actual_breakable == [["location eq 'Paris'", "location eq 'London'"]]

    def test_parse_filter_parameters_with_property_mapping(self):
        equality_filters = {'location_name': ['Paris', 'London'], 'serial_number': 1234}
        extended_filters = ["start_date > '2020-01-01'"]
        property_mapping = {'location_name': ('location', None, None, None),
                            'serial_number': ('serialNumber', None, None, None),
                            'start_date': ('startDate', None, None, None)}

        actual_unbreakable, actual_breakable = \
            _parse_filter_parameters(equality_filters, extended_filters, property_mapping)

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

    actual = _apply_filters_post_request(data, equality_filters, extended_filters, property_mapping=None)

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

    actual = _apply_filters_post_request(data, equality_filters, extended_filters, property_mapping)

    assert actual == expected_result


class TestComposeQueries:
    @pytest.mark.parametrize('testdescription,unbreakable_filters,breakable_filters,expected', [
        ('empty input returns empty filters',
            [], [], []),
        ('unbreakable filters are combined with "and"',
            ["name eq 'test'", "location eq 'Paris'"], [],
            ["name eq 'test' and location eq 'Paris'"]),
        ('breakable filters are combined with "or"',
            [], [["location eq 'Paris'", "location eq 'London'"]],
            ["(location eq 'Paris' or location eq 'London')"]),
        ('multiple breakable filters are connected with "and"',
            [], [["testFac eq 'abcCorp'", "testFac eq '123pumps'"], ["location eq 'Paris'", "location eq 'London'"]],
            ["(testFac eq 'abcCorp' or testFac eq '123pumps') and (location eq 'Paris' or location eq 'London')"]),
        ('un- and breakable filters are connected with "and"',
            ["name eq 'test'"], [["location eq 'Paris'", "location eq 'London'"]],
            ["name eq 'test' and (location eq 'Paris' or location eq 'London')"])
    ])
    def test_regular_cases(self, unbreakable_filters, breakable_filters, expected, testdescription):
        actual = _compose_queries(unbreakable_filters, breakable_filters)
        assert actual == expected

    # the correctness of the test depends on what is configured as the max_filter_length in _compose_queries
    def test_too_many_filters_are_split_verify_split_start_end(self):
        unbreakable_filters = []
        breakable_filters = [[f"manufacturer eq '{'abcCorp' if i % 2 == 0 else '123pumps'}_{i}'" for i in range(100)],
                             ["location eq 'Paris'", "location eq 'London'"]]
        expected_start_of_1st_filter = "(location eq 'Paris' or location eq 'London') and (manufacturer eq 'abcCorp_0'"
        expected_start_of_2nd_filter = "(location eq 'Paris' or location eq 'London') and (manufacturer eq "
        expected_end_of_2nd_filter = "manufacturer eq '123pumps_99')"

        actual = _compose_queries(unbreakable_filters, breakable_filters)

        assert len(actual) == 2
        assert actual[0].startswith(expected_start_of_1st_filter)
        assert actual[1].startswith(expected_start_of_2nd_filter)
        assert actual[1].endswith(expected_end_of_2nd_filter)

    # the correctness of the test depends on what is configured as the max_filter_length in _compose_queries
    def test_too_many_filters_are_split_verify_split_borders(self):
        unbreakable_filters = []
        breakable_filters = [[f"manufacturer eq '{'abcCorp' if i % 2 == 0 else '123pumps'}_{i}'" for i in range(100)],
                             ["location eq 'Paris'", "location eq 'London'"]]
        expected_end_of_1st_filter = "manufacturer eq '123pumps_59')"
        expected_start_of_2nd_filter = "(location eq 'Paris' or location eq 'London') and (manufacturer eq 'abcCorp_60'"

        actual = _compose_queries(unbreakable_filters, breakable_filters)

        assert len(actual) == 2
        assert actual[0].endswith(expected_end_of_1st_filter)
        assert actual[1].startswith(expected_start_of_2nd_filter)

    # the correctness of the test depends on what is configured as the max_filter_length in _compose_queries
    def test_too_many_filters_are_split_all_filters_present(self):
        unbreakable_filters = ["name eq 'test'"]
        breakable_filters = [[f"manufacturer eq '{'abcCorp' if i % 2 == 0 else '123pumps'}_{i}'" for i in range(100)],
                             ["location eq 'Paris'", "location eq 'London'"]]

        actual = _compose_queries(unbreakable_filters, breakable_filters)

        big_filter_string = ''.join(actual)
        assert unbreakable_filters[0] in big_filter_string
        for sublist in breakable_filters:
            for item in sublist:
                assert item in big_filter_string


class TestFetchData:
    @patch('sailor.assetcentral.utils.OAuthFlow', return_value=Mock(OAuthFlow))
    @pytest.mark.filterwarnings('ignore::sailor.utils.utils.DataNotFoundWarning')
    @pytest.mark.parametrize('testdesc,unbreakable_filters,breakable_filters,remote_return', [
        ('no filters - single return', [], [], {'a': 'dict'}),
        ('filters - single return', ['a gt b'], [['c eq 1']], {'a': 'dict'}),
        ('no filters - list return', [], [], ['result']),
        ('filters - list return', ['a gt b'], [['c eq 1']], ['result']),
    ])
    def test_returns_iterable(self, auth_mock, unbreakable_filters, breakable_filters, remote_return, testdesc):
        auth_mock.return_value.fetch_endpoint_data.return_value = remote_return
        actual = _fetch_data('', unbreakable_filters, breakable_filters)
        assert not issubclass(actual.__class__, str)
        assert isinstance(actual, Iterable)

    @patch('sailor.assetcentral.utils.OAuthFlow', return_value=Mock(OAuthFlow))
    def test_no_filters_makes_remote_call_with_no_params(self, auth_mock):
        fetch_mock = auth_mock.return_value.fetch_endpoint_data
        fetch_mock.return_value = ['result']
        unbreakable_filters = []
        breakable_filters = []

        actual = _fetch_data('', unbreakable_filters, breakable_filters)

        fetch_mock.assert_called_once_with('', method='GET', parameters=None)
        assert actual == ['result']

    @patch('sailor.assetcentral.utils.OAuthFlow', return_value=Mock(OAuthFlow))
    def test_adds_filter_parameter_on_call(self, auth_mock):
        fetch_mock = auth_mock.return_value.fetch_endpoint_data
        unbreakable_filters = ["location eq 'Walldorf'"]
        breakable_filters = [["manufacturer eq 'abcCorp'"]]
        expected_parameters = {'$filter': "location eq 'Walldorf' and (manufacturer eq 'abcCorp')"}

        _fetch_data('', unbreakable_filters, breakable_filters)

        fetch_mock.assert_called_once_with("", method="GET", parameters=expected_parameters)

    @patch('sailor.assetcentral.utils.OAuthFlow', return_value=Mock(OAuthFlow))
    def test_multiple_calls_aggregated_result(self, auth_mock):
        unbreakable_filters = ["location eq 'Walldorf'"]
        # causes _compose_queries to generate two filter strings
        breakable_filters = [["manufacturer eq 'abcCorp'"] * 100]
        fetch_mock = auth_mock.return_value.fetch_endpoint_data
        fetch_mock.side_effect = [["result1-1", "result1-2"], ["result2-1"]]
        expected_result = ["result1-1", "result1-2", "result2-1"]

        actual = _fetch_data('', unbreakable_filters, breakable_filters)

        assert actual == expected_result
