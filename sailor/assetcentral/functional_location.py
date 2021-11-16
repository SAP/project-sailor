"""
Retrieve Functional Location information from AssetCentral.

Classes are provided for individual Functional Locations as well as groups
of Functional Locations (FunctionalLocationSet).
"""

from sailor import _base
from ..utils.timestamps import _string_to_timestamp_parser
from .utils import _ac_fetch_data, AssetcentralEntity, _AssetcentralField, AssetcentralEntitySet, \
    _ac_application_url
from .constants import VIEW_FUNCTIONAL_LOCATIONS


_FUNCTIONAL_LOCATION_FIELDS = [
    _AssetcentralField('name', 'internalId'),
    _AssetcentralField('model_name', 'modelName'),
    _AssetcentralField('status_text', 'statusDescription',
                       query_transformer=_base.masterdata._qt_non_filterable('status_text')),
    _AssetcentralField('short_description', 'shortDescription'),
    _AssetcentralField('manufacturer', 'manufacturer'),
    _AssetcentralField('operator', 'operator'),
    _AssetcentralField('crititcality_description', 'criticalityDescription'),
    _AssetcentralField('id', 'id'),
    _AssetcentralField('model_id', 'modelId'),
    _AssetcentralField('template_id', 'templateId'),
    _AssetcentralField('serial_number', 'serialNumber'),
    _AssetcentralField('batch_number', 'batchNumber'),
    _AssetcentralField('_status', 'status'),
    _AssetcentralField('_version', 'version'),
    _AssetcentralField('_in_revision', 'hasInRevision'),
    _AssetcentralField('_subclass', 'subclass'),
    _AssetcentralField('_model_template', 'modelTemplate'),
    _AssetcentralField('_criticality_code', 'criticalityCode'),
    _AssetcentralField('_completeness', 'completeness'),
    _AssetcentralField('_created_on', 'createdOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_changed_on', 'changedOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_published_on', 'publishedOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_installation_date', 'installationDate', get_extractor=_string_to_timestamp_parser('ms'),
                       query_transformer=_base.masterdata._qt_timestamp),
    _AssetcentralField('_build_date', 'buildDate', get_extractor=_string_to_timestamp_parser('ms'),
                       query_transformer=_base.masterdata._qt_timestamp),
    _AssetcentralField('_tag_number', 'tagNumber'),
    _AssetcentralField('_lifecycle', 'lifeCycle'),
    _AssetcentralField('_lifecycle_description', 'lifeCycleDescription'),
    _AssetcentralField('_location', 'location'),
    _AssetcentralField('_source', 'source'),
    _AssetcentralField('_image_URL', 'imageURL'),
    _AssetcentralField('_coordinates', 'coordinates'),
    _AssetcentralField('_floc_status', 'flocStatus'),
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

    Find all Functional Locations by manufacturer 'ACME Corp' which are operated by 'Operator 42'::

        find_functional_locations(manufacturer='ACME Corp', operator='Operator 42')
    """
    unbreakable_filters, breakable_filters = \
        _base.parse_filter_parameters(kwargs, extended_filters, FunctionalLocation._field_map)

    endpoint_url = _ac_application_url() + VIEW_FUNCTIONAL_LOCATIONS
    object_list = _ac_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return FunctionalLocationSet([FunctionalLocation(obj) for obj in object_list])
