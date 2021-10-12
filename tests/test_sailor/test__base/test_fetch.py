from typing import Iterable

import pytest

from sailor import _base
from sailor._base.fetch import (
    fetch_data, apply_filters_post_request, parse_filter_parameters, _unify_filters, _compose_queries,
    _strip_quote_marks)


@pytest.mark.filterwarnings('ignore:Following parameters are not in our terminology')
class TestQueryParsers:

    @pytest.mark.parametrize('test_description,value,expected_values', [
        ('single string', 'the value', "'the value'"),
        ('list of strings', ['the value1', 'value2'], ["'the value1'", "'value2'"]),
        ('null value', None, 'null'),
        ('single integer', 7, "'7'"),
        ('list of integers', [3, 6, 1], ["'3'", "'6'", "'1'"]),
        ('single float', 3.14, "'3.14'"),
        ('list of floats', [3.4, 4.5], ["'3.4'", "'4.5'"]),
        ('mixed type list', ['value 1', 18., 'value2', 5, None], ["'value 1'", "'18.0'", "'value2'", "'5'", 'null']),
    ])
    def test_unify_filters_only_equality_known_fields(self, value, expected_values, test_description):
        expected_filters = [('filtered_term', 'eq', expected_values)]
        field_map = {'filtered_term': _base.MasterDataField('filtered_term', 'filtered_term')}

        filters = _unify_filters({'filtered_term': value}, None, field_map)

        assert filters == expected_filters

    # values of unknown fields are never modified. the user must have it right
    @pytest.mark.parametrize('test_description,value,expected_values', [
        ('single value', 'the value', 'the value'),  # this includes the null value
        ('quoted value single-quote', "'the value'", "'the value'"),
        ('quoted value double-quote', '"value"', '"value"'),
        ('list of values', ['value1', 'value2'], ["value1", "value2"]),
        ('single integer', 7, "7"),
        ('list of integers', [3, 6, 1], ["3", "6", "1"]),
        ('single float', 3.14, "3.14"),
        ('list of floats', [3.4, 4.5], ["3.4", "4.5"]),
        ('mixed type list', ['null', 18., "'value2'", 5], ["null", "18.0", "'value2'", "5"]),
    ])
    def test_unify_filters_only_equality_unknown_fields(self, value, expected_values, test_description):
        expected_filters = [('filtered_term', 'eq', expected_values)]

        filters = _unify_filters({'filtered_term': value}, None, None)

        assert filters == expected_filters

    # values of known fields are put through the default QT => single quote everything with the exception of the 'null'
    @pytest.mark.parametrize('test_description,value,expected_value', [
        ('quoted value single-quote', "'the value'", "'the value'"),
        ('quoted value double-quote', '"the value"', "'the value'"),
        ('unquoted value', 'the value', "'the value'"),
        ('empty quotes', '""', "''"),
        ('empty quotes', "''", "''"),
        ('other string', "datetimeoffset'2020-01-01'", "'datetimeoffset'2020-01-01''"),  # nonsensical example
        ('null value', 'null', 'null'),
        ('single integer', 7, "'7'"),
        ('single float', 3.14, "'3.14'"),
    ])
    def test_unify_filters_only_extended_known_fields(self, value, expected_value, test_description):
        expected_filters = [('filtered_term', 'eq', expected_value)]
        field_map = {'filtered_term': _base.MasterDataField('filtered_term', 'filtered_term')}

        filters = _unify_filters(None, ['filtered_term == {}'.format(value)], field_map)

        assert filters == expected_filters

    @pytest.mark.parametrize('test_description,value,expected_value', [
        ('quoted value single-quote', "'the value'", "'the value'"),
        ('quoted value double-quote', '"the value"', '"the value"'),
        ('other string', "datetimeoffset'2020-01-01'", "datetimeoffset'2020-01-01'"),
        ('null value', 'null', 'null'),
        ('single integer', 7, '7'),
        ('single float', 3.14, '3.14'),
    ])
    def test_unify_filters_only_extended_unknown_fields(self, value, expected_value, test_description):
        expected_filters = [('filtered_term', 'eq', expected_value)]

        filters = _unify_filters(None, ['filtered_term == {}'.format(value)], None)

        assert filters == expected_filters

    @pytest.mark.parametrize('test_description,equality_value,extended_value', [
        ('quoted value single-quote', 'the value', "'the value'"),
        ('quoted value double-quote', 'the value', '"the value"'),
        ('unquoted value double-quote', 'the value', 'the value'),
        ('quoted empty value', '', "''"),
        ('quoted empty value', '', '""'),
        ('other string', "datetimeoffset'2020-01-01'", "datetimeoffset'2020-01-01'"),
        ('null value', None, 'null'),
        ('single integer', 7, '7'),
        ('single float', 3.14, '3.14'),
    ])
    def test_extended_equals_equality_different_types_known_fields(self, equality_value, extended_value,
                                                                   test_description):

        field_map = {'filtered_term': _base.MasterDataField('filtered_term', 'filtered_term')}
        equality_filters = _unify_filters({'filtered_term': equality_value}, None, field_map)
        extended_filters = _unify_filters(None, ['filtered_term == {}'.format(extended_value)], field_map)

        assert equality_filters == extended_filters

    @pytest.mark.parametrize('test_description,equality_value,extended_value', [
        ('quoted value single-quote', "'the value'", "'the value'"),
        ('quoted value double-quote', '"the value"', '"the value"'),
        ('other string', "datetimeoffset'2020-01-01'", "datetimeoffset'2020-01-01'"),
        ('null value', 'null', 'null'),
        ('single integer', 7, '7'),
        ('single float', 3.14, '3.14'),
    ])
    def test_extended_equals_equality_different_types_unknown_fields(self, equality_value, extended_value,
                                                                     test_description):
        equality_filters = _unify_filters({'filtered_term': equality_value}, None, None)
        extended_filters = _unify_filters(None, ['filtered_term == {}'.format(extended_value)], None)

        assert equality_filters == extended_filters

    @pytest.mark.parametrize('filter,odata_expression', [
        ('==', 'eq'), ('!=', 'ne'), ('<=', 'le'), ('>=', 'ge'), ('>', 'gt'), ('<', 'lt')
    ])
    def test_unify_filters_extended_filter_types_unknown_fields(self, filter, odata_expression):
        expected_filters = [('filtered_term', odata_expression, "value")]

        filters = _unify_filters(None, ['filtered_term {} value'.format(filter)], None)

        assert filters == expected_filters

    @pytest.mark.parametrize('filter_term', [
        'a == b', 'a==b', 'a ==b', 'a    ==   b'
    ])
    def test_unify_filters_different_extended_formatting_unquoted_known_fields(self, filter_term):
        filters = _unify_filters(None, [filter_term], {'a': _base.MasterDataField('a', 'A')})

        assert filters == [('A', 'eq', "'b'")]

    @pytest.mark.parametrize('filter_term', [
        'a == b', 'a==b', 'a ==b', 'a    ==   b'
    ])
    def test_unify_filters_different_extended_formatting_unquoted_unknown_fields(self, filter_term):
        filters = _unify_filters(None, [filter_term], None)

        assert filters == [('a', 'eq', 'b')]

    @pytest.mark.parametrize('filter_term', [
        "a == 'b'", "a=='b'", "a =='b'", "a    ==   'b'"
    ])
    def test_unify_filters_different_extended_formatting_single_quoted_unknown_field(self, filter_term):
        filters = _unify_filters(None, [filter_term], None)

        assert filters == [('a', 'eq', "'b'")]

    @pytest.mark.parametrize('filter_term', [
        'a == "b"', 'a=="b"', 'a =="b"', 'a    ==   "b"'
    ])
    def test_unify_filters_different_extended_formatting_double_quoted_unknown_field(self, filter_term):
        filters = _unify_filters(None, [filter_term], None)

        assert filters == [('a', 'eq', '"b"')]

    def test_unify_filters_property_mapping_kwargs_key_field(self):
        filters = _unify_filters({'my_term': 'some_value'}, None, {'my_term': _base.MasterDataField('my_term',
                                                                                                    'their_term')})
        assert filters[0][0] == 'their_term'

    def test_unify_filters_property_mapping_extended_key_field(self):
        filters = _unify_filters(None, ['my_term == "foo"'], {'my_term': _base.MasterDataField('my_term',
                                                                                               'their_term')})
        assert filters[0][0] == 'their_term'

    def test_unify_filters_property_mapping_value_is_a_known_field(self):
        filters = _unify_filters(None, ['some_field == other_field'],
                                 {'some_field': _base.MasterDataField('some_field', 'SomeField'),
                                  'other_field': _base.MasterDataField('other_field', 'OtherField')})
        assert filters == [('SomeField', 'eq', 'OtherField')]

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
    def test_parse_filter_parameters_equality_filters_known_fields(self, equality_filters, expected_unbreakable,
                                                                   expected_breakable, testdescription):
        field_map = {'location': _base.MasterDataField('location', 'location'),
                     'name': _base.MasterDataField('name', 'name')}
        actual_unbreakable, actual_breakable = parse_filter_parameters(equality_filters, None, field_map)
        assert actual_unbreakable == expected_unbreakable
        assert actual_breakable == expected_breakable

    @pytest.mark.parametrize('testdescription,equality_filters,expected_unbreakable,expected_breakable', [
        ('no args returns empty', {}, [], []),
        ('single valued filters are unbreakable',
            {'location': "'Paris'", 'name': "'test'"}, ["location eq 'Paris'", "name eq 'test'"], []),
        ('multi valued filters are breakable',
            {'location': ["'Paris'", "'London'"]}, [], [["location eq 'Paris'", "location eq 'London'"]]),
        ('single and multi are correctly broken',
            {'location': ["'Paris'", "'London'"], 'name': "'test'"}, ["name eq 'test'"], [
                ["location eq 'Paris'", "location eq 'London'"]]),
    ])
    def test_parse_filter_parameters_equality_filters_unknown_fields(self, equality_filters, expected_unbreakable,
                                                                     expected_breakable, testdescription):
        actual_unbreakable, actual_breakable = parse_filter_parameters(equality_filters, None, None)
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

    def test_parse_filter_parameters_with_combined_filters_unknown_fields(self):
        equality_filters = {'location': ["'Paris'", "'London'"]}
        extended_filters = ["startDate > '2020-01-01'", "endDate < '2020-02-01'"]

        actual_unbreakable, actual_breakable = \
            parse_filter_parameters(equality_filters=equality_filters, extended_filters=extended_filters)

        assert actual_unbreakable == ["startDate gt '2020-01-01'", "endDate lt '2020-02-01'"]
        assert actual_breakable == [["location eq 'Paris'", "location eq 'London'"]]

    def test_parse_filter_parameters_with_property_mapping(self):
        equality_filters = {'location_name': ['Paris', 'London'], 'serial_number': 1234}
        extended_filters = ["start_date > '2020-01-01'"]
        field_map = {'location_name': _base.MasterDataField('location_name', 'location'),
                     'serial_number': _base.MasterDataField('serial_number', 'serialNumber',
                                                            query_transformer=lambda x: str(x)),
                     'start_date': _base.MasterDataField('start_date', 'startDate')}

        actual_unbreakable, actual_breakable = \
            parse_filter_parameters(equality_filters, extended_filters, field_map)

        assert actual_unbreakable == ["serialNumber eq 1234", "startDate gt '2020-01-01'"]
        assert actual_breakable == [["location eq 'Paris'", "location eq 'London'"]]

    @pytest.mark.parametrize('testdescr,equality_filters,extended_filters', [
        ('equality', {'field_str': 'PaloAlto', 'field_str_qt': 'Walldorf', 'field_int': 1234},
            []),
        ('extended_w/_quotes', {},
            ["field_str == 'PaloAlto'", "field_str_qt == 'Walldorf'", "field_int == '1234'"]),
        ('extended_w/_double_quotes', {},
            ["field_str == \"PaloAlto\"", "field_str_qt == \"Walldorf\"", "field_int == \"1234\""]),
        ('extended_w/o_quotes', {},
            ["field_str == PaloAlto", "field_str_qt == Walldorf", "field_int == 1234"]),
    ])
    @pytest.mark.filterwarnings('ignore:Trying to parse non-timezone-aware timestamp, assuming UTC.')
    def test_parse_filter_parameters_with_query_transformer(self, equality_filters, extended_filters, testdescr):
        expected_unbreakable = ["FieldStr eq 'PaloAlto'", "FieldStrQT eq 'PREFIX_Walldorf'",
                                "FieldInt eq 1234"]

        def str_add_prefix(x):
            return "'PREFIX_" + str(x) + "'"

        field_map = {'field_str': _base.MasterDataField('field_str', 'FieldStr',),
                     'field_str_qt': _base.MasterDataField('field_str_qt', 'FieldStrQT',
                                                           query_transformer=str_add_prefix),
                     'field_int': _base.MasterDataField('field_int', 'FieldInt',
                                                        query_transformer=lambda x: int(x))
                     }

        actual_unbreakable, actual_breakable = \
            parse_filter_parameters(equality_filters, extended_filters, field_map)

        assert actual_unbreakable == expected_unbreakable
        assert actual_breakable == []

    def test_parse_filter_parameters_with_query_transformer_equality_list(self):
        equality_filters = {'location_name': ['PaloAlto', 'Walldorf']}
        extended_filters = []
        expected_breakable = [["location eq 'PREFIX_PaloAlto'", "location eq 'PREFIX_Walldorf'"]]

        def add_prefix(x):
            return "'PREFIX_" + str(x) + "'"

        field_map = {'location_name': _base.MasterDataField('location_name', 'location', query_transformer=add_prefix)}

        actual_unbreakable, actual_breakable = \
            parse_filter_parameters(equality_filters, extended_filters, field_map)

        assert actual_unbreakable == []
        assert actual_breakable == expected_breakable


@pytest.mark.parametrize('testdescription,equality_filters,extended_filters,expected_ids', [
    ('without filters as None', None, None, ['indicator_id1', 'indicator_id2', 'indicator_id3']),
    ('without filters as dict and list', {}, [], ['indicator_id1', 'indicator_id2', 'indicator_id3']),
    ('equality filters', dict(type='yellow', dimension='zero'), None, ['indicator_id1']),
    ('equality filter list', dict(type=['yellow', 'brown']), None, ['indicator_id1', 'indicator_id2', 'indicator_id3']),
    ('extended filters', None, ['categoryID > "aa"'], ['indicator_id3']),
    ('both filters', dict(type='brown'), ['categoryID > "a"'], ['indicator_id3']),
    ('both filters yields empty result', dict(type='yellow'), ['categoryID > "aa"'], []),
])
@pytest.mark.filterwarnings('ignore:Following parameters are not in our terminology')
def test_apply_filters_post_request_filtering(equality_filters, extended_filters, expected_ids, testdescription):
    data = [{'id': 'indicator_id1', 'type': 'yellow', 'dimension': 'zero', 'categoryID': 'aa'},
            {'id': 'indicator_id2', 'type': 'yellow', 'dimension': 'three', 'categoryID': 'aa'},
            {'id': 'indicator_id3', 'type': 'brown', 'dimension': 'three', 'categoryID': 'aaaa'}]

    actual = apply_filters_post_request(data, equality_filters, extended_filters, field_map=None)

    assert [item['id'] for item in actual] == expected_ids


def test_apply_filters_post_request_property_mapping():
    data = [{'propertyId': 'indicator_id1', 'indicatorType': 'yellow', 'categoryID': 'aa'},
            {'propertyId': 'indicator_id2', 'indicatorType': 'yellow', 'categoryID': 'aa'},
            {'propertyId': 'indicator_id3', 'indicatorType': 'brown', 'categoryID': 'aaaa'}]
    field_map = {'type': _base.masterdata.MasterDataField('type', 'indicatorType'),
                 'template_id': _base.masterdata.MasterDataField('template_id', 'categoryID')}
    equality_filters = dict(type='yellow')
    extended_filters = ['template_id > "a"']
    expected_result = [{'propertyId': 'indicator_id1', 'indicatorType': 'yellow', 'categoryID': 'aa'},
                       {'propertyId': 'indicator_id2', 'indicatorType': 'yellow', 'categoryID': 'aa'}]

    actual = apply_filters_post_request(data, equality_filters, extended_filters, field_map)

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

    @staticmethod
    def generic_response_handler(result, endpoint_data):
        result.extend(endpoint_data)
        return result

    @pytest.mark.filterwarnings('ignore::sailor.utils.utils.DataNotFoundWarning')
    @pytest.mark.parametrize('testdesc,unbreakable_filters,breakable_filters,remote_return', [
        ('no filters - single return', [], [], {'a': 'dict'}),
        ('filters - single return', ['a gt b'], [['c eq 1']], {'a': 'dict'}),
        ('no filters - list return', [], [], ['result']),
        ('filters - list return', ['a gt b'], [['c eq 1']], ['result']),
    ])
    def test_returns_iterable(self, mock_request, unbreakable_filters, breakable_filters, remote_return, testdesc):
        mock_request.return_value = remote_return
        assert False  # fetch_data runs in an infinite loop. test needs to be adapted
        actual = fetch_data('dummy_client_name', self.generic_response_handler,
                            '', unbreakable_filters, breakable_filters)
        assert not issubclass(actual.__class__, str)
        assert isinstance(actual, Iterable)

    def test_no_filters_makes_remote_call_without_query_params(self, mock_request):
        mock_request.return_value = ['result']
        unbreakable_filters = []
        breakable_filters = []
        expected_params = {'$format': 'json'}
        assert False  # fetch_data runs in an infinite loop. test needs to be adapted

        actual = fetch_data('dummy_client_name', self.generic_response_handler,
                            '', unbreakable_filters, breakable_filters)

        mock_request.assert_called_once_with('GET', '', params=expected_params)
        assert actual == ['result']

    @pytest.mark.filterwarnings('ignore::sailor.utils.utils.DataNotFoundWarning')
    def test_adds_filter_parameter_on_call(self, mock_request):
        unbreakable_filters = ["location eq 'Walldorf'"]
        breakable_filters = [["manufacturer eq 'abcCorp'"]]
        expected_parameters = {'$filter': "location eq 'Walldorf' and (manufacturer eq 'abcCorp')",
                               '$format': 'json'}

        fetch_data('dummy_client_name', self.generic_response_handler,
                   '', unbreakable_filters, breakable_filters)

        mock_request.assert_called_once_with('GET', '', params=expected_parameters)

    def test_multiple_calls_aggregated_result(self, mock_request):
        unbreakable_filters = ["location eq 'Walldorf'"]
        # causes _compose_queries to generate two filter strings
        breakable_filters = [["manufacturer eq 'abcCorp'"] * 100]
        mock_request.side_effect = [["result1-1", "result1-2"], ["result2-1"]]
        expected_result = ["result1-1", "result1-2", "result2-1"]

        actual = fetch_data('dummy_client_name', self.generic_response_handler,
                            '', unbreakable_filters, breakable_filters)

        assert actual == expected_result


@pytest.mark.parametrize('input,expected', [
    ("'correctly-quoted'", 'correctly-quoted'),
    ('"correctly-quoted"', 'correctly-quoted'),
    ('"correctly-quoted-with-quotes"in-the"-middle"', 'correctly-quoted-with-quotes"in-the"-middle'),
    ('"wrong\'', '"wrong\''),
    ('"wrong', '"wrong'),
    ('just a string', 'just a string'),
    ('some-quotes"in-the"-middle', 'some-quotes"in-the"-middle'),
])
def test_strip_quote_marks(input, expected):
    actual = _strip_quote_marks(input)
    assert actual == expected


@pytest.mark.parametrize('testdescription,equality_filters,expected_ids', [
    ('numeric', dict(numeric_property=0), ['indicator_id1']),
    ('numeric list', dict(numeric_property=[0, 4.4]), ['indicator_id1', 'indicator_id2']),
    ('true boolean', dict(boolean_property=True), ['indicator_id1']),
    ('int boolean', dict(boolean_property=0), ['indicator_id2']),
    # TODO: post request filtering based on result type
    # ('string boolean', dict(boolean_property='1'), ['indicator_id1']),
    # ('timestamp string', dict(timestamp_property='2020-01-01 11:22:33'), ['indicator_id1']),
])
def test_post_request_filtering_data_types_equality(equality_filters, expected_ids, testdescription):
    data = [{'id': 'indicator_id1', 'numeric_property': 0, 'boolean_property': True,
             'timestamp_property': '2020-01-01T11:22:33+00:00'},
            {'id': 'indicator_id2', 'numeric_property': 4.4, 'boolean_property': False,
             'timestamp_property': '2020-01-01T11:22:33+02:00'}]

    field_map = {
        'id': _base.MasterDataField('filtered_term', 'filtered_term'),
        'numeric_property': _base.MasterDataField('numeric_property', 'numeric_property',
                                                  query_transformer=_base.masterdata._qt_double),
        'boolean_property': _base.MasterDataField('boolean_property', 'boolean_property',
                                                  query_transformer=_base.masterdata._qt_boolean_int_string),
        'timestamp_property': _base.MasterDataField('timestamp_property', 'timestamp_property',
                                                    query_transformer=_base.masterdata._qt_timestamp)
    }

    actual = apply_filters_post_request(data, equality_filters, [], field_map=field_map)

    assert [item['id'] for item in actual] == expected_ids
