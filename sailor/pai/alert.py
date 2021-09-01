"""
Retrieve Alert information from the alert re-use service.

Classes are provided for individual Alert as well as groups of Alerts (AlertSet).
"""

from sailor import _base
from ..assetcentral.utils import (_fetch_data, _parse_filter_parameters)
from ..utils.timestamps import _odata_to_timestamp_parser, _to_odata_datetimeoffset
from .constants import ALERTS_READ_PATH
from .utils import (PredictiveAssetInsightsEntity, _PredictiveAssetInsightsField,
                    PredictiveAssetInsightsEntitySet, _pai_application_url)

_ALERT_FIELDS = [
    _PredictiveAssetInsightsField('description', 'Description'),
    _PredictiveAssetInsightsField('severity_code', 'SeverityCode'),
    _PredictiveAssetInsightsField('category', 'Category'),
    _PredictiveAssetInsightsField('equipment_name', 'EquipmentName'),
    _PredictiveAssetInsightsField('model_name', 'ModelName'),
    _PredictiveAssetInsightsField('indicator_name', 'IndicatorName'),
    _PredictiveAssetInsightsField('indicator_group_name', 'IndicatorGroupName'),
    _PredictiveAssetInsightsField('template_name', 'TemplateName'),
    _PredictiveAssetInsightsField('count', 'Count'),
    _PredictiveAssetInsightsField('status_code', 'StatusCode'),
    _PredictiveAssetInsightsField('triggered_on', 'TriggeredOn', get_extractor=_odata_to_timestamp_parser(),
                                  query_transformer=_to_odata_datetimeoffset),
    _PredictiveAssetInsightsField('last_occured_on', 'LastOccuredOn', get_extractor=_odata_to_timestamp_parser(),
                                  query_transformer=_to_odata_datetimeoffset),
    _PredictiveAssetInsightsField('type_description', 'AlertTypeDescription'),
    _PredictiveAssetInsightsField('error_code_description', 'ErrorCodeDescription'),
    _PredictiveAssetInsightsField('type', 'AlertType'),
    _PredictiveAssetInsightsField('id', 'AlertId'),
    _PredictiveAssetInsightsField('equipment_id', 'EquipmentID'),
    _PredictiveAssetInsightsField('model_id', 'ModelID'),
    _PredictiveAssetInsightsField('template_id', 'TemplateID'),
    _PredictiveAssetInsightsField('indicator_id', 'IndicatorID'),
    _PredictiveAssetInsightsField('indicator_group_id', 'IndicatorGroupID'),
    _PredictiveAssetInsightsField('notification_id', 'NotificationId'),
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
                                  query_transformer=_to_odata_datetimeoffset),
    _PredictiveAssetInsightsField('_processor', 'Processor'),
    _PredictiveAssetInsightsField('_top_equipment_id', 'TopEquipmentID'),
    _PredictiveAssetInsightsField('_planning_plant', 'PlanningPlant'),
    _PredictiveAssetInsightsField('_error_code_id', 'ErrorCodeID'),
    _PredictiveAssetInsightsField('_operator_id', 'OperatorID'),
    _PredictiveAssetInsightsField('_source', 'Source'),
    _PredictiveAssetInsightsField('_top_equipment_name', 'TopEquipmentName'),
    _PredictiveAssetInsightsField('_created_on', 'CreatedOn', get_extractor=_odata_to_timestamp_parser(),
                                  query_transformer=_to_odata_datetimeoffset),
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


class AlertSet(PredictiveAssetInsightsEntitySet):
    """Class representing a group of Alerts."""

    _element_type = Alert
    _method_defaults = {
        'plot_distribution': {
            'by': 'type',
        },
    }


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
        _parse_filter_parameters(kwargs, extended_filters, Alert._field_map)

    endpoint_url = _pai_application_url() + ALERTS_READ_PATH
    objects = []
    object_list = _fetch_data(endpoint_url, unbreakable_filters, breakable_filters, 'predictive_asset_insights')
    for odata_result in object_list:
        for element in odata_result['d']['results']:
            objects.append(element)
    return AlertSet([Alert(obj) for obj in objects])
