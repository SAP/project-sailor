from unittest.mock import patch, PropertyMock, MagicMock

import pytest

from sailor.assetcentral.group import Group, GroupSet


class TestGroup:
    def test_element_fetch_ignores_non_matching_members(self, mock_config):
        with patch('sailor.assetcentral.group.Group._members_raw', new_callable=PropertyMock) as mock_members_raw:
            mock_members_raw.return_value = [{'businessObjectId': 'matching_id', 'businessObjectType': 'MATCH'},
                                             {'businessObjectId': 'wrong_id', 'businessObjectType': 'SOME_TYPE'}]
            element_class = MagicMock()
            element_class._element_type = MagicMock()
            element_class._element_type.__name__ = 'ElementName'

            def find_function(**kwargs):
                assert 'wrong_id' not in kwargs['id']
                assert 'matching_id' in kwargs['id']

            group = Group({})

            group._generic_get_members('MATCH', element_class, find_function, None)

    def test_element_fetch_raises_if_id_is_passed(self, mock_config):
        element_class = MagicMock()
        element_class._element_type = MagicMock()
        element_class._element_type.__name__ = 'ElementName'

        group = Group({})

        with pytest.raises(RuntimeError) as excinfo:
            group._generic_get_members('MATCH', element_class, None, None, id='some_id')

        assert str(excinfo.value) == 'Can not specify `id` when retrieving "ElementName" from a group.'


class TestGroupSet:
    @patch('sailor.assetcentral.equipment._fetch_data')
    def test_element_fetch_skips_duplicates(self, mock_fetch, mock_config):
        with patch('sailor.assetcentral.group.Group._members_raw', new_callable=PropertyMock) as mock_members_raw:
            mock_members_raw.return_value = [{'businessObjectId': 'first_id', 'businessObjectType': 'MATCH'},
                                             {'businessObjectId': 'second_id', 'businessObjectType': 'MATCH'}]
            element_class = MagicMock()
            element_class._element_type = MagicMock()
            element_class._element_type.__name__ = 'ElementName'

            group_set = GroupSet([Group({}), Group({})])

            def find_function(**kwargs):
                assert len(kwargs['id']) == 2  # only two IDs in query. order is not fixed.

            group_set._generic_get_members('MATCH', element_class, find_function, None)

    def test_element_fetch_ignores_non_matching_members(self, mock_config):
        with patch('sailor.assetcentral.group.Group._members_raw', new_callable=PropertyMock) as mock_members_raw:
            mock_members_raw.return_value = [{'businessObjectId': 'matching_id', 'businessObjectType': 'MATCH'},
                                             {'businessObjectId': 'wrong_id', 'businessObjectType': 'SOME_TYPE'}]
            element_class = MagicMock()
            element_class._element_type = MagicMock()
            element_class._element_type.__name__ = 'ElementName'

            def find_function(**kwargs):
                assert 'wrong_id' not in kwargs['id']
                assert 'matching_id' in kwargs['id']

            group_set = GroupSet([Group({})])

            group_set._generic_get_members('MATCH', element_class, find_function, None)

    def test_member_fetch_raises_if_id_is_passed(self, mock_config):
        element_class = MagicMock()
        element_class._element_type = MagicMock()
        element_class._element_type.__name__ = 'ElementName'

        group_set = GroupSet([Group({})])

        with pytest.raises(RuntimeError) as excinfo:
            group_set._generic_get_members('MATCH', element_class, None, None, id='some_id')

        assert str(excinfo.value) == 'Can not specify `id` when retrieving "ElementName" from a group.'
