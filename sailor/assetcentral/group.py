"""
Group module can be used to retrieve Groups information from AssetCentral.

Classes are provided for individual Groups as well as groups of Groups (GroupSet).
"""

from functools import cached_property
import warnings

from sailor import _base
from ..utils.timestamps import _string_to_timestamp_parser
from .utils import (AssetcentralEntity, _AssetcentralField, AssetcentralEntitySet,
                    _ac_application_url, _ac_fetch_data)
from .constants import VIEW_GROUPS
from .equipment import find_equipment, EquipmentSet
from .location import find_locations, LocationSet
from .model import find_models, ModelSet

_GROUP_FIELDS = [
    _AssetcentralField('name', 'displayId'),
    _AssetcentralField('group_type', 'groupTypeCode'),
    _AssetcentralField('short_description', 'shortDescription'),
    _AssetcentralField('risk_value', 'riskValue', query_transformer=_base.masterdata._qt_double),
    _AssetcentralField('id', 'id'),
    _AssetcentralField('_status', 'status'),
    _AssetcentralField('_normalized_risk_score', 'normalizedRiskScore'),
    _AssetcentralField('_criticality_value', 'criticalityValue'),
    _AssetcentralField('_risk_color_code', 'riskColorCode'),
    _AssetcentralField('_criticality_code', 'criticalityCode'),
    _AssetcentralField('_version', 'version'),
    _AssetcentralField('_group_type_count', 'groupTypeCount'),
    _AssetcentralField('_long_description', 'longDescription'),
    _AssetcentralField('_changed_on', 'lastEditedTime', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_created_on', 'creationTime', get_extractor=_string_to_timestamp_parser(unit='ms')),
]


@_base.add_properties
class Group(AssetcentralEntity):
    """AssetCentral Location Object."""

    _field_map = {field.our_name: field for field in _GROUP_FIELDS}

    @cached_property
    def _members_raw(self):
        endpoint_url = _ac_application_url() + VIEW_GROUPS + f'/{self.id}/businessobjects'
        object_list = _ac_fetch_data(endpoint_url)
        return object_list

    def _generic_get_members(self, business_object_type, set_class, find_function, extended_filters, **kwargs):
        member_name = set_class._element_type.__name__

        if kwargs.get('id'):
            raise RuntimeError(f'Cannot specify `id` when retrieving "{member_name}" from a group.')

        kwargs['id'] = [item['businessObjectId'] for item in self._members_raw
                        if item['businessObjectType'] == business_object_type]

        if not kwargs['id']:
            warnings.warn(f'There are no "{member_name}" in this group!')
            return set_class([])

        return find_function(extended_filters=extended_filters, **kwargs)

    def find_equipment(self, *, extended_filters=(), **kwargs):
        """Retrieve all Equipment that are part of this group.

        This is a wrapper for :meth:`sailor.assetcentral.equipment.find_equipment`
        that limits the fetch query to members of this group.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.
        """
        return self._generic_get_members('EQU', EquipmentSet, find_equipment, extended_filters, **kwargs)

    def find_locations(self, *, extended_filters=(), **kwargs):
        """Retrieve all Locations that are part of this group.

        This is a wrapper for :meth:`sailor.assetcentral.location.find_location`
        that limits the fetch query to members of this group.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.
        """
        return self._generic_get_members('FL', LocationSet, find_locations, extended_filters, **kwargs)

    def find_models(self, *, extended_filters=(), **kwargs):
        """Retrieve all Models that are part of this group.

        This is a wrapper for :meth:`sailor.assetcentral.model.find_models`
        that limits the fetch query to members of this group.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.
        """
        return self._generic_get_members('MOD', ModelSet, find_models, extended_filters, **kwargs)


class GroupSet(AssetcentralEntitySet):
    """Class representing a group of Groups."""

    _element_type = Group
    _method_defaults = {
        'plot_distribution': {
            'by': 'group_type',
        },
    }

    def _generic_get_members(self, business_object_type, set_class, find_function, extended_filters, **kwargs):
        member_name = set_class._element_type.__name__

        if kwargs.get('id'):
            raise RuntimeError(f'Cannot specify `id` when retrieving "{member_name}" from a group.')

        kwargs['id'] = set([item['businessObjectId'] for group in self.elements for item in group._members_raw
                            if item['businessObjectType'] == business_object_type])
        if not kwargs['id']:
            warnings.warn(f'There are no "{member_name}" in any of the groups in this set!')
            return set_class([])

        return find_function(extended_filters=extended_filters, **kwargs)

    def find_equipment(self, *, extended_filters=(), **kwargs):
        """Retrieve all equipment that are part of any group in this GroupSet.

        This is a wrapper for :meth:`sailor.assetcentral.equipment.find_equipment`
        that limits the fetch query to members of any group in this set.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.
        """
        return self._generic_get_members('EQU', EquipmentSet, find_equipment, extended_filters, **kwargs)

    def find_locations(self, *, extended_filters=(), **kwargs):
        """Retrieve all locations that are part of any group in this GroupSet.

        This is a wrapper for :meth:`sailor.assetcentral.location.find_locations`
        that limits the fetch query to members of any group in this set.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.
        """
        return self._generic_get_members('FL', LocationSet, find_locations, extended_filters, **kwargs)

    def find_models(self, *, extended_filters=(), **kwargs):
        """Retrieve all models that are part of any group in this GroupSet.

        This is a wrapper for :meth:`sailor.assetcentral.model.find_models`
        that limits the fetch query to members of any group in this set.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.
        """
        return self._generic_get_members('MOD', ModelSet, find_models, extended_filters, **kwargs)


def find_groups(*, extended_filters=(), **kwargs) -> GroupSet:
    """
    Fetch Groups from AssetCentral with the applied filters, return a GroupSet.

    This method supports the common filter language explained at :ref:`filter`, but the filters
    are evaluated locally rather than remotely, potentially leading to longer query times.

    Parameters
    ----------
    extended_filters
        See :ref:`filter`.
    **kwargs
        See :ref:`filter`.

    Examples
    --------
    Find all Groups with the name 'MyGroup'::

        find_groups(name='MyGroup')

    Find all Groups which either have the name 'MyGroup' or the name 'MyOtherGroup'::

        find_group(name=['MyGroup', 'MyOtherGroup'])

    Find all Groups with the name 'MyGroup' which are also of type 'FLEET'::

        find_groups(name='MyGroup', group_type='FLEET')

    Find all Groups having a risk_value greater than 0::

        groups = find_groups(extended_filters=['risk_value > 0'])
    """
    endpoint_url = _ac_application_url() + VIEW_GROUPS
    object_list = _ac_fetch_data(endpoint_url)

    filtered_objects = _base.apply_filters_post_request(object_list, kwargs, extended_filters, Group._field_map)
    return GroupSet([Group(obj) for obj in filtered_objects])
