from unittest.mock import patch, Mock

import pytest

from sailor.assetcentral.model import Model, ModelSet, find_models
from sailor.assetcentral import constants


@pytest.fixture
def mock_url():
    with patch('sailor.assetcentral.model._ac_application_url') as mock:
        mock.return_value = 'base_url'
        yield mock


class TestModel:

    @pytest.fixture
    def model(self):
        return Model(
            {'modelId': "D2602147691E463DA91EA2B4C3998C4B", "name": "testEquipment", "location": "USA"})

    @pytest.mark.parametrize('function_name', [
        'find_equipment'
    ])
    def test_find_equipment_delegate_called(self, model, function_name):
        expected = f'expected return value is the value returned by the delegate function "{function_name}"'
        function_under_test = getattr(model, function_name)

        with patch(f'sailor.assetcentral.model.{function_name}', return_value=expected) as mock_delegate:
            actual = function_under_test(param='123', extended_filters=['some_param > some_value'])

            mock_delegate.assert_called_once_with(['some_param > some_value'], param='123',
                                                  model_id=model.id)
            assert actual == expected

    @patch('sailor.assetcentral.model._apply_filters_post_request')
    @patch('sailor.assetcentral.model._fetch_data')
    def test_find_equipment_indicators_fetch_and_apply(self, mock_fetch, mock_apply, model, mock_url,
                                                       make_indicator_set):
        object_list = Mock(name='raw_object_list')
        mock_fetch.return_value = object_list
        mock_apply.return_value = [{'propertyId': 'indicator_1', 'pstid': 'group_id', 'categoryID': 'template_id'},
                                   {'propertyId': 'indicator_2', 'pstid': 'group_id', 'categoryID': 'template_id'}]
        filter_kwargs = {'param1': 'one'}
        extended_filters = ['other_param > 22']
        expected_result = make_indicator_set(propertyId=['indicator_1', 'indicator_2'])

        actual = model.find_model_indicators(**filter_kwargs, extended_filters=extended_filters)

        assert constants.VIEW_MODEL_INDICATORS in mock_fetch.call_args.args[0]
        assert mock_apply.call_args.args[:-1] == (object_list, filter_kwargs, extended_filters)
        assert actual == expected_result


@pytest.mark.filterwarnings('ignore:Following parameters are not in our terminology')
@patch('sailor.assetcentral.model._fetch_data')
def test_find_equipment_expect_fetch_call_args(mock_fetch, mock_url):
    find_params = dict(extended_filters=['integer_param1 < 10'], generation=['one', 'two'])
    expected_call_args = (['integer_param1 lt 10'], [["generation eq 'one'", "generation eq 'two'"]])
    mock_fetch.return_value = [{'modelId': 'm_id1'}, {'modelId': 'm_id2'}]
    expected_result = ModelSet([Model({'modelId': 'm_id1'}),
                                Model({'modelId': 'm_id2'})])

    actual_result = find_models(**find_params)

    assert constants.VIEW_MODELS in mock_fetch.call_args.args[0]
    assert mock_fetch.call_args.args[1:] == expected_call_args
    assert actual_result == expected_result
