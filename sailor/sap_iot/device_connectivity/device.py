"""
Retrieve Device information from Device Connectiviy API of SAP IoT.

Classes are provided for individual Devices as well as groups of Devices (DeviceSet).
"""

import pandas as pd

from sailor import _base
from ...utils.timestamps import _string_to_timestamp_parser
from .utils import _DeviceConnectivityField, DeviceConnectivityEntity, DeviceConnectivityEntitySet, _device_connectivity_api_url, _dc_fetch_data
from .constants import VIEW_DEVICES
from .sensor_type import SensorTypeSet, find_sensor_types
from .capability import CapabilitySet, find_capabilities

_DEVICE_FIELDS = [
    _DeviceConnectivityField('id', 'id'),
    _DeviceConnectivityField('name', 'name'),
    _DeviceConnectivityField('alternate_id', 'alternateId'),
    _DeviceConnectivityField('_gateway_id', 'gatewayId'),
    _DeviceConnectivityField('_online', 'online'),
    _DeviceConnectivityField('sensors', 'sensors'),
    _DeviceConnectivityField('_authentications', 'authentications'),
    _DeviceConnectivityField('_creation_timestamp', 'creationTimestamp', get_extractor=_string_to_timestamp_parser(unit='ms'))
]

@_base.add_properties
class Device(DeviceConnectivityEntity):
    """SAP IoT Device Object."""

    _field_map = {field.our_name: field for field in _DEVICE_FIELDS}
    
    def find_sensor_types(self, *, extended_filters=(), **kwargs) -> SensorTypeSet:
        """
        Fetch the SensorTypes assigned to the Device.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.
        """
        kwargs['id'] = [s['sensorTypeId'] for s in self.sensors]
        return find_sensor_types(extended_filters=extended_filters, **kwargs)

class DeviceSet(DeviceConnectivityEntitySet):
    """Class representing a group of Devices."""

    _element_type = Device
    _method_defaults = {
        'plot_distribution': {
            'by': '_gateway_id',
        },
    }

    def find_sensor_types(self, *, extended_filters=(), **kwargs) -> SensorTypeSet:
        """
        Fetch the SensorTypes of all Devices in the DeviceSet. Each Device is assigned one or more SensorTypes.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.
        """
        kwargs['id'] = [s['sensorTypeId'] for e in self.elements for s in e.sensors]
        return find_sensor_types(extended_filters=extended_filters, **kwargs)

def find_devices(*, extended_filters=(), **kwargs) -> DeviceSet:
    """
    Fetch Devices from Device Connctivity API with the applied filters, return an DeviceSet.

    This method supports the common filter language explained at :ref:`filter`.

    Parameters
    ----------
    extended_filters
        See :ref:`filter`.
    **kwargs
        See :ref:`filter`.

    Examples
    --------
    Find all Devices with the alternateId 'MyDevice'::

        find_devices(alternate_id='MyDevice')

    Find all Devices which either have the alternateId 'MyDevice' or the alternaeId 'MyOtherDevice'::

        find_devices(alternate_id=['MyDevice', 'MyOtherDevice'])
    """
    unbreakable_filters, breakable_filters = \
        _base.parse_filter_parameters(kwargs, extended_filters, Device._field_map)

    endpoint_url = _device_connectivity_api_url() + VIEW_DEVICES
    object_list = _dc_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return DeviceSet([Device(obj) for obj in object_list])
    