from sailor.pai.utils import _pai_fetch_data, _pai_response_handler


def test_pai_response_handler():
    result_list = ['dummy']
    endpoint_data = {'d': {'results': ['result1', 'result2']}}
    expected = ['dummy', 'result1', 'result2']
    actual = _pai_response_handler(result_list, endpoint_data)
    assert actual == expected


def test_pai_fetch_data_integration(mock_request):
    unbreakable_filters = ["location eq 'Walldorf'"]
    breakable_filters = [["manufacturer eq 'abcCorp'"]]
    expected_parameters = {'$filter': "location eq 'Walldorf' and (manufacturer eq 'abcCorp')",
                           '$format': 'json'}
    expected = ['result1', 'result2']
    mock_request.return_value = {'d': {'results': expected}}

    assert False  # fetch_data runs in an infinite loop. test needs to be adapted
    actual = _pai_fetch_data('', unbreakable_filters, breakable_filters)

    mock_request.assert_called_once_with('GET', '', params=expected_parameters)
    assert actual == expected
