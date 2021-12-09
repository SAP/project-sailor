from unittest.mock import patch

import pytest

from sailor.utils.oauth_wrapper import RequestError
from sailor.assetcentral.utils import (
    AssetcentralRequestValidationError, _AssetcentralField, _AssetcentralWriteRequest, AssetcentralEntity,
    _ac_fetch_data, _ac_response_handler)


class TestAssetcentralRequest:

    def test_setitem_sets_raw_and_emits_warning_if_key_not_found_in_mapping(self):
        actual = _AssetcentralWriteRequest({})
        with pytest.warns(UserWarning, match="Unknown name for _AssetcentralWriteRequest parameter found: 'abc'"):
            actual.update({'abc': 1})
        assert actual == {'abc': 1}

    def test_setitem_sets_nothing_and_warns_if_key_known_but_not_writable(self):
        field_map = {'our_name': _AssetcentralField('our_name', 'their_name_get')}
        actual = _AssetcentralWriteRequest(field_map)

        with pytest.warns(UserWarning, match="Parameter 'our_name' is not available"):
            actual.update({'our_name': 1})

        assert actual == {}

    def test_setitem_sets_their_name(self):
        field_map = {'our_name': _AssetcentralField('our_name', 'their_name_get', 'their_name_put')}
        actual = _AssetcentralWriteRequest(field_map)

        actual.update({'our_name': 1})

        assert actual == {'their_name_put': 1}

    def test_setitem_uses_field_put_setter(self):
        def put_setter(payload, value):
            payload['test'] = int(value)
        field_map = {'our_name': _AssetcentralField('our_name', 'their_name_get', 'their_name_put',
                                                    put_setter=put_setter)}
        actual = _AssetcentralWriteRequest(field_map)

        actual.update({'our_name': '111'})

        assert actual == {'test': 111}

    @pytest.mark.filterwarnings('ignore:Unknown name for _AssetcentralWriteRequest parameter found')
    def test_from_object(self, monkeypatch):
        field_map = {'ABC': _AssetcentralField('ABC', 'ABC', 'AbC'),
                     'DEF': _AssetcentralField('DEF', 'DEF'),
                     'GHI': _AssetcentralField('GHI', 'GHI', 'GHI')}
        monkeypatch.setattr(AssetcentralEntity, '_field_map', field_map)
        entity = AssetcentralEntity({'ABC': 1, 'DEF': 2, 'GHI': 3})
        expected_request_dict = {'AbC': 1, 'GHI': 3}

        actual = _AssetcentralWriteRequest.from_object(entity)

        assert actual == expected_request_dict

    def test_insert_user_input_updates_dict(self):
        field_map = {'our_name': _AssetcentralField('our_name', 'their_name_get', 'their_name_put')}
        actual = _AssetcentralWriteRequest(field_map)

        actual.insert_user_input({'our_name': 1})

        assert actual == {'their_name_put': 1}

    def test_insert_user_input_raises_when_field_forbidden(self):
        field_map = {'our_name': _AssetcentralField('our_name', 'their_name_get', 'their_name_put')}
        actual = _AssetcentralWriteRequest(field_map)
        with pytest.raises(RuntimeError, match="You cannot set 'our_name' in this request."):
            actual.insert_user_input({'our_name': 1}, forbidden_fields=['our_name'])
        with pytest.raises(RuntimeError, match="You cannot set 'their_name_put' in this request."):
            actual.insert_user_input({'their_name_put': 1}, forbidden_fields=['our_name'])

    @pytest.mark.parametrize('is_mandatory,has_value', [
        (True, False),
        (True, True),
        (False, False),
        (False, True),
    ])
    def test_validate_raises_when_mandatory_field_missing(self, is_mandatory, has_value):
        field_map = {'field':
                     _AssetcentralField('field', 'their_name_get', 'their_name_put', is_mandatory=is_mandatory)}
        actual = _AssetcentralWriteRequest(field_map)
        if has_value:
            actual.update(field='value')

        if not has_value and is_mandatory:
            with pytest.raises(AssetcentralRequestValidationError):
                actual.validate()
        else:
            actual.validate()


@pytest.mark.parametrize('testdesc,endpoint_data,expected', [
    ('single return', {'a': 'dict'}, ['dummy', {'a': 'dict'}]),
    ('list return', ['result1', 'result2'], ['dummy', 'result1', 'result2']),
])
def test_ac_response_handler(endpoint_data, expected, testdesc):
    result_list = ['dummy']
    actual = _ac_response_handler(result_list, endpoint_data)
    assert actual == expected


def test_ac_fetch_data_integration(mock_request):
    unbreakable_filters = ["location eq 'Walldorf'"]
    breakable_filters = [["manufacturer eq 'abcCorp'"]]
    expected_parameters = {'$filter': "location eq 'Walldorf' and (manufacturer eq 'abcCorp')",
                           '$format': 'json'}
    expected = mock_request.return_value = ['result1']

    assert False  # fetch_data runs in an infinite loop. test needs to be adapted
    actual = _ac_fetch_data('', unbreakable_filters, breakable_filters)

    mock_request.assert_called_once_with('GET', '', params=expected_parameters)
    assert actual == expected


@patch('time.sleep')
def test_ac_fetch_data_rate_limiting(mock_sleep, mock_request):
    exception = RequestError('test_message', 429, 'reason', 'error_text')
    mock_request.side_effect = [exception, 'retry-response']

    actual = _ac_fetch_data('')

    assert mock_request.call_count == 2
    assert actual == ['retry-response']


@patch('time.sleep')
def test_ac_fetch_data_rate_limiting_repeated_error(mock_sleep, mock_request):
    exception = RequestError('test_message', 429, 'reason', 'error_text')
    mock_request.side_effect = [exception, exception, 'some-response']

    with pytest.raises(RequestError, match='test_message'):
        _ac_fetch_data('')

    assert mock_request.call_count == 2


@patch('time.sleep')
def test_ac_fetch_data_rate_limiting_different_exception(mock_sleep, mock_request):
    exception = RuntimeError('Unexpected Error')
    mock_request.side_effect = [exception, 'some-response']

    with pytest.raises(RuntimeError, match='Unexpected Error'):
        _ac_fetch_data('')

    assert mock_request.call_count == 1
