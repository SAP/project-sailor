"""
System module can be used to retrieve System information from AssetCentral.

Classes are provided for individual Systems as well as groups of Systems (SystemSet).
"""
from __future__ import annotations

import math
import itertools
import logging
from typing import Union
from datetime import datetime
from functools import cached_property
from operator import itemgetter

import pandas as pd

from sailor import _base, sap_iot
from sailor.sap_iot.wrappers import TimeseriesDataset
from sailor.utils.utils import WarningAdapter
from .utils import (AssetcentralEntity, _AssetcentralField, AssetcentralEntitySet,
                    _ac_application_url, _ac_fetch_data)
from .equipment import find_equipment, EquipmentSet
from .indicators import (IndicatorSet, SystemIndicator, SystemAggregatedIndicator, AggregatedIndicatorSet,
                         SystemIndicatorSet, SystemAggregatedIndicatorSet)
from .constants import VIEW_SYSTEMS


_SYSTEM_FIELDS = [
    _AssetcentralField('name', 'internalId'),
    _AssetcentralField('model_name', 'model',
                       query_transformer=_base.masterdata._qt_non_filterable('model_name')),
    _AssetcentralField('status_text', 'systemStatusDescription',
                       query_transformer=_base.masterdata._qt_non_filterable('status_text')),
    _AssetcentralField('short_description', 'shortDescription'),
    _AssetcentralField('class_name', 'className'),
    _AssetcentralField('id', 'systemId'),
    _AssetcentralField('model_id', 'modelID',
                       query_transformer=_base.masterdata._qt_non_filterable('model_id')),
    _AssetcentralField('template_id', 'templateID',
                       query_transformer=_base.masterdata._qt_non_filterable('template_id')),
    _AssetcentralField('_status', 'status'),
    _AssetcentralField('_model_version', 'modelVersion'),
    _AssetcentralField('_system_provider', 'systemProvider'),
    _AssetcentralField('_system_version', 'systemVersion'),
    _AssetcentralField('_created_on', 'createdOn'),
    _AssetcentralField('_changed_on', 'changedOn'),
    _AssetcentralField('_published_on', 'publishedOn'),
    _AssetcentralField('_source', 'source'),
    _AssetcentralField('_image_URL', 'imageURL'),
    _AssetcentralField('_class_id', 'classID'),
    _AssetcentralField('_subclass', 'subclass'),
    _AssetcentralField('_subclass_id', 'subclassID'),
    _AssetcentralField('_system_provider_id', 'systemProviderID'),
    _AssetcentralField('_source_search_terms', 'sourceSearchTerms'),
    _AssetcentralField('_system_provider_search_terms', 'systemProviderSearchTerms'),
    _AssetcentralField('_operator', 'operator'),
    _AssetcentralField('_operator_id', 'operatorID'),
    _AssetcentralField('_completeness', 'completeness'),
]

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())
LOG = WarningAdapter(LOG)


@_base.add_properties
class System(AssetcentralEntity):
    """AssetCentral System Object."""

    _field_map = {field.our_name: field for field in _SYSTEM_FIELDS}

    @staticmethod
    def _traverse_components(component, model_order, equipment_ids, system_ids):
        """Traverse component structure recursively, starting from 'component.' Pydocstyle does not know punctuation."""
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
            obj = self.__hierarchy['equipment'].filter(id=component['id'])[0]
            component['indicators'] = self.__hierarchy['indicators'][component['id']]
        else:
            if component['id'] == self.id:
                obj = self
            else:
                obj = self.__hierarchy['systems'].filter(id=component['id'])[0]
        component['key'] = (obj.model_id, component['key'][1])
        if 'child_list' in component.keys():
            component['child_nodes'] = {}
            for child in component['child_list']:
                self._update_components(child)
                component['child_nodes'][child['key']] = child
                del component['child_nodes'][child['key']]['key']
            del component['child_list']

    @cached_property
    def _hierarchy(self):
        """Prepare component tree and cache it."""
        endpoint_url = _ac_application_url() + VIEW_SYSTEMS + f'({self.id})' + '/components'
        comps = _ac_fetch_data(endpoint_url)[0]
        self.__hierarchy = {}
        self.__hierarchy['component_tree'], equipment_ids, system_ids = System._traverse_components(comps, 0, [], [])
        if system_ids:
            self.__hierarchy['systems'] = find_systems(id=system_ids)
        else:
            self.__hierarchy['systems'] = SystemSet([])
        self.__hierarchy['indicators'] = {}
        if equipment_ids:
            self.__hierarchy['equipment'] = find_equipment(id=equipment_ids)
            for equi in self.__hierarchy['equipment']:
                self.__hierarchy['indicators'][equi.id] = equi.find_equipment_indicators(type='Measured')
        else:
            self.__hierarchy['equipment'] = EquipmentSet([])
        self._update_components(self.__hierarchy['component_tree'])
        del self.__hierarchy['component_tree']['key']
        return self.__hierarchy

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

    @staticmethod
    def _find_first_equipment(comp_tree, level, equi_id, equi_level):
        """Find first equipment on highest level of a tree recursively."""
        for child in comp_tree['child_nodes']:
            if comp_tree['child_nodes'][child]['object_type'] == 'EQU':
                return comp_tree['child_nodes'][child]['id'], level
            else:
                if (level + 1) < equi_level:
                    equi_id, equi_level = System._find_first_equipment(comp_tree['child_nodes'][child], level+1,
                                                                       equi_id, equi_level)
        return equi_id, equi_level

    def get_leading_equipment(self, path=[]):
        """Get leading piece of equipment (by path or default)."""
        if path:
            child_nodes = self._hierarchy['component_tree']['child_nodes']
            for p in path:
                object_id = child_nodes[p]['id']
                child_nodes = child_nodes[p]['child_nodes']
            return object_id
        else:
            # no path given: find first equipment on highest level
            # looks like a breadth-first search problem, but DFS is more efficient
            equi_id, equi_level = System._find_first_equipment(self._hierarchy['component_tree'], 0, 0, math.inf)
            return equi_id

    def get_indicator_data(self, start: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                           end: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                           indicator_set: IndicatorSet = None, *,
                           timeout: Union[str, pd.Timedelta, datetime.timedelta] = None) -> TimeseriesDataset:
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
        indicator_set
            IndicatorSet for which timeseries data is returned.
        timeout
            Maximum amount of time the request may take. Can be specified as an ISO 8601 string
            (like `PT2M` for 2-minute duration) or as a pandas.Timedelta or datetime.timedelta object.
            If None, there is no time limit.
        """
        if indicator_set is None:
            indicator_set = sum((equi.find_equipment_indicators() for equi in self._hierarchy['equipment']),
                                IndicatorSet([]))

        LOG.debug('Requesting indicator data of system "%s" for %d indicators.', self.id, len(indicator_set))
        return sap_iot.get_indicator_data(start, end, indicator_set, self._hierarchy['equipment'], timeout=timeout)


class SystemSet(AssetcentralEntitySet):
    """Class representing a group of Systems."""

    _element_type = System
    _method_defaults = {
        'plot_distribution': {
            'by': 'model_name',
        },
    }

    def get_indicator_data(self, start: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                           end: Union[str, pd.Timestamp, datetime.timestamp, datetime.date],
                           indicator_set: IndicatorSet = None, *,
                           timeout: Union[str, pd.Timedelta, datetime.timedelta] = None) -> TimeseriesDataset:
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
        indicator_set
            IndicatorSet for which timeseries data is returned.
        timeout
            Maximum amount of time the request may take. Can be specified as an ISO 8601 string
            (like `PT2M` for 2-minute duration) or as a pandas.Timedelta or datetime.timedelta object.
            If None, there is no time limit.
        """
        all_equipment = sum((system._hierarchy['equipment'] for system in self), EquipmentSet([]))
        if indicator_set is None:
            indicator_set = sum((equipment.find_equipment_indicators() for equipment in all_equipment),
                                IndicatorSet([]))
        LOG.debug("Requesting indicator data of system set for %d equipments and %d indicators.",
                  len(all_equipment), len(indicator_set))
        return sap_iot.get_indicator_data(start, end, indicator_set, all_equipment, timeout=timeout)

    @staticmethod
    def _fill_nones(sel_nodes, indicator_list, none_positions, equi_counter):
        """Fill None for indicators of missing subtrees recursively."""
        for node in sel_nodes:
            if node['object_type'] == 'EQU':
                equi_counter += 1
                for indicator in node['indicators']:
                    none_positions.add(len(indicator_list))
                    indicator_list.append(None)
            if 'child_nodes' in node.keys():
                equi_counter = SystemSet._fill_nones(node['child_nodes'], indicator_list, none_positions, equi_counter)
        return equi_counter

    @staticmethod
    def _map_comp_info(sel_nodes, sys_nodes, indicator_list, none_positions, equipment, equi_counter):
        """Map selection dictionary against component dictionary recursively."""
        for node in sel_nodes:
            if node['object_type'] == 'EQU':
                if (node['key'] in sys_nodes.keys()):
                    equipment[sys_nodes[node['key']]['id']] = equi_counter
                equi_counter += 1
                for indicator in node['indicators']:
                    if (node['key'] in sys_nodes.keys()) and (indicator in sys_nodes[node['key']]['indicators']):
                        indicator_list.append((sys_nodes[node['key']]['id'], indicator))
                    else:
                        none_positions.add(len(indicator_list))
                        indicator_list.append(None)
            if 'child_nodes' in node.keys():
                if node['key'] in sys_nodes.keys():
                    equi_counter = SystemSet._map_comp_info(node['child_nodes'], sys_nodes[node['key']]['child_nodes'],
                                                            indicator_list, none_positions, equipment, equi_counter)
                else:
                    equi_counter = SystemSet._fill_nones(node['child_nodes'], indicator_list, none_positions,
                                                         equi_counter)
        return equi_counter

    def _map_component_information(self, selection={}):
        """Map selection dictionary against component dictionary of systems in a system set.

        system_indicators: dictionary of selected indicators
        system_equipment: dictionary of pieces of equipment and their positions
        """
        system_indicators = {}
        system_equipment = {}
        none_positions = set()
        intersection = False
        if len(selection) == 0:
            # build selection dictionary from one of the systems
            intersection = True
            selection = System._create_selection_dictionary(self[0]._hierarchy['component_tree'])
        for system in self:
            indicator_list = []
            equipment = {}
            equi_counter = 0
            equi_counter = SystemSet._map_comp_info(selection['child_nodes'],
                                                    system._hierarchy['component_tree']['child_nodes'],
                                                    indicator_list, none_positions, equipment, equi_counter)
            system_indicators[system.id] = indicator_list
            system_equipment[system.id] = equipment
        if intersection:
            # keep only indicators that appear for all systems
            none_positions = list(none_positions)[::-1]
            for system in self:
                for p in none_positions:
                    del system_indicators[system.id][p]
            # keep only pieces of equipment for relevant indicators
            keep_equi = set()
            for indicator in system_indicators[self[0].id]:
                keep_equi.add(indicator[0])
            equi_map = {}
            c = 0
            for equi in system_equipment[self[0].id]:
                if equi in keep_equi:
                    equi_map[system_equipment[self[0].id][equi]] = c
                    c += 1
            sys_equipment = {}
            for system in self:
                equipment = {}
                for equi in system_equipment[system.id]:
                    if system_equipment[system.id][equi] in equi_map.keys():
                        equipment[equi] = equi_map[system_equipment[system.id][equi]]
                sys_equipment[system.id] = equipment
            system_equipment = sys_equipment
        return system_indicators, system_equipment

    def _get_leading_equipment_and_equipment_counter(self, system_equipment, lead_equi_path=[]):
        """Get leading equipment and equipment counter."""

        def equi_counter(equi_id, sys):
            """Get equipment counter (function makes apply() nicer)."""
            if equi_id in system_equipment[sys].keys():
                return system_equipment[sys][equi_id]
            else:
                return -1

        # get leading piece of equipment for every piece of equipment in the hierarchy trees of a system set
        for i in range(len(self)):
            eq = self[i]._hierarchy['equipment'].as_df()[['id']]
            eq.rename(columns={"id": "equipment_id"}, inplace=True)
            eq['leading_equipment'] = self[i].get_leading_equipment(lead_equi_path)
            eq['equi_counter'] = eq.equipment_id.apply(equi_counter, sys=self[i].id)
            if i == 0:
                equi_info = eq
            else:
                equi_info = equi_info.append(eq)
        # category gets lost in append(), so we have to do it here, copy = False does not work
        return equi_info.astype({'equipment_id': 'category', 'leading_equipment': 'category'})


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
        _base.parse_filter_parameters(kwargs, extended_filters, System._field_map)

    endpoint_url = _ac_application_url() + VIEW_SYSTEMS
    object_list = _ac_fetch_data(endpoint_url, unbreakable_filters, breakable_filters)
    LOG.debug('Found %d systems for the specified filters.', len(object_list))

    return SystemSet([System(obj) for obj in object_list])


def create_analysis_table(system_set: SystemSet, indicator_data: TimeseriesDataset, system_equipment,
                          leading_equipment_path=[]):
    """Create analysis table for a system set.

    An analysis table is a table in which each row contains all indicator data that are valid for a system and a
    timestamp. The system is represented by its leading piece of equipment. The data columns are represented by
    SystemIndicators or SystemAggregatedIndicators, i.e. their key consists of information about the indicator,
    the equipment counter, and for SystemAggregatedIndicators the aggregation function.

    Parameters
    ----------
    system_set: Set of systems for which data is collected
    indicator_data: TimeseriesDataset containing the relevant indicator data
    system_equipment: dictionary that contains the equipment id and a counter, which is used to distinguish multiple
    occurrences of an equipment model in a system, for the relevant pieces of equipment that are assigned to a system
    leading_equipment_path: path to the leading piece of equipment of a system
    """
    equi_info = system_set._get_leading_equipment_and_equipment_counter(system_equipment, leading_equipment_path)
    agg = isinstance(indicator_data.indicator_set, AggregatedIndicatorSet)
    id_df = indicator_data.as_df(speaking_names=False).reset_index()
    # join with leading equipment
    id_df = id_df.merge(equi_info)
    # drop equipment id
    id_df.drop(['equipment_id'], axis=1, inplace=True)
    id_df.rename(columns={'leading_equipment': 'equipment_id'}, inplace=True)
    # create really long format
    long = id_df.melt(id_vars=['timestamp', 'equipment_id', 'equi_counter'])
    long = long[long.equi_counter >= 0]
    # get rid of NAs
    long = long.dropna(subset=['value'])
    # create wide format
    wide = long.pivot(index=['equipment_id', 'timestamp'], columns=['variable', 'equi_counter'])
    # create columns and System(Aggregated)Indicators
    columns = []
    rawmap = indicator_data._indicator_set._unique_id_to_raw()
    sysindlist = []
    for c in wide.columns:
        if agg:
            sysind = SystemAggregatedIndicator(rawmap[c[1]][0], rawmap[c[1]][1], c[2])
        else:
            sysind = SystemIndicator(rawmap[c[1]], c[2])
        sysindlist.append(sysind)
        columns.append(sysind._unique_id)
    if agg:
        sysindset = SystemAggregatedIndicatorSet(sysindlist)
    else:
        sysindset = SystemIndicatorSet(sysindlist)
    wide.columns = columns
    wide.reset_index(inplace=True)
    equipment_set = EquipmentSet([e for e in indicator_data.equipment_set
                                  if e.id in list(id_df['equipment_id'].unique())])
    return sap_iot.TimeseriesDataset(wide, sysindset, equipment_set, indicator_data.nominal_data_start,
                                     indicator_data.nominal_data_end)
