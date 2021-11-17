"""
Retrieve Capability information from Device Connectiviy API of SAP IoT.

Classes are provided for individual Capabilities as well as groups of Capabilities (CapabilitySet).
"""

from sailor import _base
from .utils import _DeviceConnectivityField, DeviceConnectivityEntity, DeviceConnectivityEntitySet, \
    _device_connectivity_api_url, _dc_fetch_data
from .constants import VIEW_CAPABILITIES


_CAPABILITY_FIELDS = [
    _DeviceConnectivityField('name', 'name'),
    _DeviceConnectivityField('alternate_id', 'alternateId'),
    _DeviceConnectivityField('properties', 'properties'),
    _DeviceConnectivityField('id', 'id'),
]


@_base.add_properties
class Capability(DeviceConnectivityEntity):
    """SAP IoT Capability Object."""

    _field_map = {field.our_name: field for field in _CAPABILITY_FIELDS}


class CapabilitySet(DeviceConnectivityEntitySet):
    """Class representing a group of Capabilities."""

    _element_type = Capability


def find_capabilities(*, extended_filters=(), **kwargs) -> CapabilitySet:
    """
    Fetch Capabilities from Device Connctivity API with the applied filters, return an CapabilitySet.

    This method supports the common filter language explained at :ref:`filter`.

    Parameters
    ----------
    extended_filters
        See :ref:`filter`.
    **kwargs
        See :ref:`filter`.

    Examples
    --------
    Find all Capabilities with the id 'MyCapability'::

        find_capabilities(id='MyCapability')

    Find all Capabilities which either have the id 'MyDevice' or the id 'MyOtherCapability'::

        find_capabilities(id=['MyCapability', 'MyOtherCapability'])
    """
    unbreakable_filters, breakable_filters = \
        _base.parse_filter_parameters(kwargs, extended_filters, Capability._field_map)

    endpoint_url = _device_connectivity_api_url() + VIEW_CAPABILITIES
    object_list = _dc_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return CapabilitySet([Capability(obj) for obj in object_list])
