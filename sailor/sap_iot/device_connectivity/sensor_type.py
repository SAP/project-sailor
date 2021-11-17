"""
Retrieve Sensor Type information from Device Connectiviy API of SAP IoT.

Classes are provided for individual Sensor Types as well as groups of Sensor Types (SensorTypeSet).
"""

from sailor import _base
from sailor.sap_iot.device_connectivity.capability import CapabilitySet, find_capabilities
from .utils import _DeviceConnectivityField, DeviceConnectivityEntity, DeviceConnectivityEntitySet, \
    _device_connectivity_api_url, _dc_fetch_data
from .constants import VIEW_SENSOR_TYPES


_SENSOR_TYPE_FIELDS = [
    _DeviceConnectivityField('name', 'name'),
    _DeviceConnectivityField('alternate_id', 'alternateId'),
    _DeviceConnectivityField('capabilities', 'capabilities'),
    _DeviceConnectivityField('id', 'id'),
]


@_base.add_properties
class SensorType(DeviceConnectivityEntity):
    """SAP IoT Sensor Type Object."""

    _field_map = {field.our_name: field for field in _SENSOR_TYPE_FIELDS}

    def find_capabilities(self, *, extended_filters=(), **kwargs) -> CapabilitySet:
        """
        Find the Capabilities assigned to the SensorType.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.
        """
        kwargs['id'] = [c['id'] for c in self.capabilities]
        return find_capabilities(extended_filters=extended_filters, **kwargs)


class SensorTypeSet(DeviceConnectivityEntitySet):
    """Class representing a group of Sensor Types."""

    _element_type = SensorType

    def find_capabilities(self, *, extended_filters=(), **kwargs) -> CapabilitySet:
        """
        Find the Capabilities of all the SensorTypes in the SensorTypeSet.

        Each SensorType is assigned one or more Capability.
        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.
        """
        kwargs['id'] = [c['id'] for e in self.elements for c in e.capabilities]
        return find_capabilities(extended_filters=extended_filters, **kwargs)


def find_sensor_types(*, extended_filters=(), **kwargs) -> SensorTypeSet:
    """
    Fetch Sensor Types from Device Connctivity API with the applied filters, return an SensorTypeSet.

    This method supports the common filter language explained at :ref:`filter`.

    Parameters
    ----------
    extended_filters
        See :ref:`filter`.
    **kwargs
        See :ref:`filter`.

    Examples
    --------
    Find all Sensor Types with the id 'MySensorType'::

        find_sensor_types(id='MySensorType')

    Find all Sensor Types which either have the id 'MyDevice' or the id 'MyOtherSensorType'::

        find_sensor_types(id=['MySensorType', 'MyOtherSensorType'])
    """
    unbreakable_filters, breakable_filters = \
        _base.parse_filter_parameters(kwargs, extended_filters, SensorType._field_map)

    endpoint_url = _device_connectivity_api_url() + VIEW_SENSOR_TYPES
    object_list = _dc_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return SensorTypeSet([SensorType(obj) for obj in object_list])
