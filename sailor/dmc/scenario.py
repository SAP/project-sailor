"""
Scenario module can be used to retrieve Scenario information from Digital Manufacturing Cloud.

Classes are provided for individual Scenarios as well as groups of Scenarios (ScenarioSet).
"""

from sailor import _base
from sailor.dmc.inspection_log import InspectionLogSet, find_inspection_logs

from .constants import ACTIVE_SCENARIOS, AIML_GROUP
from .utils import (DigitalManufacturingCloudEntity, DigitalManufacturingCloudEntitySet,
                    _DigitalManufacturingCloudField, _dmc_application_url, _dmc_fetch_data)

_SCENARIO_FIELDS = [
    _DigitalManufacturingCloudField('short_description', 'scenarioDescription'),
    _DigitalManufacturingCloudField('id', 'scenarioId'),
    _DigitalManufacturingCloudField('name', 'scenarioName'),
    _DigitalManufacturingCloudField('objective', 'scenarioObjective'),
    _DigitalManufacturingCloudField('status', 'scenarioStatus'),
    _DigitalManufacturingCloudField('version', 'scenarioVersion'),
    _DigitalManufacturingCloudField('created_at', 'scenarioCreatedAt'),
    _DigitalManufacturingCloudField('changed_at', 'scenarioChangedAt'),
    _DigitalManufacturingCloudField('_combinations', 'scenarioCombinations'),
    _DigitalManufacturingCloudField('_deployment', 'deployment')
]

# all fields which can be used as request parameters for the endpoint /active-scenarios
_SCENARIO_FILTER_FIELDS = {
    'deployment_type': 'deploymentType',
    'material': 'material',
    'operation': 'operation',
    'plant': 'plant',
    'resource': 'resource',
    'routing': 'routing',
    'sfc': 'sfc',
}


@_base.add_properties
class Scenario(DigitalManufacturingCloudEntity):
    """Digital Manufacturing Cloud Scenario Object."""

    _field_map = {field.our_name: field for field in _SCENARIO_FIELDS}

    def __repr__(self) -> str:
        """Return a very short string representation."""
        name = getattr(self, 'name', getattr(self, 'short_description', None))
        return f'{self.__class__.__name__}(name="{name}", id="{self.id}")'

    def get_inspection_logs(self) -> InspectionLogSet:
        """Fetches all Inspection Logs belonging to this Scenario from Digital Manufacturing Cloud.

        For further details see :ref:`find_inspection_logs()`
        """
        return find_inspection_logs(
            scenario_id=self.id,
            scenario_version=self.version,
        )


class ScenarioSet(DigitalManufacturingCloudEntitySet):
    """Class representing a group of Scenarios."""

    _element_type = Scenario


def find_scenarios(**kwargs) -> ScenarioSet:
    """Fetch Scenarios from Digital Manufacturing Cloud with the applied filters, return a ScenarioSet.

    Any named keyword arguments are applied as equality filters, i.e. the name of the Scenario property is checked
    against the value of the keyword argument. A combination of 'plant' and 'sfc' or 'plant', 'material' and
    'operation' is required.

    Parameters
    ----------
    **kwargs
        See :ref:`filter`.

    Examples
    --------
    Find all Scenarios with plant 'MyPlant' and sfc 'MySFC':

      find_scenarios(plant='MyPlant', sfc='MySFC')

    Find all Scenarios with plant 'MyPlant', operation 'MyOperation' and material 'MyMaterial':

      kwargs = {
          'plant': 'MyPlant',
          'operation': 'MyOperation',
          'material': 'MyMaterial',
      }

      find_scenarios(**kwargs)
    """

    endpoint_url = _dmc_application_url() + AIML_GROUP + ACTIVE_SCENARIOS

    object_list = _dmc_fetch_data(endpoint_url, kwargs, _SCENARIO_FILTER_FIELDS)

    return ScenarioSet([Scenario(obj) for obj in object_list])
