"""
Retrieve Functional Location information from AssetCentral.

Classes are provided for individual Functional Locations as well as groups of Functional Locations (FunctionalLocationSet).
"""
from sailor import _base
from ..utils.timestamps import _string_to_timestamp_parser
from .utils import _ac_fetch_data, AssetcentralEntity, _AssetcentralField, AssetcentralEntitySet, \
    _ac_application_url
from .constants import VIEW_FUNCTIONAL_LOCATIONS


_FUNCTIONAL_LOCATION_FIELDS = [
    _AssetcentralField('id', 'id'),
    _AssetcentralField('name', 'name'),
    _AssetcentralField('internal_id', 'internalId'),
    _AssetcentralField('_status', 'status'),
    _AssetcentralField('_status_description', 'statusDescription'),
    _AssetcentralField('_version', 'version'),
    _AssetcentralField('_in_revision', 'hasInRevision'),
    _AssetcentralField('model_id', 'modelId'),
    _AssetcentralField('model_name', 'modelName'),
    _AssetcentralField('short_description', 'shortDescription'),
    _AssetcentralField('_template_id', 'templateId'),
    _AssetcentralField('_subclass', 'subclass'),
    _AssetcentralField('_model_template', 'modelTemplate'),
    _AssetcentralField('location_name', 'location'),
    _AssetcentralField('_criticality_code', 'criticalityCode'),
    _AssetcentralField('_crititcality_description', 'criticalityDescription'),
    _AssetcentralField('_manufacturer', 'manufacturer'),
    _AssetcentralField('_completeness', 'completeness'),
    _AssetcentralField('_created_on', 'createdOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_changed_on', 'changedOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_published_on', 'publishedOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_serial_number', 'serialNumber'),
    _AssetcentralField('_batch_number', 'batchNumber'),
    _AssetcentralField('_tag_number', 'tagNumber'),
    _AssetcentralField('_lifecycle', 'lifeCycle'),
    _AssetcentralField('_lifecycle_description', 'lifeCycleDescription'),
    _AssetcentralField('_source', 'source'),
    _AssetcentralField('_image_URL', 'imageURL'),
    _AssetcentralField('_operator', 'operator'),
    _AssetcentralField('_coordinates', 'coordinates'),
    _AssetcentralField('_installation_date', 'installationDate'),
    _AssetcentralField('_floc_status', 'flocStatus'),
    _AssetcentralField('_build_date', 'buildDate'),
    _AssetcentralField('_is_operator_valid', 'isOperatorValid'),
    _AssetcentralField('_model_version', 'modelVersion'),
    _AssetcentralField('_sold_to', 'soldTo'),
    _AssetcentralField('_image', 'image'),
    _AssetcentralField('_consume', 'consume'),
    _AssetcentralField('_dealer', 'dealer'),
    _AssetcentralField('_service_provider', 'serviceProvider'),
    _AssetcentralField('_primary_external_id', 'primaryExternalId'),
    _AssetcentralField('_floc_search_terms', 'flocSearchTerms'),
    _AssetcentralField('_source_search_terms', 'sourceSearchTerms'),
    _AssetcentralField('_manufacturer_search_terms', 'manufacturerSearchTerms'),
    _AssetcentralField('_operator_search_terms', 'operatorSearchTerms'),
    _AssetcentralField('_class', 'class')
]

@_base.add_properties
class FunctionalLocation(AssetcentralEntity):
    """AssetCentral Functional Location Object."""

    _field_map = {field.our_name: field for field in _FUNCTIONAL_LOCATION_FIELDS}

class FunctionalLocationSet(AssetcentralEntitySet):
    """Class representing a group of Functional Locations."""

    _element_type = FunctionalLocation
    _method_defaults = {
        'plot_distribution': {
            'by': 'model_name',
        },
    }

def find_functional_locations(*, extended_filters=(), **kwargs) -> FunctionalLocationSet:
    """
    Fetch Functional Locations from AssetCentral with the applied filters, return an FunctionalLocationSet.

    This method supports the common filter language explained at :ref:`filter`.

    Parameters
    ----------
    extended_filters
        See :ref:`filter`.
    **kwargs
        See :ref:`filter`.

    Examples
    --------
    Find all Functional Locations with the name 'MyFloc'::

        find_functional_locations(name='MyFloc')

    Find all Functional Locations which either have the name 'MyFloc' or the name 'MyOtherFloc'::

        find_functional_locations(name=['MyFloc', 'MyOtherFloc'])

    Find all Functional Locations with the name 'MyFloc' which are also located in 'London'::

        find_functional_locations(name='MyFloc', location_name='London')

    Find all Functional Locations created between January 1, 2018 and January 1, 2019 in 'London'::

        find_functional_locations(extended_filters=['_created_on >= "2018-01-01"', '_created_on < "2019-01-01"'],
                        location_name='London')
    """
    unbreakable_filters, breakable_filters = \
        _base.parse_filter_parameters(kwargs, extended_filters, FunctionalLocation._field_map)

    endpoint_url = _ac_application_url() + VIEW_FUNCTIONAL_LOCATIONS
    object_list = _ac_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return FunctionalLocationSet([FunctionalLocation(obj) for obj in object_list])