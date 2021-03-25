"""
System module can be used to retrieve System information from AssetCentral.

Classes are provided for individual Systems as well as groups of Systems (SystemSet).
"""
from typing import Union
from datetime import datetime
from functools import cached_property

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
        """Create a new System object."""
        self.raw = ac_json

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
    def _sort_children(component):
        """Sort child_nodes of `component` by order attribute.

        Dictionary component is not sorted by order number
        Hence, we have to sort - we do this in a data frame
        First, we sort by [model, order] to get order within model into column 'model_order'
        Second, we sort by order to have the correct order in the component dictionary
        """
        name, order, id, model, row = [], [], [], [], []
        r = 0
        for child in component['childNodes']:
            name.append(child['name'])
            order.append(child['order'])
            id.append(child['id'])
            model.append(child['model'])
            row.append(r)
            r += 1
        compdf = pd.DataFrame(list(zip(name, id, order, model, row)), columns=['name', 'id', 'order', 'model', 'row'])
        compdf['one'] = 1
        compdf.sort_values(by=['model', 'order'], inplace=True)
        compdf['model_order'] = compdf.groupby(['model']).agg(rank=('one', 'cumsum'))
        compdf.sort_values(by='order', inplace=True)
        return compdf

    @staticmethod
    def _traverse_components(component, model_order, equipment_ids, system_ids):
        """Traverse component structure recursively, starting from `component`."""
        compd = {}
        compd['key'] = (component['model'], model_order)
        compd['id'] = component['id']
        compd['name'] = component['name']
        compd['order'] = component['order']
        if component['order'] is not None:
            if component['objectType'] == 'EQU':
                equipment_ids.append(component['id'])
            else:
                system_ids.append(component['id'])
        compd['object_type'] = component['objectType']
        compdf = System._sort_children(component)
        if len(compdf) > 0:
            compd['child_list'] = []
            for c in range(len(compdf)):
                row = compdf.iloc[c]['row']
                model_order = compdf.iloc[c]['model_order']
                compd0, equipment_ids, system_ids = System._traverse_components(component['childNodes'][row],
                                                                                model_order, equipment_ids, system_ids)
                compd['child_list'].append(compd0)
        return compd, equipment_ids, system_ids

    def _update_components(self, component):
        if component['object_type'] == 'EQU':
            obj = self._equipments.filter(id=component['id'])[0]
            component['indicators'] = self._indicators[component['id']]
        else:
            if component['id'] == self.id:
                obj = self
            else:
                obj = self._systems.filter(id=component['id'])[0]
        component['key'] = (obj.model_id, component['key'][1])
        if 'child_list' in component.keys():
            component['child_nodes'] = {}
            for child in component['child_list']:
                self._update_components(child)
                component['child_nodes'][child['key']] = child
            del component['child_list']

    @cached_property
    def components(self):
        endpoint_url = _ac_application_url() + VIEW_SYSTEMS + f'({self.id})' + '/components'
        comps = _fetch_data(endpoint_url)[0]
        self._components, equipment_ids, system_ids = System._traverse_components(comps, 1, [], [])
        if system_ids:
            self._systems = find_systems(id=system_ids)
        else:
            self._systems = SystemSet([])
        self._indicators = {}
        if equipment_ids:
            self._equipments = find_equipment(id=equipment_ids)
            for equi in self._equipments:
                self._indicators[equi.id] = equi.find_equipment_indicators(type='Measured')
        else:
            self._equipments = EquipmentSet([])
        self._update_components(self._components)
        return self._components

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

    @staticmethod
    def _map_comp_info(sel_nodes, sys_nodes, indicator_list):
        for node in sel_nodes:
            if node['object_type'] == 'EQU':
                for i in node['indicators']:
                    if i in sys_nodes[node['key']]['indicators']:
                        indicator_list.append((sys_nodes[node['key']]['id'], i))
                    else:
                        indicator_list.append(None)
            if 'child_nodes' in node.keys():
                SystemSet._map_comp_info(node['child_nodes'], sys_nodes[node['key']]['child_nodes'], indicator_list)

    def map_component_information(self, selection):
        """Map selection dictionary against component dictionary of systems in a system set."""
        system_indicators = {}
        for system in self:
            indicator_list = []
            SystemSet._map_comp_info(selection['child_nodes'], system.components['child_nodes'], indicator_list)
            system_indicators[system.id] = indicator_list
        return system_indicators


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
