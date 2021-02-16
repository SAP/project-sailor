import unittest
from unittest import TestCase
from unittest.mock import patch

from sailor.assetcentral.equipment import Equipment
from sailor.assetcentral.equipment_model import EquipmentModel
from sailor.assetcentral.indicators import Indicator


class TestEquipmentModel(TestCase):

    @classmethod
    def setUpClass(cls):
        # mock the whole SailorConfig for all tests
        cls.config_mock = patch('sailor.utils.config.SailorConfig')
        cls.config_mock.start()

    @classmethod
    def tearDownClass(cls):
        cls.config_mock.stop()

    def setUp(self):
        self.obj = EquipmentModel(
            {'modelId': "D2602147691E463DA91EA2B4C3998C4B", "name": "testEquipment", "location": "USA"})

    @patch('sailor.assetcentral.equipment_model.EquipmentModel.find_equipments')
    def test_find_equipments(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value = [Equipment({"equipmentId": "E70100304AEFE7A616005E02C64AE811"})]
        response = self.obj.find_equipments()
        self.assertIsNotNone(response)
        self.assertIsInstance(response, list)
        self.assertIsInstance(response[0], Equipment)

    @patch('sailor.assetcentral.equipment_model.EquipmentModel.find_model_indicators')
    def test_find_model_indicators(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value = [Indicator({"propertyId": "E70100304AEFE7A616005E02C64AE811"})]
        response = self.obj.find_model_indicators()
        self.assertIsNotNone(response)
        self.assertIsInstance(response, list)
        self.assertIsInstance(response[0], Indicator)

    @patch('sailor.assetcentral.equipment_model.EquipmentModel.get_header')
    def test_get_header(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value = {}
        response = self.obj.get_header()
        self.assertIsNotNone(response)
        self.assertIsInstance(response, dict)

    @patch('sailor.assetcentral.equipment_model.EquipmentModel.get_indicator_configuration_of_model')
    def test_get_indicator_configuration_of_model(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value = {}
        response = self.obj.get_indicator_configuration_of_model()
        self.assertIsNotNone(response)
        self.assertIsInstance(response, dict)


if __name__ == '__main__':
    unittest.main()
