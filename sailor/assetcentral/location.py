"""
Location module can be used to retrieve Location information from AssetCentral.

Classes are provided for individual Locations as well as groups of Locations (LocationSet).
"""


from .utils import _fetch_data, _add_properties, _parse_filter_parameters, AssetcentralEntity, ResultSet, \
    _ac_application_url
from .constants import VIEW_LOCATIONS


@_add_properties
class Location(AssetcentralEntity):
    """AssetCentral Location Object."""

    # Properties (in AC terminology) are:
    # locationId, name, status, version, hasInRevision, shortDescription, location, completeness, createdOn,
    # changedOn, publishedOn, source, imageURL, locationStatus, locationTypeDescription, locationType

    @classmethod
    def get_property_mapping(cls):
        """Return a mapping from assetcentral terminology to our terminology."""
        return {
            'id': ('locationId', None, None, None),
            'name': ('name', None, None, None),
            'short_description': ('shortDescription', None, None, None),
            'type': ('locationType', None, None, None),
            'type_description': ('locationTypeDescription', None, None, None),
        }


class LocationSet(ResultSet):
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
        _parse_filter_parameters(kwargs, extended_filters, Location.get_property_mapping())

    endpoint_url = _ac_application_url() + VIEW_LOCATIONS

    object_list = _fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return LocationSet([Location(obj) for obj in object_list],
                       {'filters': kwargs, 'extended_filters': extended_filters})
