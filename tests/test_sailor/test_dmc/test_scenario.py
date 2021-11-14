from unittest.mock import patch

import pytest

from sailor.dmc.scenario import Scenario, ScenarioSet, find_scenarios


@pytest.fixture
def mock_url():
    with patch('sailor.dmc.scenario._dmc_application_url') as mock:
        mock.return_value = 'base_url'
        yield mock


@pytest.fixture
def mock_fetch():
    with patch('sailor.dmc.scenario._dmc_fetch_data') as mock:
        mock.return_value = [{
            'scenarioCreatedAt': '2000-01-01 00:00:00.000',
            'scenarioChangedAt': '2000-01-02 00:00:00.000',
            'scenarioDescription': 'Example_Description',
            'scenarioId': 'Example_ID',
            'scenarioName': 'Example_Name',
            'scenarioObjective': 'Example_Objective',
            'scenarioStatus': 'Example_Status',
            'scenarioVersion': 1
        }]
        yield mock


@pytest.fixture
def mock_find_inspection_logs():
    with patch('sailor.dmc.scenario.find_inspection_logs') as mock:
        yield mock


def test_expected_public_attributes_are_present():
    expected_attributes = [
        'short_description', 'id', 'name', 'objective', 'status', 'version', 'created_at', 'changed_at'
    ]

    fieldmap_public_attributes = [field.our_name for field in Scenario._field_map.values() if field.is_exposed]

    assert expected_attributes == fieldmap_public_attributes


def test_correct_arguments(mock_url, mock_fetch):

    plant = 'Example_Plant'
    sfc = 'Example_SFC'

    expected_url = 'base_url/aiml/v1/active-scenarios'

    expected_filters = {
        'plant': 'Example_Plant',
        'sfc': 'Example_SFC',
    }

    expected_filter_fields = {
        'deployment_type': 'deploymentType',
        'material': 'material',
        'operation': 'operation',
        'plant': 'plant',
        'resource': 'resource',
        'routing': 'routing',
        'sfc': 'sfc',
    }

    find_scenarios(plant=plant, sfc=sfc)

    mock_fetch.assert_called_once_with(expected_url, expected_filters, expected_filter_fields)


def test_correct_scenario_object(mock_url, mock_fetch):
    kwargs = {
        'deployment_type': 'Deployment_Type',
        'material': 'Example_Material',
        'operation': 'Example_Operation',
        'plant': 'Example_Plant',
        'resource': 'Example_Resource',
        'routing': 'Example_Routing',
        'sfc': 'Example_SFC',
    }

    scenarios = find_scenarios(**kwargs)

    assert len(scenarios) == 1
    assert type(scenarios) == ScenarioSet

    scenario = scenarios[0]

    assert type(scenario) == Scenario

    expected_attributes = {
        'id': 'Example_ID',
        'version': 1,
        'name': 'Example_Name',
        'objective': 'Example_Objective',
        'status': 'Example_Status',
        'short_description': 'Example_Description',
        'created_at': '2000-01-01 00:00:00.000',
        'changed_at': '2000-01-02 00:00:00.000',
    }

    for property_name, value in expected_attributes.items():
        assert getattr(scenario, property_name) == value


def test_get_inspection_logs(mock_url, mock_fetch, mock_find_inspection_logs):
    kwargs = {
        'deployment_type': 'Deployment_Type',
        'material': 'Example_Material',
        'operation': 'Example_Operation',
        'plant': 'Example_Plant',
        'resource': 'Example_Resource',
        'routing': 'Example_Routing',
        'sfc': 'Example_SFC',
    }

    scenarios = find_scenarios(**kwargs)

    scenario = scenarios[0]

    scenario.get_inspection_logs()

    mock_find_inspection_logs.assert_called_once_with(scenario_id='Example_ID', scenario_version=1)
