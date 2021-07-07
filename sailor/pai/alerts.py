"""
Retrieve Alert information from the alert re-use service.

Classes are provided for individual Alert as well as groups of Alerts (AlertSet).
"""


from .constants import ALERTS_READ_PATH
from .utils import PredictiveAssetInsightsEntity, _pai_application_url
from ..assetcentral.utils import _fetch_data, _add_properties, _parse_filter_parameters, ResultSet
from ..utils.timestamps import _odata_to_timestamp_parser


@_add_properties
class Alert(PredictiveAssetInsightsEntity):
    """PredictiveAssetInsights Alert Object."""

    # Properties (in PredictiveAssetInsights terminology) are:
    # AlertId, AlertType, AlertTypeDescription, Category, ChangedBy, ChangedOn, Count, CountryID,
    # CreatedBy, CreatedOn, CustomProperty, Description, EquipmentDescription, EquipmentID, EquipmentName,
    # ErrorCodeDescription, ErrorCodeID, FunctionalLocationID, FunctionalLocationName, FunctionalLocationDescription,
    # IndicatorDescription, IndicatorGroupID, IndicatorGroupName, IndicatorID, IndicatorName, LastOccuredOn,
    # MaintenancePlant, ModelDescription, ModelID, ModelName, NotificationId, OperatorID, OperatorName,
    # lannerGroup, PlanningPlant, Processor, RefAlertTypeId, SerialNumber, SeverityCode, Source, StatusCode,
    # TemplateID, TemplateName, TopEquipmentDescription, TopEquipmentID, TopEquipmentName, TopFunctionalLocationID,
    # TopFunctionalLocationName, TopFunctionalLocationDescription, TriggeredOn

    @classmethod
    def get_property_mapping(cls):
        """Return a mapping from PredictiveAssetInsights (PAI) terminology to our terminology."""
        return {
            'id': ('AlertId', None, None, None),
            'type': ('AlertType', None, None, None),
            'type_description': ('AlertTypeDescription', None, None, None),
            'category': ('Category', None, None, None),
            'changed_by': ('ChangedBy', None, None, None),
            'changed_on': ('ChangedOn', _odata_to_timestamp_parser('ChangedOn', unit='s'), None, None),
            'count': ('Count', None, None, None),
            'country_id': ('CountryID', None, None, None),
            'created_by': ('CreatedBy', None, None, None),
            'created_on': ('CreatedOn', _odata_to_timestamp_parser('CreatedOn', unit='s'), None, None),
            'custom_property': ('CustomProperty', None, None, None),
            'description': ('Description', None, None, None),
            'equipment_description': ('EquipmentDescription', None, None, None),
            'equipment_id': ('EquipmentID', None, None, None),
            'equipment_name': ('EquipmentName', None, None, None),
            'error_code_description': ('ErrorCodeDescription', None, None, None),
            'error_code_id': ('ErrorCodeID', None, None, None),
            'functional_location_id': ('FunctionalLocationID', None, None, None),
            'functional_location_name': ('FunctionalLocationName', None, None, None),
            'functional_location_description': ('FunctionalLocationDescription', None, None, None),
            'indicator_description': ('IndicatorDescription', None, None, None),
            'indicator_group_id': ('IndicatorGroupID', None, None, None),
            'indicator_group_name': ('IndicatorGroupName', None, None, None),
            'indicator_id': ('IndicatorID', None, None, None),
            'indicator_name': ('IndicatorName', None, None, None),
            'last_occured_on': ('LastOccuredOn', _odata_to_timestamp_parser('CreatedOn', unit='s'), None, None),
            'maintenance_plant': ('MaintenancePlant', None, None, None),
            'model_description': ('ModelDescription', None, None, None),
            'model_id': ('ModelID', None, None, None),
            'model_name': ('ModelName', None, None, None),
            'notification_id': ('NotificationId', None, None, None),
            'operator_id': ('OperatorID', None, None, None),
            'operator_name': ('OperatorName', None, None, None),
            'planner_group': ('PlannerGroup', None, None, None),
            'planning_plant': ('PlanningPlant', None, None, None),
            'processor': ('Processor', None, None, None),
            'ref_alert_type_id': ('RefAlertTypeId', None, None, None),
            'serial_number': ('SerialNumber', None, None, None),
            'severity_code': ('SeverityCode', None, None, None),
            'source': ('Source', None, None, None),
            'template_id': ('TemplateID', None, None, None),
            'status_code': ('StatusCode', None, None, None),
            'template_name': ('TemplateName', None, None, None),
            'top_equipment_description': ('TopEquipmentDescription', None, None, None),
            'top_equipment_id': ('TopEquipmentID', None, None, None),
            'top_equipment_name': ('TopEquipmentName', None, None, None),
            'top_functional_location_id': ('TopFunctionalLocationID', None, None, None),
            'top_functional_location_name': ('TopFunctionalLocationName', None, None, None),
            'top_functional_location_description': ('TopFunctionalLocationDescription', None, None, None),
            'triggered_on': ('TriggeredOn', _odata_to_timestamp_parser('TriggeredOn', unit='s'), None, None)
        }


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
        _parse_filter_parameters(kwargs, extended_filters, Alert.get_property_mapping())

    endpoint_url = _pai_application_url() + ALERTS_READ_PATH
    objects = []
    object_list = _fetch_data(endpoint_url, unbreakable_filters, breakable_filters, 'predictive_asset_insights')
    for odata_result in object_list:
        for element in odata_result['d']['results']:
            objects.append(element)
    return AlertSet([Alert(obj) for obj in objects],
                    {'filters': kwargs, 'extended_filters': extended_filters})
