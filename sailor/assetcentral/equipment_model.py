"""
Retrieve EquipmentModel information from AssetCentral.

Classes are provided for individual EquipmentModels as well as groups of EquipemtModels (EquipmentModelSet).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import EQUIPMENT_MODEL_INDICATORS, EQUIPMENT_MODEL_API, INDICATOR_CONFIGURATION
from .indicators import Indicator, IndicatorSet
from .equipment import find_equipment
from .utils import _fetch_data, _add_properties, _parse_filter_parameters, \
    _apply_filters_post_request, _ac_application_url, AssetcentralEntity, ResultSet
from ..utils.timestamps import _string_to_timestamp_parser

if TYPE_CHECKING:
    from .equipment import EquipmentSet


@_add_properties
class EquipmentModel(AssetcentralEntity):
    """
    AssetCentral EquipmentModel object.

    Properties (in AC terminology) are:  # as returned by 'models'-api, not model-details
    modelId, name, internalId, status, version, hasInRevision, templateId, modelTemplate, subclass,
    generation, manufacturer, shortDescription, longDescription, completeness, createdOn, changedOn,
    imageURL, publishedOn, source, equipmentTracking, serviceExpirationDate, modelExpirationDate,
    releaseDate, isManufacturerValid, image, isClientValid, consume, primaryExternalId, modelSearchTerms,
    sourceSearchTerms, manufacturerSearchTerms, class

    Additional properties returned in model-details (again ac terminology, some have sub-structure):
    organizationID, calibrationDate, orderStopDate, noSparePartsDate, globalId, keywords, safetyRiskCode,
    description, descriptions[], gtin, brand, isFirmwareCompatible, templates[], classId, subclassId, adminData{},
    sectionCompleteness{}, modelType, countryCode, referenceId, metadata, templatesDetails[]
    """

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

    def find_equipment(self, extended_filters=(), **kwargs) -> EquipmentSet:
        """
        Get a list of equipment derived from this EquipmentModel.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Example
        -------
        Find all Equipment for EquipmentModel 'myEquipmentModelName'. Return an EquipmentSet::

           model = find_equipment_models(name='myEquipmentModelName')
           model[0].find_equipment()

        The resulting Equipments can further be filter based on their properties (name, location etc).
        """
        kwargs['equipment_model_id'] = self.id
        return find_equipment(extended_filters, **kwargs)

    def find_model_indicators(self, extended_filters=(), **kwargs) -> IndicatorSet:
        """Return all Indicators assigned to the EquipmentModel.

        Parameters
        ----------
        extended_filters
            See :ref:`filter`.
        **kwargs
            See :ref:`filter`.

        Example
        -------
        Find all indicators for Equipment Model 'myEquipmentModelName'::

            models = find_equipment_models(name='myEquipmentModelName')
            models[0].find_model_indicators()
        """
        endpoint_url = _ac_application_url() + EQUIPMENT_MODEL_INDICATORS + f'({self.id})' + '/indicatorvalues'

        # AC-BUG: this api doesn't support filters (thank you AC) so we have to fetch all of them and then filter below
        object_list = _fetch_data(endpoint_url)
        filtered_objects = _apply_filters_post_request(object_list, kwargs, extended_filters,
                                                       Indicator.get_property_mapping())

        return IndicatorSet([Indicator(obj) for obj in filtered_objects])

    def get_header(self):
        """Retrieve header information for the EquipmentModel."""
        endpoint_url = _ac_application_url() + EQUIPMENT_MODEL_API + f'({self.id})' + '/header'
        header = _fetch_data(endpoint_url)
        return header

    def get_indicator_configuration_of_model(self):
        """Retrieve details on an indicator attached to an equipment model."""
        endpoint_url = _ac_application_url() + INDICATOR_CONFIGURATION + f'({self.id})' + '/header'
        header = _fetch_data(endpoint_url)
        return header


class EquipmentModelSet(ResultSet):
    """Class representing a group of EquipmentModels."""

    _element_type = EquipmentModel
    _method_defaults = {
        'plot_distribution': {
            'by': 'model_template_id',
        },
    }


def find_equipment_models(extended_filters=(), **kwargs) -> EquipmentModelSet:
    """Fetch EquipmentModels from AssetCentral with the applied filters, return an EquipmentModelSet.

    This method supports the usual filter criteria, i.e.
    Any named keyword arguments applied as equality filters, i.e. the name of the EquipmentModel property is checked
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
    Find all EquipmentModels with name 'MyEquipmentModel'::

        find_equipment_models(name='MyEquipmentModel')

    Find all EquipmentModels which either have the name 'MyEquipmentModel' or the name 'MyOtherEquipmentModel'::

        find_equipment_models(name=['MyEquipmentModel', 'MyOtherEquipmentModel'])


    If multiple named arguments are provided then *all* conditions have to match.

    Example
    -------
    Find all EquipmentModels with name 'MyEquipmentModel' which also have the short description 'Description'::

        find_equipment_models(name='MyEquipmentModel', short_description='Description')

    The ``extended_filters`` parameter can be used to specify filters that can not be expressed as an equality. Each
    extended_filter needs to be provided as a string, multiple filters can be passed as a list of strings. As above,
    all filter criteria need to match. Inequality filters can be freely combined with named arguments. Here, too, all
    filter criteria need to match for an EquipmentModel to be returned.

    Example
    -------
    Find all EquipmentModels with an expiration date before January 1, 2018::

        find_equipment_models(extended_filters=['model_expiration_date < "2018-01-01"'])
    """
    unbreakable_filters, breakable_filters = \
        _parse_filter_parameters(kwargs, extended_filters, EquipmentModel.get_property_mapping())

    endpoint_url = _ac_application_url() + EQUIPMENT_MODEL_API
    object_list = _fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    return EquipmentModelSet([EquipmentModel(obj) for obj in object_list],
                             {'filters': kwargs, 'extended_filters': extended_filters})
