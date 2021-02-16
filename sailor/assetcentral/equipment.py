"""
Retrieve Equipment information from AssetCentral.

Classes are provided for individual Equipments as well as groups of Equipments (EquipmentSet).
"""

from .constants import VIEW_EQUIPMENT, VIEW_OBJECTS
from .failure_mode import find_failure_modes, FailureModeSet
from .indicators import Indicator, IndicatorSet
from .notification import NotificationSet, find_notifications
from .location import Location, find_locations
from .workorder import WorkorderSet, find_workorders
from .utils import fetch_data, add_properties, parse_filter_parameters, AssetcentralEntity, ResultSet, \
    ac_application_url, apply_filters_post_request, _string_to_date_parser


@add_properties
class Equipment(AssetcentralEntity):
    """
    AssetCentral Equipment Object.

    Properties (in AC terminology) are:
    equipmentId, name, internalId, status, statusDescription, version, hasInRevision,
    modelId, modelName, shortDescription, templateId, subclass, modelTemplate,
    location, criticalityCode, criticalityDescription, manufacturer, completeness, createdOn,
    changedOn, publishedOn, serialNumber, batchNumber, tagNumber, lifeCycle, lifeCycleDescription,
    source, imageURL, operator, coordinates, installationDate, equipmentStatus, buildDate,
    isOperatorValid, modelVersion, soldTo, image, consume, dealer, serviceProvider, primaryExternalId,
    equipmentSearchTerms, sourceSearchTerms, manufacturerSearchTerms, operatorSearchTerms, class
    """

    _location = None

    @classmethod
    def get_property_mapping(cls):
        """Return a mapping from assetcentral terminology to our terminology."""
        return {
            'id': ('equipmentId', None, None, None),
            'name': ('name', None, None, None),
            'short_description': ('shortDescription', None, None, None),
            'batch_number': ('batchNumber', None, None, None),
            'build_date': ('buildDate', _string_to_date_parser('buildDate', 'ms'), None, None),
            'criticality_description': ('criticalityDescription', None, None, None),
            'equipment_model_id': ('modelId', None, None, None),
            'equipment_model_name': ('modelName', None, None, None),
            'installation_date': ('installationDate', _string_to_date_parser('installationDate', 'ms'), None, None),
            'lifecycle_description': ('lifeCycleDescription', None, None, None),
            'location_name': ('location', None, None, None),
            'manufacturer': ('manufacturer', None, None, None),
            'operator': ('operator', None, None, None),
            'serial_number': ('serialNumber', None, None, None),
            'status_text': ('statusDescription', None, None, None),
            'template_id': ('templateId', None, None, None),
        }

    @property
    def location(self) -> Location:
        """Return the Location associated with this Equipment."""
        if self._location is None:
            locations = find_locations(name=self.location_name)  # why do we have a name here, not an ID???
            assert len(locations) == 1
            self._location = locations[0]
        return self._location

    def find_equipment_indicators(self, extended_filters=(), **kwargs) -> IndicatorSet:
        """Find all indicators assigned to this Equipment.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Example
        -------
        Find all indicators with name 'MyIndicator' for equipment object 'my_equipment'::

            my_equipment.find_equipment_indicators(name='MyIndicator')
        """
        # AC-BUG: this endpoint just silently ignores filter parameters, so we can't really support them...
        endpoint_url = ac_application_url() + VIEW_EQUIPMENT + f'({self.id})' + '/indicatorvalues'
        object_list = fetch_data(endpoint_url)

        filtered_objects = apply_filters_post_request(object_list, kwargs, extended_filters,
                                                      Indicator.get_property_mapping())
        return IndicatorSet([Indicator(obj) for obj in filtered_objects])

    def find_notifications(self, extended_filters=(), **kwargs) -> NotificationSet:
        """
        Fetch notifications objects associated with this equipment.

        This is a wrapper for :meth:`sailor.assetcentral.notification.find_notifications`
        that limits the fetch query to this equipment.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Example
        -------
        Find all notifications for equipment object 'my_equipment'::

            my_equipment.find_notifications()
        """
        kwargs['equipment_id'] = self.id
        return find_notifications(extended_filters, **kwargs)

    def find_failure_modes(self, extended_filters=(), **kwargs) -> FailureModeSet:
        """
        Fetch the failure modes configured for the given equipment.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Examples
        --------
        Find all failure modes with name 'MyFailureMode' for equipment object 'my_equipment'::

            my_equipment.find_failure_modes(name='MyFailureMode')
        """
        # AC-BUG: this endpoint just silently ignores filter parameters, so we can't really support them...
        if 'id' in kwargs or 'ID' in kwargs:
            raise RuntimeError('Can not manually filter for FailureMode ID when using this method.')
        endpoint_url = ac_application_url() + VIEW_OBJECTS + 'EQU/' + self.id + '/failuremodes'
        object_list = fetch_data(endpoint_url)
        kwargs['id'] = [element['ID'] for element in object_list]
        return find_failure_modes(extended_filters, **kwargs)

    def find_workorders(self, extended_filters=(), **kwargs) -> WorkorderSet:
        """
        Fetch workorder objects associated with this equipment.

        This is a wrapper for :meth:`sailor.assetcentral.workorder.find_workorders` that limits the fetch query
        to this equipment.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.
        """
        kwargs['equipment_id'] = self.id
        return find_workorders(extended_filters, **kwargs)

    def __hash__(self):
        """Hash of an equipment object is the hash of it's id."""
        return self.id.__hash__()


class EquipmentSet(ResultSet):
    """Class representing a group of Equipments."""

    _element_name = 'Equipment'
    _set_name = 'EquipmentSet'
    _method_defaults = {
        'plot_distribution': {
            'by': 'location_name',
        },
        'as_df': {
            'properties': Equipment.get_property_mapping().keys()
        }
    }

    def find_notifications(self, extended_filters=(), **kwargs) -> NotificationSet:
        """Find all Notifications for any of the equipments in this EquipmentSet.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Examples
        --------
        Get all notifications for the 'equipment_set' as a data frame::

            equipment_set = find_equipments()

            equipment_set.find_notifications().as_df()

        Get all Breakdown notifications (M2) for the 'equipment_set' as a data frame::

            equipment_set.find_notifications(type = 'M2').as_df()
        """
        if len(self) == 0:
            raise RuntimeError('This EquipmentSet is empty, can not find notifications.')

        kwargs['equipment_id'] = [equipment.id for equipment in self.elements]
        return find_notifications(extended_filters, **kwargs)

    def find_workorders(self, extended_filters=(), **kwargs) -> WorkorderSet:
        """
        Find all Workorders for any of the equipments in this EquipmentSet.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Example
        -------
        Find all workorders for an equipment set 'my_equipment_set'::

            my_equipment_set.find_workorders()

        This method supports the common filter language explained at :ref:`filter`.
        """
        if len(self) == 0:
            raise RuntimeError('This EquipmentSet is empty, can not find workorders.')

        kwargs['equipment_id'] = [equipment.id for equipment in self.elements]
        return find_workorders(extended_filters, **kwargs)

    def find_common_indicators(self, extended_filters=(), **kwargs) -> IndicatorSet:
        """
        Find all Indicators common to all Equipments in this EquipmentSet.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Example
        -------
        Find all common indicators for an equipment set 'my_equipment_set'::

            my_equipment_set.find_common_indicators().as_df()


        Note
        ----
        If all the Equipments in the set are derived from the same EquipmentModel the overlap in
        Indicators is likely very high. If you get fewer indicators than expected from this method
        verify the uniformity of the Equipments included in this set.
        """
        if len(self) == 0:
            raise RuntimeError('This EquipmentSet is empty, can not find common indicators.')

        common_indicators = self.elements[0].find_equipment_indicators(extended_filters, **kwargs)
        for equipment in self.elements[1:]:
            equipment_indicators = equipment.find_equipment_indicators(extended_filters, **kwargs)
            common_indicators = IndicatorSet([indicator for indicator in common_indicators
                                              if indicator in equipment_indicators])

        return common_indicators


def find_equipments(extended_filters=(), **kwargs) -> EquipmentSet:
    """
    Fetch Equipments from AssetCentral with the applied filters, return an EquipmentSet.

    This method supports the common filter language explained at :ref:`filter`.

    Parameters
    ----------
    extended_filters
        See :ref:`filter`.
    **kwargs
        See :ref:`filter`.

    Examples
    --------
    Find all Equipments with the name 'MyEquipment'::

        find_equipments(name='MyEquipment')

    Find all Equipments which either have the name 'MyEquipment' or the name 'MyOtherEquipment'::

        find_equipments(name=['MyEquipment', 'MyOtherEquipment'])

    Find all Equipments with the name 'MyEquipment' which are also located in 'London'::

        find_equipments(name='MyEquipment', location_name='London')

    Find all Equipments installed between January 1, 2018 and January 1, 2019 in 'London'::

        find_equipments(extended_filters=['installationDate >= "2018-01-01"', 'installationDate < "2019-01-01"'],
                        location_name='London')
    """
    unbreakable_filters, breakable_filters = \
        parse_filter_parameters(kwargs, extended_filters, Equipment.get_property_mapping())

    endpoint_url = ac_application_url() + VIEW_EQUIPMENT
    object_list = fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return EquipmentSet([Equipment(obj) for obj in object_list],
                        {'filters': kwargs, 'extended_filters': extended_filters})
