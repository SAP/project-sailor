"""
Retrieve Model information from AssetCentral.

Classes are provided for individual Models as well as groups of Models (ModelSet).
Models can be of type Equipment, System or FunctionalLocation, but the type is not part of the AC response currently.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import VIEW_MODEL_INDICATORS, VIEW_MODELS
from .indicators import Indicator, IndicatorSet
from .equipment import find_equipment
from .utils import _fetch_data, _add_properties, _parse_filter_parameters, \
    _apply_filters_post_request, _ac_application_url, AssetcentralEntity, ResultSet
from ..utils.timestamps import _string_to_timestamp_parser

if TYPE_CHECKING:
    from .equipment import EquipmentSet


@_add_properties
class Model(AssetcentralEntity):
    """AssetCentral Model object."""

    # Properties (in AC terminology) are:  # as returned by 'models'-api, not model-details
    # modelId, name, internalId, status, version, hasInRevision, templateId, modelTemplate, subclass,
    # generation, manufacturer, shortDescription, longDescription, completeness, createdOn, changedOn,
    # imageURL, publishedOn, source, equipmentTracking, serviceExpirationDate, modelExpirationDate,
    # releaseDate, isManufacturerValid, image, isClientValid, consume, primaryExternalId, modelSearchTerms,
    # sourceSearchTerms, manufacturerSearchTerms, class

    # Additional properties returned in model-details (again ac terminology, some have sub-structure):
    # organizationID, calibrationDate, orderStopDate, noSparePartsDate, globalId, keywords, safetyRiskCode,
    # description, descriptions[], gtin, brand, isFirmwareCompatible, templates[], classId, subclassId, adminData{},
    # sectionCompleteness{}, modelType, countryCode, referenceId, metadata, templatesDetails[]

    @classmethod
    def get_property_mapping(cls):
        """Return a mapping from assetcentral terminology to our terminology."""
        return {
            'id': ('modelId', None, None, None),
            'name': ('name', None, None, None),
            'short_description': ('shortDescription', None, None, None),
            'long_description': ('longDescription', None, None, None),
            'generation': ('generation', None, None, None),
            'manufacturer': ('manufacturer', None, None, None),
            'model_expiration_date': ('modelExpirationDate',
                                      _string_to_timestamp_parser('modelExpirationDate', 'ms'), None, None),
            'model_template_id': ('modelTemplate', None, None, None),
            'service_expiration_date': ('serviceExpirationDate',
                                        _string_to_timestamp_parser('serviceExpirationDate', 'ms'), None, None),
            'template_id': ('templateId', None, None, None),
        }

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
        object_list = _fetch_data(endpoint_url)
        filtered_objects = _apply_filters_post_request(object_list, kwargs, extended_filters,
                                                       Indicator.get_property_mapping())

        return IndicatorSet([Indicator(obj) for obj in filtered_objects])


class ModelSet(ResultSet):
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
        _parse_filter_parameters(kwargs, extended_filters, Model.get_property_mapping())

    endpoint_url = _ac_application_url() + VIEW_MODELS
    object_list = _fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return ModelSet([Model(obj) for obj in object_list],
                    {'filters': kwargs, 'extended_filters': extended_filters})
