import unittest
import os
import sys
from unittest import TestCase
from unittest.mock import patch, Mock

import pytest

from sailor.utils.config import SailorConfig


class TestConfig(TestCase):

    def setUp(self):
        SailorConfig.config = None
        self.env_backup = os.environ.copy()

    def tearDown(self):
        SailorConfig.config = None
        os.environ.clear()
        os.environ.update(self.env_backup)

    def test_load_config_already_present(self):
        config_mock = Mock(SailorConfig)
        SailorConfig.config = config_mock
        result = SailorConfig.load()
        self.assertEqual(result, config_mock)

    @patch('sailor.utils.config.SailorConfig.from_yaml')
    @patch('sailor.utils.config.SailorConfig.from_env')
    def test_load_order_env_first(self, from_env, from_yaml):
        os.environ['SAILOR_CONFIG_JSON'] = "test"
        SailorConfig.load()
        from_env.assert_called_once()
        from_yaml.assert_not_called()

    @patch('sailor.utils.config.SailorConfig.from_yaml')
    @patch('sailor.utils.config.SailorConfig.from_env')
    def test_load_order_yaml_second(self, from_env, from_yaml):
        os.environ['SAILOR_CONFIG_PATH'] = "test"
        from_env.reset_mock()
        from_yaml.reset_mock()
        with patch('os.path.exists') as exists_mock:
            exists_mock.return_value = True
            SailorConfig.load()
            from_yaml.assert_called_once_with("test")
            from_env.assert_not_called()

    @patch('sailor.utils.config.SailorConfig.from_yaml')
    @patch('sailor.utils.config.SailorConfig.from_env')
    def test_load_order_yaml_second_with_config_yml_opt1(self, from_env, from_yaml):
        from_env.reset_mock()
        from_yaml.reset_mock()
        with patch('os.path.exists') as exists_mock:
            exists_mock.return_value = True
            SailorConfig.load()
            expected_config_yml_path = os.path.join(os.path.abspath(os.curdir), 'config.yml')
            from_yaml.assert_called_once_with(expected_config_yml_path)
            from_env.assert_not_called()

    @patch('sailor.utils.config.SailorConfig.from_yaml')
    @patch('sailor.utils.config.SailorConfig.from_env')
    def test_load_order_yaml_second_with_config_yml_opt2(self, from_env, from_yaml):
        from_env.reset_mock()
        from_yaml.reset_mock()
        with patch('os.path.exists') as exists_mock:
            exists_mock.side_effect = [False, True]
            SailorConfig.load()
            expected_config_yml_path = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'config.yml')
            from_yaml.assert_called_once_with(expected_config_yml_path)
            from_env.assert_not_called()

    @patch('sailor.utils.config.SailorConfig.from_yaml')
    @patch('sailor.utils.config.SailorConfig.from_env')
    def test_load_order_no_available_methods(self, from_env, from_yaml):
        with pytest.raises(RuntimeError) as excinfo:
            SailorConfig.load()
        from_env.assert_not_called()
        from_yaml.assert_not_called()
        self.assertIn("No methods left", str(excinfo.value))

    @patch('sailor.utils.config.SailorConfig.load')
    def test_get_config_not_loaded(self, load_mock):
        config_mock = Mock(SailorConfig)
        config_mock.x = 1

        def load_config():
            SailorConfig.config = config_mock

        load_mock.side_effect = load_config
        SailorConfig.get("x")
        load_mock.assert_called_once()

    @patch('sailor.utils.config.SailorConfig.load')
    def test_get_config_already_present(self, load_mock):
        config_mock = Mock(SailorConfig)
        config_mock.x = 1
        SailorConfig.config = config_mock
        SailorConfig.get("x")
        load_mock.assert_not_called()

    def test_get_simple_lookup(self):
        config_mock = Mock(SailorConfig)
        config_mock.x = 1
        SailorConfig.config = config_mock
        result = SailorConfig.get("x")
        self.assertEqual(1, result)
        with pytest.raises(AttributeError):
            SailorConfig.get("z")

    def test_get_deep_lookup(self):
        config_mock = Mock(SailorConfig)
        config_mock.x = {'y': {'z': 42}}
        SailorConfig.config = config_mock
        result = SailorConfig.get("x", "y", "z")
        self.assertEqual(42, result)
        with pytest.raises(KeyError):
            SailorConfig.get("x", "z")


if __name__ == '__main__':
    unittest.main()
