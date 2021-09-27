"""
Location module can be used to retrieve Location information from AssetCentral.

Classes are provided for individual Locations as well as groups of Locations (LocationSet).
"""

from sailor import _base
from ..utils.timestamps import _string_to_timestamp_parser
from .utils import (AssetcentralEntity, _AssetcentralField, AssetcentralEntitySet,
                    _ac_application_url, _ac_fetch_data)
from .constants import VIEW_LOCATIONS

_LOCATION_FIELDS = [
    _AssetcentralField('name', 'name'),
    _AssetcentralField('short_description', 'shortDescription'),
    _AssetcentralField('type_description', 'locationTypeDescription',
                       query_transformer=_base.masterdata._qt_non_filterable('type_description')),
    _AssetcentralField('id', 'locationId'),
    _AssetcentralField('type', 'locationType',
                       query_transformer=_base.masterdata._qt_non_filterable('type')),
    _AssetcentralField('_status', 'status'),
    _AssetcentralField('_version', 'version'),
    _AssetcentralField('_in_revision', 'hasInRevision'),
    _AssetcentralField('_location', 'location'),
    _AssetcentralField('_completeness', 'completeness'),
    _AssetcentralField('_created_on', 'createdOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_changed_on', 'changedOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_published_on', 'publishedOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_source', 'source'),
    _AssetcentralField('_image_URL', 'imageURL'),
    _AssetcentralField('_location_status', 'locationStatus'),
]


@_base.add_properties
class Location(AssetcentralEntity):
    """AssetCentral Location Object."""

    _field_map = {field.our_name: field for field in _LOCATION_FIELDS}


class LocationSet(AssetcentralEntitySet):
    """Class representing a group of Locations."""

    _element_type = Location
    _method_defaults = {
        'plot_distribution': {
            'by': 'type',
        },
    }


def find_locations(*, extended_filters=(), **kwargs) -> LocationSet:
    """Fetch Locations from AssetCentral with the applied filters, return a LocationSet.

    This method supports the usual filter criteria, i.e.
    - Any named keyword arguments applied as equality filters, i.e. the name of the Location property is checked
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
    Find all Location with name 'MyLocation'::

      find_locations(name='MyLocation')


    Find all Locations which either have the name 'MyLocation' or the name 'MyOtherLocation'::

        find_locations(name=['MyLocation', 'MyOtherLocation'])


    If multiple named arguments are provided then *all* conditions have to match.

    Example
    -------
    Find all Locations with name 'MyLocation' which also have the location type description 'Functional Location'::

        find_locations(name='MyLocation', type_description='Functional Location')


    The ``extended_filters`` parameter can be used to specify filters that can not be expressed as an equality. Each
    extended_filter needs to be provided as a string, multiple filters can be passed as a list of strings. As above,
    all filter criteria need to match. Extended filters can be freely combined with named arguments. Here, too all
    filter criteria need to match for a Location to be returned.

    Example
    -------
    Find all Locations with a short description not matching to 'Location 1'::

        find_locations(extended_filters=['short_description != "Location 1"'])
    """
    unbreakable_filters, breakable_filters = \
        _base.parse_filter_parameters(kwargs, extended_filters, Location._field_map)

    endpoint_url = _ac_application_url() + VIEW_LOCATIONS

    object_list = _ac_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return LocationSet([Location(obj) for obj in object_list])
