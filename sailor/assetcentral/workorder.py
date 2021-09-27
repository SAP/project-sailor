"""
Workorder module can be used to retrieve Workorder information from AssetCentral.

Classes are provided for individual Workorders as well as groups of Workorders (WorkorderSet).
"""

from sailor import _base
from ..utils.timestamps import _string_to_timestamp_parser
from .constants import VIEW_WORKORDERS
from .utils import (AssetcentralEntity, _AssetcentralField, AssetcentralEntitySet,
                    _ac_application_url, _ac_fetch_data)


_WORKORDER_FIELDS = [
    _AssetcentralField('name', 'internalId'),
    _AssetcentralField('type_description', 'workOrderTypeDescription'),
    _AssetcentralField('priority_description', 'priorityDescription'),
    _AssetcentralField('status_text', 'statusDescription'),
    _AssetcentralField('short_description', 'shortDescription'),
    _AssetcentralField('equipment_name', 'equipmentName'),
    _AssetcentralField('location', 'location'),
    _AssetcentralField('plant', 'plant'),
    _AssetcentralField('start_date', 'startDate',
                       query_transformer=_base.masterdata._qt_date),
    _AssetcentralField('end_date', 'endDate',
                       query_transformer=_base.masterdata._qt_date),
    _AssetcentralField('long_description', 'longDescription'),
    _AssetcentralField('id', 'workOrderID'),
    _AssetcentralField('equipment_id', 'equipmentId'),
    _AssetcentralField('model_id', 'modelId'),
    _AssetcentralField('type', 'workOrderType'),
    _AssetcentralField('_status', 'status'),
    _AssetcentralField('_priority', 'priority'),
    _AssetcentralField('_workcenter', 'workCenter'),
    _AssetcentralField('_is_internal', 'isInternal'),
    _AssetcentralField('_created_by', 'createdBy'),
    _AssetcentralField('_created_on', 'creationDateTime'),
    _AssetcentralField('_lastChangedBy', 'lastChangedBy'),
    _AssetcentralField('_changed_on', 'lastChangeDateTime'),
    _AssetcentralField('_basic_start_date', 'basicStartDate', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_basic_end_date', 'basicEndDate', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_actual_start_date', 'actualStartDate',
                       get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_actual_end_date', 'actualEndDate', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_progress_status', 'progressStatus'),
    _AssetcentralField('_progress_status_description', 'progressStatusDescription'),
    _AssetcentralField('_root_equipment_id', 'rootEquipmentId'),
    _AssetcentralField('_root_equipment_name', 'rootEquipmentName'),
    _AssetcentralField('_person_responsible', 'personResponsible'),
    _AssetcentralField('_location_id', 'locationId'),
    _AssetcentralField('_coordinates', 'coordinates'),
    _AssetcentralField('_source', 'source'),
    _AssetcentralField('_source_id', 'sourceId'),
    _AssetcentralField('_operator_id', 'operatorId'),
    _AssetcentralField('_is_source_active', 'isSourceActive'),
    _AssetcentralField('_asset_core_equipment_id', 'assetCoreEquipmentId'),
    _AssetcentralField('_operator', 'operator'),
]


@_base.add_properties
class Workorder(AssetcentralEntity):
    """AssetCentral Workorder Object."""

    _field_map = {field.our_name: field for field in _WORKORDER_FIELDS}


class WorkorderSet(AssetcentralEntitySet):
    """Class representing a group of Workorders."""

    _element_type = Workorder
    _method_defaults = {
        'plot_distribution': {
            'by': 'equipment_name',
        },
    }


def find_workorders(*, extended_filters=(), **kwargs) -> WorkorderSet:
    """Fetch Workorders from AssetCentral with the applied filters, return a WorkorderSet.

    This method supports the usual filter criteria, i.e.
    - Any named keyword arguments applied as equality filters, i.e. the name of the Workorder property is checked
    against the value of the keyword argument. If the value of the keyword argument is an iterable (e.g. a list)
    then all objects matching any of the values in the iterable are returned.

    Parameters
    ----------
    extended_filters
        See :ref:`filter`.
    **kwargs
        See :ref:`filter`.

    Examples
    --------
    Find all Workorders with name 'MyWorkorder'::

        find_workorders(name='MyWorkorder')

    Find all Workorders which either have the name 'MyWorkorder' or the name 'MyOtherWorkorder'::

        find_workorders(name=['MyWorkorder', 'MyOtherWorkorder'])

    Find all workorders with very high priority::

        find_workorders(priority = 20)

    If multiple named arguments are provided then *all* conditions have to match.

    Example
    -------
    Find all workorders with very high priority (20) and has progress status 'pending'(15) ::

        find_workorders(priority = 20, progressStatus = 15).


    The ``extended_filters`` parameter can be used to specify filters that can not be expressed as an equality. Each
    extended_filter needs to be provided as a string, multiple filters can be passed as a list of strings. As above,
    all filter criteria need to match. Extended filters can be freely combined with named arguments. Here, too all
    filter criteria need to match for a Workorder to be returned.

    Example
    -------
    Find all Workorders with start date higher than 2020-01-01::

        find_workorders(extended_filters=['start_date >= "2020-01-01"'])
    """
    unbreakable_filters, breakable_filters = \
        _base.parse_filter_parameters(kwargs, extended_filters, Workorder._field_map)

    endpoint_url = _ac_application_url() + VIEW_WORKORDERS
    object_list = _ac_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return WorkorderSet([Workorder(obj) for obj in object_list])
