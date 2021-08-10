from unittest.mock import patch, Mock

import pytest

from sailor.assetcentral.model import Model
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

            mock_delegate.assert_called_once_with(extended_filters=['some_param > some_value'], param='123',
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

    def test_expected_public_attributes_are_present(self):
        expected_attributes = [
            'name', 'model_type', 'manufacturer', 'short_description', 'service_expiration_date',
            'model_expiration_date', 'generation', 'long_description', 'id', 'template_id', 'model_template_id'
        ]

        fieldmap_public_attributes = [
            field.our_name for field in Model._field_map.values() if field.is_exposed
        ]

        assert expected_attributes == fieldmap_public_attributes
