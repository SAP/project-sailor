"""
Retrieve Notification information from AssetCentral.

Classes are provided for individual Notifications as well as groups of Notifications (NotificationSet).
"""

import warnings

import pandas as pd
import plotnine as p9

import sailor.assetcentral.equipment
from .constants import VIEW_NOTIFICATIONS
from .utils import (_AssetcentralRequestMapper, _fetch_data, ResultSet, _parse_filter_parameters,
                    AssetcentralEntity, _AssetcentralRequest, _ac_application_url, _add_properties_new)
from ..utils.oauth_wrapper import get_oauth_client
from ..utils.timestamps import _string_to_timestamp_parser
from ..utils.plot_helper import _default_plot_theme


class _NotificationRequestMapper(_AssetcentralRequestMapper):

    # Properties (in AC terminology) are: notificationId, shortDescription, status, statusDescription, notificationType,
    # notificationTypeDescription, priority, priorityDescription, isInternal, createdBy, creationDateTime,
    # lastChangedBy, lastChangeDateTime, longDescription, startDate, endDate, malfunctionStartDate, malfunctionEndDate,
    # progressStatus, progressStatusDescription, equipmentId, equipmentName, rootEquipmentId, rootEquipmentName,
    # locationId, breakdown, coordinates, source, operatorId, location, assetCoreEquipmentId, operator, internalId,
    # modelId, proposedFailureModeID, proposedFailureModeDisplayID, proposedFailureModeDesc, confirmedFailureModeID,
    # confirmedFailureModeDesc, confirmedFailureModeDisplayIDs, systemProposedFailureModeID,
    # systemProposedFailureModeDesc, systemProposedFailureModeDisplayID, effectID, effectDisplayID, effectDesc,
    # causeID, causeDisplayID, causeDesc, instructionID, instructionTitle

    _mapping = {
        # our: (their_get, get_function, their_put_or_requestsetter)
        'id': ('notificationId', None, 'notificationID'),
        'name': ('internalId', None, None),
        'short_description': ('shortDescription', None,
                              lambda r, v: r.data.setdefault('description', {}).update(shortDescription=v)),
        'long_description': ('longDescription', None,
                             lambda r, v: r.data.setdefault('description', {}).update(longDescription=v)),
        'breakdown': ('breakdown', None, 'breakdown'),  # TODO: turn into boolean? // setting 'breakdown' has no effect
        'cause_id': ('causeID', None, 'causeID'),
        'cause_description': ('causeDesc', None, None),
        'cause_display_id': ('causeDisplayID', None, None),
        'effect_id': ('effectID', None, 'effectID'),
        'effect_description': ('effectDesc', None, None),
        'effect_display_id': ('effectDisplayID', None, None),
        'instruction_id': ('instructionID', None, 'instructionID'),
        'instruction_title': ('instructionTitle', None, None),
        'operator_id': ('operatorId', None, 'operator'),  # setting 'operator' has no effect
        'confirmed_failure_mode_id': ('confirmedFailureModeID', None, 'confirmedFailureModeID'),
        'confirmed_failure_mode_description': ('confirmedFailureModeDesc', None, None),
        'confirmed_failure_mode_name': ('confirmedFailureModeDisplayID', None, None),
        'end_date': ('endDate', _string_to_timestamp_parser('endDate'), 'endDate'),
        'equipment_id': ('equipmentId', None, 'equipmentID'),
        'equipment_name': ('equipmentName', None, None),
        'functional_location_id': ('functionalLocationID', None, None),
        'location_id': ('locationId', None, 'locationID'),
        'location_name': ('location', None, None),
        'malfunction_end_date': ('malfunctionEndDate', _string_to_timestamp_parser('malfunctionEndDate'),
                                 'malfunctionEndDate'),
        'malfunction_start_date': ('malfunctionStartDate', _string_to_timestamp_parser('malfunctionStartDate'),
                                   'malfunctionStartDate'),
        'notification_type': ('notificationType', None, 'type'),
        'notification_type_description': ('notificationTypeDescription', None, None),
        'priority': ('priority', None, 'priority'),
        'priority_description': ('priorityDescription', None, None),
        'root_equipment_id': ('rootEquipmentId', None, None),
        'root_equipment_name': ('rootEquipmentName', None, None),
        'start_date': ('startDate', _string_to_timestamp_parser('startDate'), 'startDate'),
        'status': ('status', None,
                   lambda r, v: r.data.update({'status': [v] if isinstance(v, str) else v})),
        'status_text': ('statusDescription', None, None),
        'system_failure_mode_id': ('systemProposedFailureModeID', None, 'systemProposedFailureModeID'),
        'system_failure_mode_description': ('systemProposedFailureModeDesc', None, None),
        'system_failure_mode_name': ('systemProposedFailureModeDisplayID', None, None),
        'user_failure_mode_id': ('proposedFailureModeID', None, 'proposedFailureModeID'),
        'user_failure_mode_description': ('proposedFailureModeDesc', None, None),
        'user_failure_mode_name': ('proposedFailureModeDisplayID', None, None),
        }

    _keys_safe_to_remove = [
        'isInternal', 'createdBy', 'creationDateTime', 'lastChangedBy', 'lastChangeDateTime',
        'progressStatus', 'progressStatusDescription', 'coordinates', 'source', 'assetCoreEquipmentId', 'operator',
        'modelId']


class _NotificationRequest(_AssetcentralRequest, _NotificationRequestMapper):
    pass


@_add_properties_new
class Notification(AssetcentralEntity, _NotificationRequestMapper):
    """AssetCentral Notification Object."""

    @classmethod
    def get_property_mapping(cls):
        """Return a mapping from assetcentral terminology to our terminology."""
        # TODO: remove method in future version
        warnings.warn("get_property_mapping: deprecated - use 'get_available_properties' instead", FutureWarning)
        return cls._mapping

    def update(self, *args, **kwargs) -> 'Notification':
        """Write the current state of this object to AssetCentral with updated values supplied.

        After the successful update in the remote system this object reflects the updated state.

        Example
        -------
        .. code-block::

            notf2 = notf.update(notification_type='M1')
            assert notf.notification_type == 'M1'
            assert notf2 == notf

        See Also
        --------
        :meth:`update_notification`
        """
        updated_obj = update_notification(self, *args, **kwargs)
        self.raw = updated_obj.raw
        return self

    def plot_context(self, data=None, window_before=pd.Timedelta(days=7), window_after=pd.Timedelta(days=2)):
        """
        Plot a notification in the context of the timeseries data around the time of the notification.

        This plot can be used to gain insight into the sensor behaviour around the time that a malfunction occurs.
        If the `data` parameter is left as `None` the data required for plotting is automatically retrieved from
        SAP IoT.

        Parameters
        ----------
        data
            TimeseriesDataset to use for plotting indicator data near the Notification.
        window_before
            Time interval plotted before a notification. Default value is 7 days before a notification
        window_after
            Time interval plotted after a notification. Default value is 2 days after a notification
        """
        equipment_set = sailor.assetcentral.equipment.find_equipment(id=self.equipment_id)

        if self.start_date and self.end_date:
            data_start = self.start_date - window_before
            area_start = max(data_start, self.start_date)
            data_end = self.end_date + window_after
            area_end = min(data_end, self.end_date)
        elif self.start_date:
            data_start = self.start_date - window_before
            area_start = max(data_start, self.start_date)
            data_end = self.start_date + window_after
            area_end = data_end
        elif self.end_date:
            data_start = self.end_date - window_before
            area_start = data_start
            data_end = self.end_date + window_after
            area_end = min(data_end, self.end_date)
        else:
            raise RuntimeError('Either notification start_date or notification end_date must be known to plot context.')

        if data is None:
            data = equipment_set.get_indicator_data(data_start, data_end)

        plot = (
                data.plot(data_start, data_end, equipment_set=equipment_set) +
                p9.annotate('vline', xintercept=[self.start_date, self.end_date], size=2, linetype='dotted') +
                p9.annotate('rect', xmin=area_start, xmax=area_end,
                            ymin=-float('inf'), ymax=float('inf'), alpha=0.2)
        )
        return plot


class NotificationSet(ResultSet):
    """Class representing a group of Notifications."""

    _element_type = Notification
    _method_defaults = {
        'plot_distribution': {
            'by': 'equipment_name',
        },
    }

    def plot_overview(self):
        """
        Plot an overview over all notifications in the set as a function of time.

        Each notification will be shown by a rectangle, on a y-scale representing the affected equipment
        and with a color representing the confirmed failure mode description.

        Example
        -------
        Plot an overview over all notifications in the dataset "my_notifications" by time::

            my_notifications.plot_overview()
        """
        data = self.as_df(columns=['malfunction_start_date', 'malfunction_end_date',
                                   'equipment_name', 'confirmed_failure_mode_description'])

        aes = {
            'x': 'malfunction_start_date', 'xend': 'malfunction_end_date',
            'y': 'equipment_name', 'yend': 'equipment_name',
            'color': 'confirmed_failure_mode_description',
        }

        plot = p9.ggplot(data, p9.aes(**aes))
        plot += p9.geom_segment(size=6, alpha=0.7)
        plot += _default_plot_theme()

        return plot


def find_notifications(*, extended_filters=(), **kwargs) -> NotificationSet:
    """Fetch Notifications from AssetCentral with the applied filters, return a NotificationSet.

    This method supports the common filter language explained at :ref:`filter`.

    **Allowed entries for filter terms**

        Type of notifications and its meanings
            M1: Maintenance Request, M2: BreakDown

        Priorities and its meanings
            5: Low, 10: Medium, 15: High, 20:  Very High, 25: Emergency

        Status types and its meanings
            NEW: New, PBD: Published, CPT: Completed, IPR: InProcess

    Parameters
    ----------
    extended_filters
        See :ref:`filter`.
    **kwargs
        See :ref:`filter`.

    Examples
    --------
    Find all notifications with short_description 'MyNotification'::

        find_notifications(short_description='MyNotification')

    Find all notifications which either have the short_description 'MyNotification' or the short_description
    'MyOtherNotification'::

        find_notifications(short_description=['MyNotification', 'MyOtherNotification'])

    Find all notifications with short_description 'MyNotification' which also have the start date '2020-07-01'::

        find_notifications(short_description='MyNotification', start_date='2020-07-01')

    Find all notifications with a confirmed failure mode description is not empty::

        find_notifications(extended_filters=['confirmed_failure_mode_description != "None"'])

    Find all notifications in a given timeframe for specific equipment::

        find_notifications(extended_filters=['malfunctionStartDate > "2020-08-01"',
                                             'malfunctionEndDate <= "2020-09-01"'],
                           equipment_id=['id1', 'id2'])
    """
    unbreakable_filters, breakable_filters = \
        _parse_filter_parameters(kwargs, extended_filters, _NotificationRequestMapper._mapping)

    endpoint_url = _ac_application_url() + VIEW_NOTIFICATIONS
    object_list = _fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return NotificationSet([Notification(obj) for obj in object_list],
                           {'filters': kwargs, 'extended_filters': extended_filters})


def create_notification(*args, **kwargs) -> Notification:
    """Create a new notification.

    Accepts a dictionary and keyword arguments.

    Examples
    --------
    >>> notf = create_notification({'equipment_id': '123', 'short_description': 'test'})
    >>> notf = create_notification(equipment_id='123', short_description='test')
    >>> notf = create_notification({'equipment_id': '123'}, short_description='test')
    """
    request = _NotificationRequest(*args, **kwargs)
    endpoint_url = _ac_application_url() + VIEW_NOTIFICATIONS
    oauth_client = get_oauth_client('asset_central')

    response = oauth_client.request('POST', endpoint_url, json=request.data)
    notification = find_notifications(id=response['notificationID'])[0]
    return notification


def update_notification(notification: Notification, *args, **kwargs) -> Notification:
    """Update an existing notification.

    Write the current state of the given notification object to AssetCentral with updated values supplied.
    This equals a PUT request in the traditional REST programming model.

    Accepts a dict, key/value pairs and keyword arguments as input.

    Returns
    -------
    Notification
        A new notification object as retrieved from AssetCentral after the update succeeded.

    Examples
    --------
    >>> notf = update_notification(notf, {'notification_type': 'M1', 'short_description': 'test'})
    >>> notf = update_notification(notf, notification_type='M1', short_description='test')
    >>> notf = update_notification(notf, {'notification_type': 'M1'}, short_description='test')
    """
    request = _NotificationRequest.from_object(notification)
    request.update(*args, **kwargs)

    endpoint_url = _ac_application_url() + VIEW_NOTIFICATIONS
    oauth_client = get_oauth_client('asset_central')

    response = oauth_client.request('PUT', endpoint_url, json=request.data)
    notification = find_notifications(id=response['notificationID'])[0]
    return notification
