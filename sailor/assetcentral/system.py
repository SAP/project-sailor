"""
System module can be used to retrieve System information from AssetCentral.

Classes are provided for individual Systems as well as groups of Systems (SystemSet).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Union
from datetime import datetime

import pandas as pd

from sailor import sap_iot
from .utils import _fetch_data, _add_properties, _parse_filter_parameters, AssetcentralEntity, ResultSet, \
    _ac_application_url
from .equipment import find_equipment, EquipmentSet
from .indicators import IndicatorSet
from .constants import VIEW_SYSTEMS

if TYPE_CHECKING:
    from ..sap_iot import TimeseriesDataset


@_add_properties
class System(AssetcentralEntity):
    """AssetCentral System Object."""

    # Properties (in AC terminology) are: systemId, internalId, status, systemStatusDescription, modelID, modelVersion,
    # model, shortDescription, templateID, systemProvider, systemVersion, createdOn, changedOn, source, imageURL,
    # className, classID, subclass, subclassID, systemProviderID, sourceSearchTerms, systemProviderSearchTerms,
    # publishedOn, operator, operatorID, completeness

    def __init__(self, ac_json):
        """Create a new System object and fetch all components."""
        self.raw = ac_json
        self._prepare_components()

    @classmethod
    def get_property_mapping(cls):
        """Return a mapping from assetcentral terminology to our terminology."""
        return {
            'id': ('systemId', None, None, None),
            'name': ('internalId', None, None, None),
            'short_description': ('shortDescription', None, None, None),
            'class_name': ('className', None, None, None),
            'model_id': ('modelID', None, None, None),
            'model_name': ('model', None, None, None),
            'status_text': ('systemStatusDescription', None, None, None),
            'template_id': ('templateID', None, None, None),
        }

    def _prepare_components(self):
        endpoint_url = _ac_application_url() + VIEW_SYSTEMS + f'({self.id})' + '/components'
        components = _fetch_data(endpoint_url)[0]
        equipment_ids = []

        for child_node in components['childNodes']:
            if child_node['objectType'] != 'EQU':  # SYS or EQU are currently possible
                raise RuntimeError('Only single-level system hierarchies are currently supported.')
            equipment_ids.append(child_node['id'])

        if equipment_ids:
            self.components = find_equipment(id=equipment_ids)
        else:
            self.components = EquipmentSet([])

    def get_indicator_data(self, start: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                           end: Union[str, pd.Timestamp, datetime.timestamp, datetime.date]) -> TimeseriesDataset:
        """
        Get timeseries data for all Equipment in the System.

        This is a wrapper for :meth:`sailor.sap_iot.fetch.get_indicator_data` that limits the fetch query
        to the equipment in this System.

        Each component equipment will be returned as separate rows in the dataset,
        potentially making the dataset very sparse.


        Parameters
        ----------
        start
            Begin of time series data.
        end
            End of time series data.
        """
        all_indicators = sum((equipment.find_equipment_indicators() for equipment in self.components), IndicatorSet([]))
        return sap_iot.get_indicator_data(start, end, all_indicators, self.components)


class SystemSet(ResultSet):
    """Class representing a group of Systems."""

    _element_type = System
    _method_defaults = {
        'plot_distribution': {
            'by': 'model_name',
        },
    }

    def get_indicator_data(self, start: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                           end: Union[str, pd.Timestamp, datetime.timestamp, datetime.date]) -> TimeseriesDataset:
        """
        Fetch data for a set of systems for all component equipment of each system.

        This is a wrapper for :meth:`sailor.sap_iot.fetch.get_indicator_data` that limits the fetch query
        to the equipment in this SystemSet.

        Similar to ``System.get_indicator_data`` each component will be returned as separate rows in the dataset,
        potentially making the dataset very sparse.

        Parameters
        ----------
        start
            Begin of time series data.
        end
            End of time series data.
        """
        all_equipment = sum((system.components for system in self), EquipmentSet([]))
        all_indicators = sum((equipment.find_equipment_indicators() for equipment in all_equipment), IndicatorSet([]))

        return sap_iot.get_indicator_data(start, end, all_indicators, all_equipment)


def find_systems(*, extended_filters=(), **kwargs) -> SystemSet:
    """Fetch Systems from AssetCentral with the applied filters, return an SystemSet.

    This method supports the usual filter criteria, i.e.
    - Any named keyword arguments applied as equality filters, i.e. the name of the System property is checked
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
     Find all Systems with name 'MySystem'::

        find_systems(name='MySystem')

    Find all Systems which either have the name 'MySystem' or the name 'MyOtherSystem'::

        find_systems(name=['MySystem', 'MyOtherSystem'])

    If multiple named arguments are provided then *all* conditions have to match.

    Example
    -------
    Find all Systems with name 'MySystem' which also is published (status_text = 'Published')::

        find_systems(name='MySystem', status_text='Published')

    The ``extended_filters`` parameter can be used to specify filters that can not be expressed as an equality. Each
    extended_filter needs to be provided as a string, multiple filters can be passed as a list of strings. As above,
    all filter criteria need to match. Extended filters can be freely combined with named arguments. Here, too all
    filter criteria need to match for a System to be returned.

    Example
    -------
    Find all Systems with creation date higher or equal to 01.01.2020::

        find_systems(extended_filters=['created_on >= "2020-01-01"'])
    """
    unbreakable_filters, breakable_filters = \
        _parse_filter_parameters(kwargs, extended_filters, System.get_property_mapping())

    endpoint_url = _ac_application_url() + VIEW_SYSTEMS
    object_list = _fetch_data(endpoint_url, unbreakable_filters, breakable_filters)

    return SystemSet([System(obj) for obj in object_list],
                     {'filters': kwargs, 'extended_filters': extended_filters})
