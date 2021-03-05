"""
System module can be used to retrieve System information from AssetCentral.

Classes are provided for individual Systems as well as groups of Systems (SystemSet).
"""
from typing import Union
from datetime import datetime

import pandas as pd

from .utils import _fetch_data, _add_properties, _parse_filter_parameters, AssetcentralEntity, ResultSet, \
    _ac_application_url
from .equipment import find_equipment, EquipmentSet
from .indicators import IndicatorSet
from .constants import VIEW_SYSTEMS
from ..sap_iot import get_indicator_data, TimeseriesDataset


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

    @staticmethod
    def _sort_components(comps):
        """Sort components by order attribute.

        Dictionary comps is not sorted by order number
        Hence, we have to sort - we do this in a data frame
        First, we sort by [model, order] to get order within model into column 'model_order'
        Second, we sort by order to have the correct order in the component dictionary
        """
        name, order, id, model, row = [], [], [], [], []
        r = 0
        for c in comps['childNodes']:
            name.append(c['name'])
            order.append(c['order'])
            id.append(c['id'])
            model.append(c['model'])
            row.append(r)
            r += 1
        compdf = pd.DataFrame(list(zip(name, id, order, model, row)), columns=['name', 'id', 'order', 'model', 'row'])
        compdf['one'] = 1
        compdf.sort_values(by=['model', 'order'], inplace=True)
        compdf['model_order'] = compdf.groupby(['model']).agg(rank=('one', 'cumsum'))
        compdf.sort_values(by='order', inplace=True)
        return compdf

    @staticmethod
    def _traverse_components(comps, model_order, equipment_ids, system_ids):
        """Traverse component structure recursively."""
        compd = {}
        compd['id'] = comps['id']
        compd['name'] = comps['name']
        if comps['order'] is not None:
            if comps['objectType'] == 'EQU':
                equipment_ids.append(compd['id'])
            else:
                system_ids.append(compd['id'])
        compd['key'] = (comps['model'], model_order)
        compd['object_type'] = comps['objectType']
        compdf = System._sort_components(comps)
        if len(compdf) > 0:
            compd['child_nodes'] = []
            for c in range(len(compdf)):
                row = compdf.iloc[c]['row']
                model_order = compdf.iloc[c]['model_order']
                compd0, equipment_ids, system_ids = System._traverse_components(comps['childNodes'][row], model_order,
                                                                                equipment_ids, system_ids)
                compd['child_nodes'].append(compd0)
        return compd, equipment_ids, system_ids

    def _update_dictionary(self, comps):
        if comps['object_type'] == 'EQU':
            obj = self.equipments.filter(id=comps['id'])[0]
            comps['indicators'] = self.indicators[comps['id']]
        else:
            if comps['id'] == self.id:
                obj = self
            else:
                obj = self.systems.filter(id=comps['id'])[0]
        comps['key'] = (obj.model_id, comps['key'][1])
        if 'child_nodes' in comps.keys():
            for c in comps['child_nodes']:
                self._update_dictionary(c)

    def _prepare_components(self):
        endpoint_url = _ac_application_url() + VIEW_SYSTEMS + f'({self.id})' + '/components'
        components = _fetch_data(endpoint_url)[0]
        self.components, equipment_ids, system_ids = System._traverse_components(components, 1, [], [])
        if system_ids:
            self.systems = find_systems(id=system_ids)
        else:
            self.systems = SystemSet([])
        self.indicators = {}
        if equipment_ids:
            self.equipments = find_equipment(id=equipment_ids)
            for equi in self.equipments:
                self.indicators[equi.id] = equi.find_equipment_indicators(type='Measured')
        else:
            self.equipments = EquipmentSet([])
        self._update_dictionary(self.components)

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
        return get_indicator_data(start, end, all_indicators, self.components)


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

        return get_indicator_data(start, end, all_indicators, all_equipment)


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
