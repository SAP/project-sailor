"""
Failure Mode module can be used to retrieve FailureMode information from AssetCentral.

Classes are provided for individual FailureModes as well as groups of FailureModes (FailureModeSet).
"""


from .utils import _fetch_data, _add_properties, _parse_filter_parameters, ResultSet, \
    AssetcentralEntity, _ac_application_url
from .constants import VIEW_FAILUREMODES


@_add_properties
class FailureMode(AssetcentralEntity):
    """AssetCentral Failure Mode Object."""

    # Properties (in AC terminology) are:
    # Client, ID, SubClass, StatusText, SubClassDescription, Type, EquipmentsCount, ModelsCount, SparepartsCount,
    # LocationsCount, GroupsCount, SystemsCount, ObjectCount, DisplayID, Source, SourceID, Version, Consume,
    # CategoryCode, CategoryDescription, Causes, ShortDescription, LongDescription, Status, LastChange, MyFailureMode,
    # Owner, ObjectID, PatternID, PatternConfidence, MTTFValue, MTTFUnit, MTTFConfidence, MTTRValue, MTTRUnit,
    # MTTRConfidence, MTBFValue, MTBFUnit, MTBFConfidence, PatternName, PatternImage, ImageID, PrimaryExternalID,
    # FailureModesSearchTerms, TypeCode, DetectionMethod

    @classmethod
    def get_property_mapping(cls):
        """Return a mapping from assetcentral terminology to our terminology."""
        return {
            'id': ('ID', None, None, None),
            'name': ('DisplayID', None, None, None),
            'short_description': ('ShortDescription', None, None, None),
            'long_description': ('LongDescription', None, None, None),
            'status_text': ('StatusText', None, None, None),
        }


class FailureModeSet(ResultSet):
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
        _parse_filter_parameters(kwargs, extended_filters, FailureMode.get_property_mapping())

    endpoint_url = _ac_application_url() + VIEW_FAILUREMODES
    object_list = _fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return FailureModeSet([FailureMode(obj) for obj in object_list],
                          {'filters': kwargs, 'extended_filters': extended_filters})
