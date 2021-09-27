"""
Failure Mode module can be used to retrieve FailureMode information from AssetCentral.

Classes are provided for individual FailureModes as well as groups of FailureModes (FailureModeSet).
"""

from sailor import _base
from .utils import (AssetcentralEntity, _AssetcentralField, AssetcentralEntitySet,
                    _ac_application_url, _ac_fetch_data)
from .constants import VIEW_FAILUREMODES

_FAILURE_MODE_FIELDS = [
    _AssetcentralField('name', 'DisplayID'),
    _AssetcentralField('short_description', 'ShortDescription'),
    _AssetcentralField('status_text', 'StatusText'),
    _AssetcentralField('long_description', 'LongDescription'),
    _AssetcentralField('id', 'ID'),
    _AssetcentralField('_client', 'Client'),
    _AssetcentralField('_subclass', 'SubClass'),
    _AssetcentralField('_subclass_description', 'SubClassDescription'),
    _AssetcentralField('_type', 'Type'),
    _AssetcentralField('_equipment_count', 'EquipmentsCount'),
    _AssetcentralField('_models_count', 'ModelsCount'),
    _AssetcentralField('_spareparts_count', 'SparepartsCount'),
    _AssetcentralField('_locations_count', 'LocationsCount'),
    _AssetcentralField('_groups_count', 'GroupsCount'),
    _AssetcentralField('_systems_count', 'SystemsCount'),
    _AssetcentralField('_object_count', 'ObjectCount'),
    _AssetcentralField('_source', 'Source'),
    _AssetcentralField('_source_id', 'SourceID'),
    _AssetcentralField('_version', 'Version'),
    _AssetcentralField('_consume', 'Consume'),
    _AssetcentralField('_category_code', 'CategoryCode'),
    _AssetcentralField('_category_description', 'CategoryDescription'),
    _AssetcentralField('_causes', 'Causes'),
    _AssetcentralField('_status', 'Status'),
    _AssetcentralField('_last_change', 'LastChange'),
    _AssetcentralField('_my_failure_mode', 'MyFailureMode'),
    _AssetcentralField('_owner', 'Owner'),
    _AssetcentralField('_object_id', 'ObjectID'),
    _AssetcentralField('_pattern_id', 'PatternID'),
    _AssetcentralField('_pattern_confidence', 'PatternConfidence'),
    _AssetcentralField('_MTTF_value', 'MTTFValue', query_transformer=_base.masterdata._qt_double),
    _AssetcentralField('_MTTF_unit', 'MTTFUnit'),
    _AssetcentralField('_MTTF_confidence', 'MTTFConfidence'),
    _AssetcentralField('_MTTR_value', 'MTTRValue', query_transformer=_base.masterdata._qt_double),
    _AssetcentralField('_MTTR_unit', 'MTTRUnit'),
    _AssetcentralField('_MTTR_confidence', 'MTTRConfidence'),
    _AssetcentralField('_MTBF_value', 'MTBFValue', query_transformer=_base.masterdata._qt_double),
    _AssetcentralField('_MTBF_unit', 'MTBFUnit'),
    _AssetcentralField('_MTBF_confidence', 'MTBFConfidence'),
    _AssetcentralField('_pattern_name', 'PatternName'),
    _AssetcentralField('_pattern_image', 'PatternImage'),
    _AssetcentralField('_image_id', 'ImageID'),
    _AssetcentralField('_primary_external_id', 'PrimaryExternalID'),
    _AssetcentralField('_failure_mode_search_terms', 'FailureModesSearchTerms'),
    _AssetcentralField('_type_code', 'TypeCode'),
    _AssetcentralField('_detection_method', 'DetectionMethod'),
]


@_base.add_properties
class FailureMode(AssetcentralEntity):
    """AssetCentral Failure Mode Object."""

    _field_map = {field.our_name: field for field in _FAILURE_MODE_FIELDS}


class FailureModeSet(AssetcentralEntitySet):
    """Class representing a group of FailureModes."""

    _element_type = FailureMode
    _method_defaults = {
        'plot_distribution': {
            'by': 'status_text',
        },
    }


def find_failure_modes(*, extended_filters=(), **kwargs) -> FailureModeSet:
    """Fetch FailureModes from AssetCentral with the applied filters, return an FailureModeSet.

    This method supports the usual filter criteria, i.e.
    - Any named keyword arguments applied as equality filters, i.e. the name of the FailureMode property is checked
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
    Find all FailureModes with name 'MyFailureMode'::

        find_failure_modes(name='MyFailureMode')

    Find all FailureModes which either have the name 'MyFailureMode' or the name 'MyOtherFailureMode'::

        find_failure_modes(name=['MyFailureMode', 'MyOtherFailureMode'])


    If multiple named arguments are provided then *all* conditions have to match.

    Example
    -------
    Find all FailureModes with name 'MyFailureMode' which also have the short description 'Description'::

        find_failure_modes(name='MyFailureMode', short_description='Description')


    The ``extended_filters`` parameter can be used to specify filters that can not be expressed as an equality. Each
    extended_filter needs to be provided as a string, multiple filters can be passed as a list of strings. As above,
    all filter criteria need to match. Extended filters can be freely combined with named arguments. Here, too, all
    filter criteria need to match for a FailureMode to be returned.

    Example
    -------
    Find all FailureModes where equipment count higher or equal to 5::

        find_failure_modes(extended_filters=['equipments_count >= 5'])
    """
    unbreakable_filters, breakable_filters = \
        _base.parse_filter_parameters(kwargs, extended_filters, FailureMode._field_map)

    endpoint_url = _ac_application_url() + VIEW_FAILUREMODES
    object_list = _ac_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return FailureModeSet([FailureMode(obj) for obj in object_list])
