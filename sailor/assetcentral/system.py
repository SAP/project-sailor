"""
System module can be used to retrieve System information from AssetCentral.

Classes are provided for individual Systems as well as groups of Systems (SystemSet).
"""
from __future__ import annotations

import itertools
# import warnings
from typing import TYPE_CHECKING, Union
from datetime import datetime
from functools import cached_property
from operator import itemgetter

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
    def _traverse_components(component, model_order, equipment_ids, system_ids):
        """Traverse component structure recursively, starting from `component`. Pydocstyle does not know punctuation."""
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
        if 'childNodes' in component.keys():
            component['childNodes'] = sorted(component['childNodes'], key=itemgetter('model', 'order'))
            compd['child_list'] = []
            for _, comps_by_model in itertools.groupby(component['childNodes'], itemgetter('model')):
                for model_order, c in enumerate(comps_by_model):
                    compd0, equipment_ids, system_ids = System._traverse_components(c, model_order,
                                                                                    equipment_ids, system_ids)
                    compd['child_list'].append(compd0)
            compd['child_list'] = sorted(compd['child_list'], key=itemgetter('order'))
        return compd, equipment_ids, system_ids

    def _update_components(self, component):
        """Add indicators and replace id with model_id in the key."""
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
                del component['child_nodes'][child['key']]['key']
            del component['child_list']

    @cached_property
    def _component_tree(self):
        """Prepare component tree and cache it."""
        endpoint_url = _ac_application_url() + VIEW_SYSTEMS + f'({self.id})' + '/components'
        comps = _fetch_data(endpoint_url)[0]
        self._components, equipment_ids, system_ids = System._traverse_components(comps, 0, [], [])
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
        del self._components['key']
        return self._components

    @cached_property
    def components(self):
        """Pieces of equipment that are children of the system.

        Only top level, lower levels are ignored
        """
        # warnings.warn("deprecated: attribute will be removed as soon as multilevel system hierarchies are supported",
        #              FutureWarning)
        equipment_ids = set()
        comp_tree = self._component_tree
        for c in comp_tree['child_nodes']:
            if comp_tree['child_nodes'][c]['object_type'] == 'EQU':
                equipment_ids.add(comp_tree['child_nodes'][c]['id'])
        return self._equipments.filter(id=equipment_ids)

    @staticmethod
    def _create_selection_dictionary(comp_tree):
        """Create a selection dictionary recursively based on 'comp_tree.' Pydocstyle does not know punctuation."""
        selection = {}
        selection['object_type'] = comp_tree['object_type']
        if comp_tree['object_type'] == 'EQU':
            selection['indicators'] = comp_tree['indicators']
        if 'child_nodes' in comp_tree.keys():
            selection['child_nodes'] = []
            for child in comp_tree['child_nodes']:
                sel = System._create_selection_dictionary(comp_tree['child_nodes'][child])
                sel['key'] = child
                selection['child_nodes'].append(sel)
        return selection

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

    @staticmethod
    def _fill_nones(sel_nodes, indicator_list, none_positions):
        """Fill None for indicators of missing subtrees recursively."""
        for node in sel_nodes:
            if node['object_type'] == 'EQU':
                for indicator in node['indicators']:
                    none_positions.add(len(indicator_list))
                    indicator_list.append(None)
            if 'child_nodes' in node.keys():
                SystemSet._fill_nones(node['child_nodes'], indicator_list, none_positions)

    @staticmethod
    def _map_comp_info(sel_nodes, sys_nodes, indicator_list, none_positions):
        """Map selection dictionary against component dictionary recursively."""
        for node in sel_nodes:
            if node['object_type'] == 'EQU':
                for indicator in node['indicators']:
                    if (node['key'] in sys_nodes.keys()) and (indicator in sys_nodes[node['key']]['indicators']):
                        indicator_list.append((sys_nodes[node['key']]['id'], indicator))
                    else:
                        none_positions.add(len(indicator_list))
                        indicator_list.append(None)
            if 'child_nodes' in node.keys():
                if node['key'] in sys_nodes.keys():
                    SystemSet._map_comp_info(node['child_nodes'], sys_nodes[node['key']]['child_nodes'],
                                             indicator_list, none_positions)
                else:
                    SystemSet._fill_nones(node['child_nodes'], indicator_list, none_positions)

    def _map_component_information(self, selection):
        """Map selection dictionary against component dictionary of systems in a system set."""
        system_indicators = {}
        none_positions = set()
        intersection = False
        if len(selection) == 0:
            # build selection dictionary from one of the systems
            intersection = True
            selection = System._create_selection_dictionary(self[0]._component_tree)
        for system in self:
            indicator_list = []
            SystemSet._map_comp_info(selection['child_nodes'], system._component_tree['child_nodes'],
                                     indicator_list, none_positions)
            system_indicators[system.id] = indicator_list
        if intersection:
            # keep only indicators that appear for all systems
            none_positions = list(none_positions)[::-1]
            for system in self:
                for p in none_positions:
                    del system_indicators[system.id][p]
        return system_indicators


def find_systems(*, extended_filters=(), **kwargs) -> SystemSet:
    """Fetch Systems from AssetCentral with the applied filters, return a SystemSet.

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
