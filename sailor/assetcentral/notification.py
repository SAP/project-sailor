"""
Retrieve Notification information from AssetCentral.

Classes are provided for individual Notifications as well as groups of Notifications (NotificationSet).
"""
import logging

import pandas as pd
import plotnine as p9

import sailor.assetcentral.equipment
from .constants import VIEW_NOTIFICATIONS
from .utils import (_fetch_data, ResultSet, _parse_filter_parameters,
                    AssetcentralEntity, _AssetcentralWriteRequest, AssetcentralFieldTemplate, _ac_application_url,
                    _add_properties_ft, _nested_put_setter)
from ..utils.oauth_wrapper import get_oauth_client
from ..utils.timestamps import _string_to_timestamp_parser_ft
from ..utils.plot_helper import _default_plot_theme

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())

_field_templates = [
    AssetcentralFieldTemplate('id', 'notificationId', 'notificationID'),
    AssetcentralFieldTemplate('notification_type', 'notificationType', 'type', is_mandatory=True),
    AssetcentralFieldTemplate('short_description', 'shortDescription', 'description', is_mandatory=True,
                              put_setter=_nested_put_setter('description', 'shortDescription')),
    AssetcentralFieldTemplate('priority', 'priority', 'priority', is_mandatory=True),
    AssetcentralFieldTemplate('status', 'status', 'status', is_mandatory=True,
                              put_setter=lambda p, v: p.update({'status': [v] if isinstance(v, str) else v})),
    AssetcentralFieldTemplate('equipment_id', 'equipmentId', 'equipmentID', is_mandatory=True),
    AssetcentralFieldTemplate('long_description', 'longDescription', 'description', is_mandatory=True,
                              put_setter=_nested_put_setter('description', 'longDescription')),
    AssetcentralFieldTemplate('breakdown', 'breakdown', 'breakdown', get_extractor=lambda v: bool(int(v))),
    AssetcentralFieldTemplate('cause_id', 'causeID', 'causeID'),
    AssetcentralFieldTemplate('cause_description', 'causeDesc'),
    AssetcentralFieldTemplate('cause_display_id', 'causeDisplayID'),
    AssetcentralFieldTemplate('effect_id', 'effectID', 'effectID'),
    AssetcentralFieldTemplate('effect_description', 'effectDesc'),
    AssetcentralFieldTemplate('effect_display_id', 'effectDisplayID'),
    AssetcentralFieldTemplate('instruction_id', 'instructionID', 'instructionID'),
    AssetcentralFieldTemplate('instruction_title', 'instructionTitle'),
    AssetcentralFieldTemplate('operator_id', 'operatorId', 'operator'),  # setting 'operator' has no effect
    AssetcentralFieldTemplate('confirmed_failure_mode_id', 'confirmedFailureModeID', 'confirmedFailureModeID'),
    AssetcentralFieldTemplate('confirmed_failure_mode_description', 'confirmedFailureModeDesc'),
    AssetcentralFieldTemplate('confirmed_failure_mode_name', 'confirmedFailureModeDisplayID'),
    AssetcentralFieldTemplate('end_date', 'endDate', 'endDate', get_extractor=_string_to_timestamp_parser_ft()),
    AssetcentralFieldTemplate('equipment_name', 'equipmentName'),
    AssetcentralFieldTemplate('functional_location_id', 'functionalLocationID', 'functionalLocationID'),
    AssetcentralFieldTemplate('location_id', 'locationId', 'locationID'),
    AssetcentralFieldTemplate('location_name', 'location'),
    AssetcentralFieldTemplate('malfunction_end_date', 'malfunctionEndDate', 'malfunctionEndDate',
                              get_extractor=_string_to_timestamp_parser_ft()),
    AssetcentralFieldTemplate('malfunction_start_date', 'malfunctionStartDate', 'malfunctionStartDate',
                              get_extractor=_string_to_timestamp_parser_ft()),
    AssetcentralFieldTemplate('model_id', 'modelId'),
    AssetcentralFieldTemplate('name', 'internalId'),
    AssetcentralFieldTemplate('notification_type_description', 'notificationTypeDescription'),
    AssetcentralFieldTemplate('priority_description', 'priorityDescription'),
    AssetcentralFieldTemplate('root_equipment_id', 'rootEquipmentId'),
    AssetcentralFieldTemplate('root_equipment_name', 'rootEquipmentName'),
    AssetcentralFieldTemplate('start_date', 'startDate', 'startDate',
                              get_extractor=_string_to_timestamp_parser_ft()),
    AssetcentralFieldTemplate('status_text', 'statusDescription'),
    AssetcentralFieldTemplate('system_failure_mode_id', 'systemProposedFailureModeID',
                              'systemProposedFailureModeID'),
    AssetcentralFieldTemplate('system_failure_mode_description', 'systemProposedFailureModeDesc'),
    AssetcentralFieldTemplate('system_failure_mode_name', 'systemProposedFailureModeDisplayID'),
    AssetcentralFieldTemplate('user_failure_mode_id', 'proposedFailureModeID', 'proposedFailureModeID'),
    AssetcentralFieldTemplate('user_failure_mode_description', 'proposedFailureModeDesc'),
    AssetcentralFieldTemplate('user_failure_mode_name', 'proposedFailureModeDisplayID'),
    AssetcentralFieldTemplate('isInternal', 'isInternal', is_exposed=False),
    AssetcentralFieldTemplate('createdBy', 'createdBy', is_exposed=False),
    AssetcentralFieldTemplate('creationDateTime', 'creationDateTime', is_exposed=False),
    AssetcentralFieldTemplate('lastChangedBy', 'lastChangedBy', is_exposed=False),
    AssetcentralFieldTemplate('lastChangeDateTime', 'lastChangeDateTime', is_exposed=False),
    AssetcentralFieldTemplate('progressStatus', 'progressStatus', is_exposed=False),
    AssetcentralFieldTemplate('progressStatusDescription', 'progressStatusDescription', is_exposed=False),
    AssetcentralFieldTemplate('coordinates', 'coordinates', is_exposed=False),
    AssetcentralFieldTemplate('source', 'source', is_exposed=False),
    AssetcentralFieldTemplate('assetCoreEquipmentId', 'assetCoreEquipmentId', is_exposed=False),
    AssetcentralFieldTemplate('operator', 'operator', is_exposed=False),
]


@_add_properties_ft
class Notification(AssetcentralEntity):
    """AssetCentral Notification Object."""

    _field_templates = _field_templates

    def update(self, **kwargs) -> 'Notification':
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
        updated_obj = update_notification(self, **kwargs)
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
        _parse_filter_parameters(kwargs, extended_filters, Notification._get_legacy_mapping())

    endpoint_url = _ac_application_url() + VIEW_NOTIFICATIONS
    object_list = _fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return NotificationSet([Notification(obj) for obj in object_list],
                           {'filters': kwargs, 'extended_filters': extended_filters})


def create_notification(**kwargs) -> Notification:
    """Create a new notification.

    Accepts a dictionary and keyword arguments.

    Examples
    --------
    >>> notf = create_notification({'equipment_id': '123', 'short_description': 'test'})
    >>> notf = create_notification(equipment_id='123', short_description='test')
    >>> notf = create_notification({'equipment_id': '123'}, short_description='test')
    """
    request = _AssetcentralWriteRequest(_field_templates, **kwargs)
    request.validate()
    endpoint_url = _ac_application_url() + VIEW_NOTIFICATIONS
    oauth_client = get_oauth_client('asset_central')

    response = oauth_client.request('POST', endpoint_url, json=request.data)
    result = find_notifications(id=response['notificationID'])
    if len(result) != 1:
        raise RuntimeError('Unexpected error when creating the notification. Please try again.')
    return result[0]


def update_notification(notification: Notification, **kwargs) -> Notification:
    """Update an existing notification.

    Write the current state of the given notification object to AssetCentral with updated values supplied.
    This equals a PUT request in the traditional REST programming model.

    Accepts a dict, key/value pairs and keyword arguments as input.

    Returns
    -------
    A new notification object as retrieved from AssetCentral after the update succeeded.

    Examples
    --------
    >>> notf = update_notification(notf, {'notification_type': 'M1', 'short_description': 'test'})
    >>> notf = update_notification(notf, notification_type='M1', short_description='test')
    >>> notf = update_notification(notf, {'notification_type': 'M1'}, short_description='test')
    """
    request = _AssetcentralWriteRequest.from_object(notification)
    request.update(**kwargs)
    request.validate()

    endpoint_url = _ac_application_url() + VIEW_NOTIFICATIONS
    oauth_client = get_oauth_client('asset_central')

    response = oauth_client.request('PUT', endpoint_url, json=request.data)
    result = find_notifications(id=response['notificationID'])
    if len(result) != 1:
        raise RuntimeError('Unexpected error when updating the notification. Please try again.')
    return result[0]
