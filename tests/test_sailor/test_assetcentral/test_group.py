from unittest.mock import patch, PropertyMock

import pytest

from sailor.assetcentral.group import Group, GroupSet


class TestGroup:
    @patch('sailor.assetcentral.equipment._fetch_data')
    def test_equipment_fetch_ignores_non_equipment_members(self, mock_fetch, mock_config):
        with patch('sailor.assetcentral.group.Group._members_raw', new_callable=PropertyMock) as mock_members_raw:
            mock_members_raw.return_value = [{'businessObjectId': 'first_id', 'businessObjectType': 'EQU'},
                                             {'businessObjectId': 'second_id', 'businessObjectType': 'SOME_TYPE'}]
            group = Group({})

            group.find_equipment()

            assert mock_fetch.call_args[0][-1] == [["equipmentId eq 'first_id'"]]

    def test_equipment_fetch_raises_if_id_is_passed(self, mock_config):
        group = Group({})

        with pytest.raises(RuntimeError) as excinfo:
            group.find_equipment(id='some_equipment_id')

        assert str(excinfo.value) == 'Can not specify `id` when retrieving equipment from a group.'


class TestGroupSet:
    @patch('sailor.assetcentral.equipment._fetch_data')
    def test_equipment_fetch_skips_duplicates(self, mock_fetch, mock_config):
        with patch('sailor.assetcentral.group.Group._members_raw', new_callable=PropertyMock) as mock_members_raw:
            mock_members_raw.return_value = [{'businessObjectId': 'first_id', 'businessObjectType': 'EQU'},
                                             {'businessObjectId': 'second_id', 'businessObjectType': 'EQU'}]
            group_set = GroupSet([Group({}), Group({})])

            group_set.find_equipment()

            assert len(mock_fetch.call_args[0][-1][0]) == 2  # only two equipment IDs in query. order is not fixed.

    @patch('sailor.assetcentral.equipment._fetch_data')
    def test_equipment_fetch_ignores_non_equipment_members(self, mock_fetch, mock_config):
        with patch('sailor.assetcentral.group.Group._members_raw', new_callable=PropertyMock) as mock_members_raw:
            mock_members_raw.return_value = [{'businessObjectId': 'first_id', 'businessObjectType': 'EQU'},
                                             {'businessObjectId': 'second_id', 'businessObjectType': 'SOME_TYPE'}]
            group_set = GroupSet([Group({})])

            group_set.find_equipment()

            assert mock_fetch.call_args[0][-1] == [["equipmentId eq 'first_id'"]]

    def test_equipment_fetch_raises_if_id_is_passed(self, mock_config):
        group_set = GroupSet([Group({})])

        with pytest.raises(RuntimeError) as excinfo:
            group_set.find_equipment(id='some_equipment_id')

        assert str(excinfo.value) == 'Can not specify `id` when retrieving equipment from a group.'
