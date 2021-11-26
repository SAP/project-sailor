"""
Retrieve Equipment information from AssetCentral.

Classes are provided for individual Equipment as well as groups of Equipment (EquipmentSet).
"""
from __future__ import annotations

from typing import Union, TYPE_CHECKING, Iterable
from datetime import datetime, timedelta

import pandas as pd

from sailor import _base
from sailor import pai
from sailor import sap_iot
from ..utils.timestamps import _string_to_timestamp_parser
from .constants import VIEW_EQUIPMENT, VIEW_OBJECTS
from .failure_mode import find_failure_modes
from .indicators import Indicator, IndicatorSet
from .notification import Notification, find_notifications, _create_or_update_notification
from .location import Location, find_locations
from .workorder import find_workorders
from .utils import (AssetcentralEntity, _AssetcentralField, _AssetcentralWriteRequest, AssetcentralEntitySet,
                    _ac_application_url, _ac_fetch_data)

if TYPE_CHECKING:
    from .notification import NotificationSet
    from .failure_mode import FailureModeSet
    from .workorder import WorkorderSet
    from ..sap_iot import TimeseriesDataset

_EQUIPMENT_FIELDS = [
    _AssetcentralField('name', 'internalId'),  # there is also a native `name`, which we're ignoring
    _AssetcentralField('model_name', 'modelName'),
    _AssetcentralField('location_name', 'location'),
    _AssetcentralField('status_text', 'statusDescription',
                       query_transformer=_base.masterdata._qt_non_filterable('status_text')),
    _AssetcentralField('short_description', 'shortDescription'),
    _AssetcentralField('manufacturer', 'manufacturer'),
    _AssetcentralField('operator', 'operator'),
    _AssetcentralField('installation_date', 'installationDate', get_extractor=_string_to_timestamp_parser('ms'),
                       query_transformer=_base.masterdata._qt_timestamp),
    _AssetcentralField('build_date', 'buildDate', get_extractor=_string_to_timestamp_parser('ms'),
                       query_transformer=_base.masterdata._qt_timestamp),
    _AssetcentralField('criticality_description', 'criticalityDescription'),
    _AssetcentralField('id', 'equipmentId'),
    _AssetcentralField('model_id', 'modelId'),
    _AssetcentralField('template_id', 'templateId'),
    _AssetcentralField('serial_number', 'serialNumber'),
    _AssetcentralField('batch_number', 'batchNumber'),
    _AssetcentralField('_tag_number', 'tagNumber'),
    _AssetcentralField('_lifecycle', 'lifeCycle'),
    _AssetcentralField('_lifecycle_description', 'lifeCycleDescription'),
    _AssetcentralField('_source', 'source'),
    _AssetcentralField('_status', 'status'),
    _AssetcentralField('_version', 'version'),
    _AssetcentralField('_in_revision', 'hasInRevision'),
    _AssetcentralField('_subclass', 'subclass'),
    _AssetcentralField('_model_template', 'modelTemplate'),
    _AssetcentralField('_criticality_code', 'criticalityCode'),
    _AssetcentralField('_completeness', 'completeness', query_transformer=_base.masterdata._qt_double),
    _AssetcentralField('_created_on', 'createdOn'),
    _AssetcentralField('_changed_on', 'changedOn'),
    _AssetcentralField('_published_on', 'publishedOn'),
    _AssetcentralField('_image_URL', 'imageURL'),
    _AssetcentralField('_coordinates', 'coordinates'),
    _AssetcentralField('_equipment_status', 'equipmentStatus'),
    _AssetcentralField('_is_operator_valid', 'isOperatorValid'),
    _AssetcentralField('_model_version', 'modelVersion'),
    _AssetcentralField('_sold_to', 'soldTo'),
    _AssetcentralField('_image', 'image'),
    _AssetcentralField('_consume', 'consume'),
    _AssetcentralField('_dealer', 'dealer'),
    _AssetcentralField('_service_provider', 'serviceProvider'),
    _AssetcentralField('_primary_external_id', 'primaryExternalId'),
    _AssetcentralField('_equipment_search_terms', 'equipmentSearchTerms'),
    _AssetcentralField('_source_search_terms', 'sourceSearchTerms'),
    _AssetcentralField('_manufacturer_search_terms', 'manufacturerSearchTerms'),
    _AssetcentralField('_operator_search_terms', 'operatorSearchTerms'),
    _AssetcentralField('_class', 'class'),
]


@_base.add_properties
class Equipment(AssetcentralEntity):
    """AssetCentral Equipment Object."""

    _field_map = {field.our_name: field for field in _EQUIPMENT_FIELDS}
    _location = None

    @property
    def location(self) -> Location:
        """Return the Location associated with this Equipment."""
        if self._location is None and self.location_name is not None:
            locations = find_locations(name=self.location_name)  # why do we have a name here, not an ID???
            assert len(locations) == 1
            self._location = locations[0]
        return self._location

    def find_equipment_indicators(self, *, extended_filters=(), **kwargs) -> IndicatorSet:
        """Find all Indicators assigned to this Equipment.

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
        endpoint_url = _ac_application_url() + VIEW_EQUIPMENT + f'({self.id})' + '/indicatorvalues'
        object_list = _ac_fetch_data(endpoint_url)

        filtered_objects = _base.apply_filters_post_request(object_list, kwargs, extended_filters,
                                                            Indicator._field_map)
        return IndicatorSet([Indicator(obj) for obj in filtered_objects])

    def find_notifications(self, *, extended_filters=(), **kwargs) -> NotificationSet:
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
        return find_notifications(extended_filters=extended_filters, **kwargs)

    def find_failure_modes(self, *, extended_filters=(), **kwargs) -> FailureModeSet:
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
        endpoint_url = _ac_application_url() + VIEW_OBJECTS + 'EQU/' + self.id + '/failuremodes'
        object_list = _ac_fetch_data(endpoint_url)
        kwargs['id'] = [element['ID'] for element in object_list]
        return find_failure_modes(extended_filters=extended_filters, **kwargs)

    def find_workorders(self, *, extended_filters=(), **kwargs) -> WorkorderSet:
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

        Examples
        --------
        Find all workorders for equipment object 'my_equipment'::

            my_equipment.find_workorders()
        """
        kwargs['equipment_id'] = self.id
        return find_workorders(extended_filters=extended_filters, **kwargs)

    def get_indicator_data(self, start: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                           end: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                           indicator_set: IndicatorSet = None) -> TimeseriesDataset:
        """
        Fetch timeseries data from SAP Internet of Things for Indicators attached to this equipment.

        This is a wrapper for :meth:`sailor.sap_iot.fetch.get_indicator_data` that limits the fetch query
        to this equipment. Note that filtering for the equipment can only be done locally, so calling this function
        repeatedly for different equipment with the same indicators can be very inefficient.

        Parameters
        ----------
        start
            Date of beginning of requested timeseries data. Any time component will be ignored.
        end
            Date of end of requested timeseries data. Any time component will be ignored
        indicator_set
            IndicatorSet for which timeseries data is returned.

        Example
        -------
        Get indicator data for an equipment 'my_equipment' for a period from 01.06.2020 to 05.12.2020 ::
            my_equipment = find_equipment(name='my_equipment')[0]
            my_equipment.get_indicator_data('2020-06-01', '2020-12-05')

        Note
        ----
        If `indicator_set` is not specified, all indicators associated to this equipment are used.
        """
        if indicator_set is None:
            indicator_set = self.find_equipment_indicators()

        return sap_iot.get_indicator_data(start, end, indicator_set, EquipmentSet([self]))

    def create_notification(self, **kwargs) -> Notification:
        """Create a new notification for this equipment.

        See Also
        --------
        :meth:`sailor.assetcentral.notification.create_notification`
        """
        fixed_kwargs = {'equipment_id': self.id}
        if self.location is not None:
            fixed_kwargs['location_id'] = self.location.id
        request = _AssetcentralWriteRequest(Notification._field_map, **fixed_kwargs)
        request.insert_user_input(kwargs, forbidden_fields=['id', 'equipment_id'])
        return _create_or_update_notification(request, 'POST')

    def create_alert(self, **kwargs) -> pai.alert.Alert:
        """Create a new alert for this equipment.

        See Also
        --------
        :meth:`sailor.pai.alert.create_alert`
        """
        fixed_kwargs = {'equipment_id': self.id}
        request = pai.alert._AlertWriteRequest(**fixed_kwargs)
        request.insert_user_input(kwargs, forbidden_fields=['id', 'equipment_id'])
        return pai.alert._create_alert(request)


class EquipmentSet(AssetcentralEntitySet):
    """Class representing a group of Equipment."""

    _element_type = Equipment
    _method_defaults = {
        'plot_distribution': {
            'by': 'location_name',
        },
    }

    def find_notifications(self, *, extended_filters=(), **kwargs) -> NotificationSet:
        """Find all Notifications for any of the equipment in this EquipmentSet.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Examples
        --------
        Get all notifications for the 'equipment_set' as a data frame::

            equipment_set = find_equipment()

            equipment_set.find_notifications().as_df()

        Get all Breakdown notifications (M2) for the 'equipment_set' as a data frame::

            equipment_set.find_notifications(type = 'M2').as_df()
        """
        if len(self) == 0:
            raise RuntimeError('This EquipmentSet is empty, can not find notifications.')

        kwargs['equipment_id'] = [equipment.id for equipment in self.elements]
        return find_notifications(extended_filters=extended_filters, **kwargs)

    def find_workorders(self, *, extended_filters=(), **kwargs) -> WorkorderSet:
        """
        Find all Workorders for any of the equipment in this EquipmentSet.

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
        return find_workorders(extended_filters=extended_filters, **kwargs)

    def find_common_indicators(self, *, extended_filters=(), **kwargs) -> IndicatorSet:
        """
        Find all Indicators common to all Equipment in this EquipmentSet.

        This method supports the common filter language explained at :ref:`filter`.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Example
        -------
        Find all common indicators for an EquipmentSet 'my_equipment_set'::

            my_equipment_set.find_common_indicators().as_df()


        Note
        ----
        If all the Equipment in the set are derived from the same Model the overlap in
        Indicators is likely very high. If you get fewer indicators than expected from this method
        verify the uniformity of the Equipment included in this set.
        """
        if len(self) == 0:
            raise RuntimeError('This EquipmentSet is empty, can not find common indicators.')

        common_indicators = self.elements[0].find_equipment_indicators(extended_filters=extended_filters, **kwargs)
        for equipment in self.elements[1:]:
            equipment_indicators = equipment.find_equipment_indicators(extended_filters=extended_filters, **kwargs)
            common_indicators = IndicatorSet([indicator for indicator in common_indicators
                                              if indicator in equipment_indicators])

        return common_indicators

    def get_indicator_data(self, start: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                           end: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                           indicator_set: IndicatorSet = None) -> TimeseriesDataset:
        """
        Fetch timeseries data from SAP Internet of Things for Indicators attached to all equipments in this set.

        This is a wrapper for :meth:`sailor.sap_iot.fetch.get_indicator_data` that limits the fetch query
        to this equipment set.

        Parameters
        ----------
        start
            Date of beginning of requested timeseries data. Any time component will be ignored.
        end
            Date of end of requested timeseries data. Any time component will be ignored.
        indicator_set
            IndicatorSet for which timeseries data is returned.

        Example
        -------
        Get indicator data for all Equipment belonging to the Model 'MyModel'
        for a period from 01.06.2020 to 05.12.2020 ::

            my_equipment_set = find_equipment(model_name='MyModel')
            my_equipment_set.get_indicator_data('2020-06-01', '2020-12-05')
        Note
        ----
        If `indicator_set` is not specified, indicators common to all equipments in this set are used.
        """
        if indicator_set is None:
            indicator_set = self.find_common_indicators()

        return sap_iot.get_indicator_data(start, end, indicator_set, self)

    def get_indicator_aggregates(
            self, start: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
            end: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
            indicator_set: IndicatorSet = None,
            aggregation_functions: Iterable[str] = ('AVG',),
            aggregation_interval: Union[str, pd.Timedelta, timedelta] = 'PT2M'
    ) -> TimeseriesDataset:
        """
        Fetch timeseries data from SAP Internet of Things for Indicators attached to all equipments in this set.

        This is a wrapper for :meth:`sailor.sap_iot.fetch_aggregates.get_indicator_aggregates` that limits the fetch
        query to this equipment set. Unlike :meth:`sailor.assetcentral.equipment.Equipment.get_indicator_data` this
        function retrieves pre-aggregated data from the hot store.

        Parameters
        ----------
        start
            Date of beginning of requested timeseries data.
        end
            Date of end of requested timeseries data.
        indicator_set
            IndicatorSet for which timeseries data is returned. Defaults to indicators common to all equipment in this
            equipment set.
        aggregation_functions: Determines which aggregates to retrieve. Possible aggregates are
            'MIN', 'MAX', 'AVG', 'STDDEV', 'SUM', 'FIRST', 'LAST',
            'COUNT', 'PERCENT_GOOD', 'TMIN', 'TMAX',  'TFIRST', 'TLAST'
        aggregation_interval: Determines the aggregation interval. Can be specified as an ISO 8601 string
            (like `PT2M` for 2-minute aggregates) or as a pandas.Timedelta or datetime.timedelta object.

        Example
        -------
        Get indicator data for all Equipment belonging to the Model 'MyModel'
        for a period from 01.06.2020 to 05.12.2020 ::

            my_equipment_set = find_equipment(model_name='MyModel')
            my_equipment_set.get_indicator_aggregates('2020-06-01', '2020-12-05', aggregation_functions=['MIN'])
        """
        if indicator_set is None:
            indicator_set = self.find_common_indicators()

        return sap_iot.get_indicator_aggregates(start, end, indicator_set, self,
                                                aggregation_functions, aggregation_interval)


def find_equipment(*, extended_filters=(), **kwargs) -> EquipmentSet:
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
    Find all Equipment with the name 'MyEquipment'::

        find_equipment(name='MyEquipment')

    Find all Equipment which either have the name 'MyEquipment' or the name 'MyOtherEquipment'::

        find_equipment(name=['MyEquipment', 'MyOtherEquipment'])

    Find all Equipment with the name 'MyEquipment' which are also located in 'London'::

        find_equipment(name='MyEquipment', location_name='London')

    Find all Equipment installed between January 1, 2018 and January 1, 2019 in 'London'::

        find_equipment(extended_filters=['installationDate >= "2018-01-01"', 'installationDate < "2019-01-01"'],
                        location_name='London')
    """
    unbreakable_filters, breakable_filters = \
        _base.parse_filter_parameters(kwargs, extended_filters, Equipment._field_map)

    endpoint_url = _ac_application_url() + VIEW_EQUIPMENT
    object_list = _ac_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return EquipmentSet([Equipment(obj) for obj in object_list])
