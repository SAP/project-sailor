"""
Workorder module can be used to retrieve Workorder information from AssetCentral.

Classes are provided for individual Workorders as well as groups of Workorders (WorkorderSet).
"""

from .utils import _fetch_data, _add_properties, _parse_filter_parameters, AssetcentralEntity, ResultSet, \
    _ac_application_url
from .constants import VIEW_WORKORDERS


@_add_properties
class Workorder(AssetcentralEntity):
    """AssetCentral Workorder Object."""

    # Properties (in AC terminology) are:
    # workOrderID, shortDescription, status, statusDescription, workOrderType, workOrderTypeDescription, priority,
    # priorityDescription, isInternal, createdBy, creationDateTime, lastChangedBy, lastChangeDateTime, longDescription,
    # startDate, endDate, progressStatus, progressStatusDescription, equipmentId, equipmentName, rootEquipmentId,
    # rootEquipmentName, locationId, coordinates, source, sourceId, operatorId, location, isSourceActive,
    # assetCoreEquipmentId, operator, internalId, modelId, plant, workCenter, basicStartDate, basicEndDate,
    # actualStartDate, actualEndDate, personResponsible

    @classmethod
    def get_property_mapping(cls):
        """Return a mapping from assetcentral terminology to our terminology."""
        return {
            'id': ('workOrderID', None, None, None),
            'name': ('internalId', None, None, None),
            'short_description': ('shortDescription', None, None, None),
            'long_description': ('longDescription', None, None, None),
            'equipment_id': ('equipmentId', None, None, None),
            'equipment_name': ('equipmentName', None, None, None),
            'endDate': ('end_date', None, None, None),
            'location': ('location', None, None, None),
            'plant': ('plant', None, None, None),
            'priority_description': ('priorityDescription', None, None, None),
            'start_date': ('startDate', None, None, None),
            'status_text': ('statusDescription', None, None, None),
            'type': ('workOrderType', None, None, None),
            'type_description': ('workOrderTypeDescription', None, None, None),
        }


class WorkorderSet(ResultSet):
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
        _parse_filter_parameters(kwargs, extended_filters, Workorder.get_property_mapping())

    endpoint_url = _ac_application_url() + VIEW_WORKORDERS
    object_list = _fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return WorkorderSet([Workorder(obj) for obj in object_list],
                        {'filters': kwargs, 'extended_filters': extended_filters})
