"""
Retrieve Alert information from the alert re-use service.

Classes are provided for individual Alert as well as groups of Alerts (AlertSet).
"""


from .constants import ALERTS_READ_PATH
from .utils import PredictiveAssetInsightsEntity, _pai_application_url
from ..assetcentral.utils import (_fetch_data, _add_properties, _parse_filter_parameters,
                                  ResultSet, _AssetcentralField)
from ..utils.timestamps import _odata_to_timestamp_parser


_ALERT_FIELDS = [
    _AssetcentralField('description', 'Description'),
    _AssetcentralField('severity_code', 'SeverityCode'),
    _AssetcentralField('category', 'Category'),
    _AssetcentralField('equipment_name', 'EquipmentName'),
    _AssetcentralField('model_name', 'ModelName'),
    _AssetcentralField('indicator_name', 'IndicatorName'),
    _AssetcentralField('indicator_group_name', 'IndicatorGroupName'),
    _AssetcentralField('template_name', 'TemplateName'),
    _AssetcentralField('count', 'Count'),
    _AssetcentralField('status_code', 'StatusCode'),
    _AssetcentralField('triggered_on', 'TriggeredOn', get_extractor=_odata_to_timestamp_parser()),
    _AssetcentralField('last_occured_on', 'LastOccuredOn', get_extractor=_odata_to_timestamp_parser()),
    _AssetcentralField('type_description', 'AlertTypeDescription'),
    _AssetcentralField('error_code_description', 'ErrorCodeDescription'),
    _AssetcentralField('type', 'AlertType'),
    _AssetcentralField('id', 'AlertId'),
    _AssetcentralField('equipment_id', 'EquipmentID'),
    _AssetcentralField('model_id', 'ModelID'),
    _AssetcentralField('template_id', 'TemplateID'),
    _AssetcentralField('indicator_id', 'IndicatorID'),
    _AssetcentralField('indicator_group_id', 'IndicatorGroupID'),
    _AssetcentralField('notification_id', 'NotificationId'),
    _AssetcentralField('_indicator_description', 'IndicatorDescription'),
    _AssetcentralField('_country_id', 'CountryID'),
    _AssetcentralField('_functional_location_id', 'FunctionalLocationID'),
    _AssetcentralField('_maintenance_plant', 'MaintenancePlant'),
    _AssetcentralField('_functional_location_description', 'FunctionalLocationDescription'),
    _AssetcentralField('_top_functional_location_name', 'TopFunctionalLocationName'),
    _AssetcentralField('_planner_group', 'PlannerGroup'),
    _AssetcentralField('_ref_alert_type_id', 'RefAlertTypeId'),
    _AssetcentralField('_operator_name', 'OperatorName'),
    _AssetcentralField('_created_by', 'CreatedBy'),
    _AssetcentralField('_changed_by', 'ChangedBy'),
    _AssetcentralField('_serial_number', 'SerialNumber'),
    _AssetcentralField('_changed_on', 'ChangedOn', get_extractor=_odata_to_timestamp_parser()),
    _AssetcentralField('_processor', 'Processor'),
    _AssetcentralField('_top_equipment_id', 'TopEquipmentID'),
    _AssetcentralField('_planning_plant', 'PlanningPlant'),
    _AssetcentralField('_error_code_id', 'ErrorCodeID'),
    _AssetcentralField('_operator_id', 'OperatorID'),
    _AssetcentralField('_source', 'Source'),
    _AssetcentralField('_top_equipment_name', 'TopEquipmentName'),
    _AssetcentralField('_created_on', 'CreatedOn', get_extractor=_odata_to_timestamp_parser()),
    _AssetcentralField('_model_description', 'ModelDescription'),
    _AssetcentralField('_top_equipment_description', 'TopEquipmentDescription'),
    _AssetcentralField('_functional_location_name', 'FunctionalLocationName'),
    _AssetcentralField('_top_functional_location_description', 'TopFunctionalLocationDescription'),
    _AssetcentralField('_top_functional_location_id', 'TopFunctionalLocationID'),
    _AssetcentralField('_equipment_description', 'EquipmentDescription'),
]


@_add_properties
class Alert(PredictiveAssetInsightsEntity):
    """PredictiveAssetInsights Alert Object."""

    _field_map = {field.our_name: field for field in _ALERT_FIELDS}


class AlertSet(ResultSet):
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
        _parse_filter_parameters(kwargs, extended_filters, Alert._get_legacy_mapping())

    endpoint_url = _pai_application_url() + ALERTS_READ_PATH
    objects = []
    object_list = _fetch_data(endpoint_url, unbreakable_filters, breakable_filters, 'predictive_asset_insights')
    for odata_result in object_list:
        for element in odata_result['d']['results']:
            objects.append(element)
    return AlertSet([Alert(obj) for obj in objects],
                    {'filters': kwargs, 'extended_filters': extended_filters})
