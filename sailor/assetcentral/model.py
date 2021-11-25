"""
Retrieve Model information from AssetCentral.

Classes are provided for individual Models as well as groups of Models (ModelSet).
Models can be of type Equipment, System or FunctionalLocation, but the type is not part of the AC response currently.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sailor import _base
from ..utils.timestamps import _string_to_timestamp_parser
from .constants import VIEW_MODEL_INDICATORS, VIEW_MODELS
from .indicators import Indicator, IndicatorSet
from .equipment import find_equipment
from .utils import (AssetcentralEntity, _AssetcentralField, AssetcentralEntitySet,
                    _ac_application_url, _ac_fetch_data)

if TYPE_CHECKING:
    from .equipment import EquipmentSet


_MODEL_FIELDS = [
    _AssetcentralField('name', 'internalId'),  # there is also a native `name`, which we're ignoring
    _AssetcentralField('model_type', 'modelType'),
    _AssetcentralField('manufacturer', 'manufacturer'),
    _AssetcentralField('short_description', 'shortDescription'),
    _AssetcentralField('service_expiration_date', 'serviceExpirationDate',
                       get_extractor=_string_to_timestamp_parser(unit='ms'),
                       query_transformer=_base.masterdata._qt_timestamp),
    _AssetcentralField('model_expiration_date', 'modelExpirationDate',
                       get_extractor=_string_to_timestamp_parser(unit='ms'),
                       query_transformer=_base.masterdata._qt_timestamp),
    _AssetcentralField('generation', 'generation'),
    _AssetcentralField('long_description', 'longDescription'),
    _AssetcentralField('id', 'modelId'),
    _AssetcentralField('template_id', 'templateId'),
    _AssetcentralField('model_template_id', 'modelTemplate'),
    _AssetcentralField('_status', 'status'),
    _AssetcentralField('_version', 'version'),
    _AssetcentralField('_in_revision', 'hasInRevision'),
    _AssetcentralField('_subclass', 'subclass'),
    _AssetcentralField('_completeness', 'completeness'),
    _AssetcentralField('_created_on', 'createdOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_changed_on', 'changedOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_published_on', 'publishedOn', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_image_URL', 'imageURL'),
    _AssetcentralField('_source', 'source'),
    _AssetcentralField('_equipment_tracking', 'equipmentTracking'),
    _AssetcentralField('_release_date', 'releaseDate', get_extractor=_string_to_timestamp_parser(unit='ms')),
    _AssetcentralField('_is_manufacturer_valid', 'isManufacturerValid'),
    _AssetcentralField('_image', 'image'),
    _AssetcentralField('_is_client_valid', 'isClientValid'),
    _AssetcentralField('_consume', 'consume'),
    _AssetcentralField('_primary_external_id', 'primaryExternalId'),
    _AssetcentralField('_model_search_terms', 'modelSearchTerms'),
    _AssetcentralField('_source_search_terms', 'sourceSearchTerms'),
    _AssetcentralField('_manufacturer_search_terms', 'manufacturerSearchTerms'),
    _AssetcentralField('_class', 'class'),
]


@_base.add_properties
class Model(AssetcentralEntity):
    """AssetCentral Model object."""

    # Additional properties returned in model-details (ac terminology, some have sub-structure):
    # organizationID, calibrationDate, orderStopDate, noSparePartsDate, globalId, keywords, safetyRiskCode,
    # description, descriptions[], gtin, brand, isFirmwareCompatible, templates[], classId, subclassId, adminData{},
    # sectionCompleteness{}, modelType, countryCode, referenceId, metadata, templatesDetails[]

    _field_map = {field.our_name: field for field in _MODEL_FIELDS}

    def find_equipment(self, *, extended_filters=(), **kwargs) -> EquipmentSet:
        """
        Get a list of equipment derived from this Model.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Example
        -------
        Find all Equipment for Model 'myModelName'. Return an EquipmentSet::

           model = find_models(name='myModelName')
           model[0].find_equipment()

        The resulting Equipments can further be filter based on their properties (name, location etc).
        """
        kwargs['model_id'] = self.id
        return find_equipment(extended_filters=extended_filters, **kwargs)

    def find_model_indicators(self, *, extended_filters=(), **kwargs) -> IndicatorSet:
        """Return all Indicators assigned to the Model.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Example
        -------
        Find all indicators for Model 'myModelName'::

            models = find_models(name='myModelName')
            models[0].find_model_indicators()
        """
        endpoint_url = _ac_application_url() + VIEW_MODEL_INDICATORS + f'({self.id})' + '/indicatorvalues'

        # AC-BUG: this api doesn't support filters (thank you AC) so we have to fetch all of them and then filter below
        object_list = _ac_fetch_data(endpoint_url)
        filtered_objects = _base.apply_filters_post_request(object_list, kwargs, extended_filters,
                                                            Indicator._field_map)

        return IndicatorSet([Indicator(obj) for obj in filtered_objects])


class ModelSet(AssetcentralEntitySet):
    """Class representing a group of Models."""

    _element_type = Model
    _method_defaults = {
        'plot_distribution': {
            'by': 'model_template_id',
        },
    }


def find_models(*, extended_filters=(), **kwargs) -> ModelSet:
    """Fetch Models from AssetCentral with the applied filters, return an ModelSet.

    This method supports the usual filter criteria, i.e.
    Any named keyword arguments applied as equality filters, i.e. the name of the Model property is checked
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
    Find all Models with name 'MyModel'::

        find_models(name='MyModel')

    Find all Models which either have the name 'MyModel' or the name 'MyOtherModel'::

        find_models(name=['MyModel', 'MyOtherModel'])


    If multiple named arguments are provided then *all* conditions have to match.

    Example
    -------
    Find all Models with name 'MyModel' which also have the short description 'Description'::

        find_models(name='MyModel', short_description='Description')

    The ``extended_filters`` parameter can be used to specify filters that can not be expressed as an equality. Each
    extended_filter needs to be provided as a string, multiple filters can be passed as a list of strings. As above,
    all filter criteria need to match. Extended filters can be freely combined with named arguments. Here, too, all
    filter criteria need to match for an Model to be returned.

    Example
    -------
    Find all Models with an expiration date before January 1, 2018::

        find_models(extended_filters=['model_expiration_date < "2018-01-01"'])
    """
    unbreakable_filters, breakable_filters = \
        _base.parse_filter_parameters(kwargs, extended_filters, Model._field_map)

    endpoint_url = _ac_application_url() + VIEW_MODELS
    object_list = _ac_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return ModelSet([Model(obj) for obj in object_list])
