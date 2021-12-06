"""
Retrieve Alert information from the alert re-use service.

Classes are provided for individual Alert as well as groups of Alerts (AlertSet).
"""

from functools import lru_cache
from typing import Iterable
import re

import plotnine as p9

import sailor.assetcentral.utils as ac_utils
from sailor import _base
from sailor.utils.oauth_wrapper import get_oauth_client
from sailor.utils.timestamps import _odata_to_timestamp_parser, _any_to_timestamp, _timestamp_to_isoformat
from sailor._base.masterdata import _qt_odata_datetimeoffset, _qt_double
from .constants import ALERTS_READ_PATH, ALERTS_WRITE_PATH
from .utils import (PredictiveAssetInsightsEntity, _PredictiveAssetInsightsField,
                    PredictiveAssetInsightsEntitySet, _pai_application_url, _pai_fetch_data)
from ..utils.plot_helper import _default_plot_theme

_ALERT_FIELDS = [
    _PredictiveAssetInsightsField('triggered_on', 'TriggeredOn', 'triggeredOn', is_mandatory=True,
                                  get_extractor=_odata_to_timestamp_parser(),
                                  put_setter=lambda p, v: p.update({'triggeredOn': _timestamp_to_isoformat(
                                                                    _any_to_timestamp(v), with_zulu=True)}),
                                  query_transformer=_qt_odata_datetimeoffset),
    _PredictiveAssetInsightsField('last_occured_on', 'LastOccuredOn', get_extractor=_odata_to_timestamp_parser(),
                                  query_transformer=_qt_odata_datetimeoffset),
    _PredictiveAssetInsightsField('count', 'Count', query_transformer=_qt_double),
    _PredictiveAssetInsightsField('type', 'AlertType', 'alertType', is_mandatory=True),
    _PredictiveAssetInsightsField('category', 'Category'),
    _PredictiveAssetInsightsField('severity_code', 'SeverityCode', 'severityCode', is_mandatory=True,
                                  query_transformer=_qt_double),
    _PredictiveAssetInsightsField('equipment_name', 'EquipmentName'),
    _PredictiveAssetInsightsField('model_name', 'ModelName'),
    _PredictiveAssetInsightsField('indicator_name', 'IndicatorName'),
    _PredictiveAssetInsightsField('indicator_group_name', 'IndicatorGroupName'),
    _PredictiveAssetInsightsField('template_name', 'TemplateName'),
    _PredictiveAssetInsightsField('status_code', 'StatusCode', query_transformer=_qt_double),
    _PredictiveAssetInsightsField('type_description', 'AlertTypeDescription'),
    _PredictiveAssetInsightsField('error_code_description', 'ErrorCodeDescription'),
    _PredictiveAssetInsightsField('source', 'Source', 'source'),
    _PredictiveAssetInsightsField('description', 'Description', 'description'),
    _PredictiveAssetInsightsField('id', 'AlertId'),
    _PredictiveAssetInsightsField('equipment_id', 'EquipmentID', 'equipmentId', is_mandatory=True),
    _PredictiveAssetInsightsField('model_id', 'ModelID'),
    _PredictiveAssetInsightsField('template_id', 'TemplateID', 'templateId'),
    _PredictiveAssetInsightsField('indicator_id', 'IndicatorID', 'indicatorId'),
    _PredictiveAssetInsightsField('indicator_group_id', 'IndicatorGroupID', 'indicatorGroupId'),
    _PredictiveAssetInsightsField('notification_id', 'NotificationId'),
    _PredictiveAssetInsightsField('error_code_id', 'ErrorCodeID', 'errorCodeId'),
    _PredictiveAssetInsightsField('_indicator_description', 'IndicatorDescription'),
    _PredictiveAssetInsightsField('_country_id', 'CountryID'),
    _PredictiveAssetInsightsField('_functional_location_id', 'FunctionalLocationID'),
    _PredictiveAssetInsightsField('_maintenance_plant', 'MaintenancePlant'),
    _PredictiveAssetInsightsField('_functional_location_description', 'FunctionalLocationDescription'),
    _PredictiveAssetInsightsField('_top_functional_location_name', 'TopFunctionalLocationName'),
    _PredictiveAssetInsightsField('_planner_group', 'PlannerGroup'),
    _PredictiveAssetInsightsField('_ref_alert_type_id', 'RefAlertTypeId'),
    _PredictiveAssetInsightsField('_operator_name', 'OperatorName'),
    _PredictiveAssetInsightsField('_created_by', 'CreatedBy'),
    _PredictiveAssetInsightsField('_changed_by', 'ChangedBy'),
    _PredictiveAssetInsightsField('_serial_number', 'SerialNumber'),
    _PredictiveAssetInsightsField('_changed_on', 'ChangedOn', get_extractor=_odata_to_timestamp_parser(),
                                  query_transformer=_qt_odata_datetimeoffset),
    _PredictiveAssetInsightsField('_processor', 'Processor'),
    _PredictiveAssetInsightsField('_top_equipment_id', 'TopEquipmentID'),
    _PredictiveAssetInsightsField('_planning_plant', 'PlanningPlant'),
    _PredictiveAssetInsightsField('_operator_id', 'OperatorID'),
    _PredictiveAssetInsightsField('_top_equipment_name', 'TopEquipmentName'),
    _PredictiveAssetInsightsField('_created_on', 'CreatedOn', get_extractor=_odata_to_timestamp_parser(),
                                  query_transformer=_qt_odata_datetimeoffset),
    _PredictiveAssetInsightsField('_model_description', 'ModelDescription'),
    _PredictiveAssetInsightsField('_top_equipment_description', 'TopEquipmentDescription'),
    _PredictiveAssetInsightsField('_functional_location_name', 'FunctionalLocationName'),
    _PredictiveAssetInsightsField('_top_functional_location_description', 'TopFunctionalLocationDescription'),
    _PredictiveAssetInsightsField('_top_functional_location_id', 'TopFunctionalLocationID'),
    _PredictiveAssetInsightsField('_equipment_description', 'EquipmentDescription'),
]


@_base.add_properties
class Alert(PredictiveAssetInsightsEntity):
    """PredictiveAssetInsights Alert Object."""

    _field_map = {field.our_name: field for field in _ALERT_FIELDS}

    def __init__(self, ac_json: dict):
        super().__init__(ac_json)
        for key, value in self._custom_properties.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        """Return a very short string representation."""
        descr = getattr(self, 'description', None)
        return f'{self.__class__.__name__}(description="{descr}", id="{self.id}")'

    @property
    @lru_cache(maxsize=None)
    def _custom_properties(self):
        # the Alerts Extension API supports creating custom fields which must start with Z_ or z_
        return {key: value for key, value in self.raw.items()
                if key.startswith('Z_') or key.startswith('z_')}


class AlertSet(PredictiveAssetInsightsEntitySet):
    """Class representing a group of Alerts."""

    _element_type = Alert
    _method_defaults = {
        'plot_distribution': {
            'by': 'type',
        },
    }

    def as_df(self, columns: Iterable[str] = None, include_all_custom_properties=False):
        """Return all information on the objects stored in the AlertSet as a pandas dataframe.

        Parameters
        ----------
        columns
            Select the columns (and their order) for the DataFrame.
        include_all_custom_properties
            If True, adds ALL custom properties attached to the alerts to the resulting DataFrame.
            This can only be used when all alerts in the AlertSet are of the same type.
        """
        if columns is None:
            columns = [field.our_name for field in self._element_type._field_map.values() if field.is_exposed]

        if len(self) > 0 and include_all_custom_properties:
            alert_types = super().as_df(columns=['type'])['type']
            if alert_types.nunique() > 1:
                raise RuntimeError('Cannot include custom properties: More than one alert type present in result.')
            # to preserve order a dict is used instead of a set
            columns = dict.fromkeys(columns)
            custom_columns = dict.fromkeys(self[0]._custom_properties.keys())
            columns.update(custom_columns)

        return super().as_df(columns=list(columns))

    def plot_overview(self):
        """
        Plot an overview over all alerts in the set as a function of time.

        Each alert will be shown by a point, on a y-scale representing the affected equipment
        and with a color representing the alert type. The size of the point is given by the ``count`` value.
        This value represents how many times the alert has occurred in the deduplication window specified by the
        alert type.

        Example
        -------
        Plot an overview over all alerts in the dataset "alert_set" by time::

            alert_set.plot_overview()
        """
        data = self.as_df(columns=['last_occured_on', 'equipment_name', 'type', 'count'])

        # if there are any `NA` values in the equipment_name the plot gets messed up.
        # this turns the NAs into an 'nan' string, which works fine.
        data['equipment_name'] = data['equipment_name'].astype(str)

        aes = {
            'x': 'last_occured_on',
            'y': 'equipment_name',
            'color': 'type',
        }

        plot = p9.ggplot(data, p9.aes(**aes))
        plot += p9.geom_point(p9.aes(size='count'))
        plot += _default_plot_theme()

        return plot


def find_alerts(*, extended_filters=(), **kwargs) -> AlertSet:
    """
    Fetch Alerts from PredictiveAssetInsights (PAI) with the applied filters, return an AlertSet.

    This method supports the common filter language explained at :ref:`filter`.

    Parameters
    ----------
    extended_filters
        See :ref:`filter`.
    **kwargs
        See :ref:`filter`.

    Examples
    --------
    Get all Alerts with the type 'MyAlertType'::

        find_alerts(type='MyAlertType')

    Get all Error(severity code=10) and Information(severity code=1) alerts::

        find_equipment(severity_code=[10, 1])
    """
    unbreakable_filters, breakable_filters = \
        _base.parse_filter_parameters(kwargs, extended_filters, Alert._field_map)

    endpoint_url = _pai_application_url() + ALERTS_READ_PATH
    object_list = _pai_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return AlertSet([Alert(obj) for obj in object_list])


def create_alert(**kwargs) -> Alert:
    """Create a new alert in the remote system.

    Alerts are immutable. If the specified alert type uses a deduplication period,
    the remote system will not create a new alert but **ONLY** increase the counter for an existing alert
    on the same equipment within the deduplication period. This means (1) additional properties supplied are
    discarded and (2) this function will return the existing alert object as a response.

    Parameters
    ----------
    **kwargs
        Keyword arguments which names correspond to the available properties.
        Can also be used to supply custom fields (Z_*, z_*) used with the corresponding alert type: in this case the
        type of the field is not known to Sailor and therefore the value must be strictly given in the format defined by
        the type as defined by the remote API.

    Returns
    -------
    Alert
        A new alert object as retrieved from PAI after the create succeeded.

    Example
    -------
    >>> alert = create_alert(equipment_id='123', triggered_on='2020-07-31T13:23:00Z',
    ...                      type='PUMP_TEMP_WARN', severity_code=5, indicator_id='ic1',
    ...                      indicator_group_id='ig1', template_id='t1')
    """
    request = _AlertWriteRequest()
    request.insert_user_input(kwargs, forbidden_fields=['id'])
    return _create_alert(request)


def _create_alert(request) -> Alert:
    request.validate()
    endpoint_url = ac_utils._ac_application_url() + ALERTS_WRITE_PATH
    oauth_client = get_oauth_client('asset_central')

    response = oauth_client.request('POST', endpoint_url, json=request.data)
    alert_id = re.search(
                r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}',
                response.decode('utf-8')).group()

    result = find_alerts(id=alert_id)
    if len(result) != 1:
        raise RuntimeError('Unexpected error when creating the alert. Please try again.')
    return result[0]


class _AlertWriteRequest(ac_utils._AssetcentralWriteRequest):

    ADD_WRITE_PARAMS = {
        'custom_properties': _PredictiveAssetInsightsField('custom_properties', None, 'custom_properties')
    }

    def __init__(self, *args, **kwargs):
        super().__init__({**Alert._field_map, **self.ADD_WRITE_PARAMS}, *args, **kwargs)

    def insert_user_input(self, input_dict: dict, forbidden_fields=()):
        custom_properties = {key: input_dict.pop(key) for key in list(input_dict.keys())
                             if key.startswith('Z_') or key.startswith('z_')}
        if custom_properties:
            input_dict['custom_properties'] = custom_properties
        return super().insert_user_input(input_dict, forbidden_fields=forbidden_fields)
