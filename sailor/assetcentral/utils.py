"""Module for various utility functions, in particular those related to fetching data from remote oauth endpoints."""

from copy import deepcopy
from typing import Union
from collections.abc import Sequence, Iterable
from collections import Counter, UserDict
from itertools import product
import operator
import logging
import warnings
import re

import pandas as pd
import plotnine as p9

from ..utils.oauth_wrapper import get_oauth_client
from ..utils.plot_helper import _default_plot_theme
from ..utils.config import SailorConfig
from ..utils.utils import DataNotFoundWarning

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


def _compose_queries(unbreakable_filters, breakable_filters):
    # So the AC endpoints can only accept a certain URL length
    # and since the filters are part of the URL for GET requests
    # we have to make sure the query doesn't get too long.
    # Assume we have a query like (A AND B AND (C OR D) AND (E OR F OR G))
    # (where the 'OR' terms can become quite long).
    # The shortest way to break this up is into a number of sequential query
    # like ((A AND B AND C AND E) OR (A AND B AND C AND F) OR ...) where we can
    # break on each OR.
    # If any of these individual terms is longer than the allowed length we can't
    # execute the query.
    #
    # However, while this way of breaking it gives us the shortest possible URLs
    # it also gives us the largest amount of queries. So it would be better to break
    # it into e.g. ((A AND B AND (C OR D) AND (E OR F)) OR (A AND B AND (C OR D) AND G)
    # which gives us two queries. Unfortunately I can't think of a sane (and non-exponential)
    # algorithms to find this optimal breakup.
    #
    # So my compromise is to include all the (OR) groups that can fit as a whole in the query,
    # and to break the remaining part up into cartesian products.

    if not (unbreakable_filters or breakable_filters):
        return []

    max_filter_length = 2000

    filter_string = ' and '.join(unbreakable_filters)
    current_fixed_length = len(filter_string)

    cartesian_product = set(product(*breakable_filters))
    remaining_cartesian_length_max = max(len(' and '.join(p)) for p in cartesian_product)

    if max_filter_length < current_fixed_length + remaining_cartesian_length_max + len(' and '):
        raise RuntimeError('Your filter conditions are too complex. Please split your query into multiple calls.')

    breakable_filters = sorted(breakable_filters, key=len)

    # add entire groups for as long as we can
    for idx in range(len(breakable_filters)):
        subfilter = '(' + ' or '.join(breakable_filters[idx]) + ')'
        cartesian_product = set(product(*breakable_filters[(idx + 1):]))
        remaining_cartesian_length_max = max(len(' and '.join(p)) for p in cartesian_product)

        if max_filter_length > len(subfilter) + current_fixed_length + remaining_cartesian_length_max + 2*len(' and '):
            filter_string = ' and '.join([filter_string, subfilter])
            if filter_string.startswith(' and '):
                filter_string = filter_string[5:]
            current_fixed_length = len(filter_string)
        else:
            LOG.debug('Can not fit next filter term completely, breaking at %s', idx)
            break
    else:
        # did not break, so we could process all breakable filters here
        return [filter_string]

    # add everything that's left as cartesian product
    # as a small optimisation: everything but the *last* group.
    # we'll split the last group again, to fill up the space
    # we have as much as possible
    if idx < len(breakable_filters) - 1:  # more than one group left
        cartesian_product = set(product(*breakable_filters[idx:-1]))
        filters = [filter_string + ' and ' + ' and '.join(p) for p in cartesian_product]
    else:
        filters = [filter_string]

    # now we add the last group, in chunks
    if idx < len(breakable_filters):
        current_max_length = max(len(query) for query in filters)
        remaining_length = max_filter_length - current_max_length - len(' and ')
        filter_group = breakable_filters[-1]

        result = []
        start_idx = 0
        end_idx = 2
        while end_idx <= len(filter_group):
            subfilter = '(' + ' or '.join(filter_group[start_idx:end_idx]) + ')'

            # this one is too long, we need to break one before
            if len(subfilter) > remaining_length:
                last_subfilter = '(' + ' or '.join(filter_group[start_idx:(end_idx - 1)]) + ')'
                result.extend(q + ' and ' + last_subfilter if q != '' else last_subfilter for q in filters)
                # this one is too long, but also the last element
                # since we had to break, we have to add the last element separately
                if end_idx == len(filter_group):
                    result.extend(q + ' and ' + filter_group[-1] for q in filters)
                    break
                else:
                    start_idx = end_idx - 1

            # we've reached the and, but didn't neet to break. add everything we have left
            if end_idx == len(filter_group):
                result.extend(q + ' and ' + subfilter if q != '' else subfilter for q in filters)
                break

            end_idx += 1

        filters = result

    return filters


def _fetch_data(endpoint_url, unbreakable_filters=(), breakable_filters=(), client_name='asset_central'):
    """Retrieve data from the AssetCentral service."""
    filters = _compose_queries(unbreakable_filters, breakable_filters)
    oauth_client = get_oauth_client(client_name)

    if not filters:
        filters = ['']

    result = []
    for filter_string in filters:
        params = {'$filter': filter_string} if filter_string else {}
        params['$format'] = 'json'
        endpoint_data = oauth_client.request('GET', endpoint_url, params=params)

        if isinstance(endpoint_data, list):
            result.extend(endpoint_data)
        else:
            result.append(endpoint_data)

    if len(result) == 0:
        warnings.warn(DataNotFoundWarning(), stacklevel=2)

    return result


def _unify_filters(equality_filters, extended_filters, field_map):
    operator_map = {
        '>': 'gt',
        '<': 'lt',
        '>=': 'ge',
        '<=': 'le',
        '!=': 'ne',
        '==': 'eq'
    }

    if equality_filters is None:
        equality_filters = {}
    if extended_filters is None:
        extended_filters = []
    if field_map is None:
        field_map = {}

    unified_filters = []
    not_our_term = []
    for k, v in equality_filters.items():
        if k in field_map:
            key = field_map[k].their_name_get
        else:
            key = k
            not_our_term.append(key)

        def quote_if_string(x):
            if isinstance(x, str):
                return f"'{x}'"
            else:
                return str(x)

        if _is_non_string_iterable(v):
            v = [quote_if_string(x) for x in v]
        else:
            v = quote_if_string(v)

        unified_filters.append((key, 'eq', v))

    quoted_pattern = re.compile(r'^(\w+) *?(>|<|==|<=|>=|!=) *?([\"\'])((?:\\?.)*?)\3$')
    unquoted_pattern = re.compile(r'^(\w+) *?(>|<|==|<=|>=|!=) *?([+-]?[\w.]+)$')
    for filter_entry in extended_filters:
        if match := quoted_pattern.fullmatch(filter_entry):
            k, o, _, v = match.groups()
            v = f"'{v}'"  # we always need single quotes, but want to accept double quotes as well, hence re-writing.
        elif match := unquoted_pattern.fullmatch(filter_entry):
            k, o, v = match.groups()
            if v in field_map:
                v = field_map[v].their_name_get
        else:
            raise RuntimeError(f'Failed to parse filter entry {filter_entry}')

        if k in field_map:
            key = field_map[k].their_name_get
        else:
            key = k
            not_our_term.append(key)

        unified_filters.append((key, operator_map[o], v))

    if len(not_our_term) > 0:
        warnings.warn(f'Following parameters are not in our terminology: {not_our_term}', stacklevel=3)

    return unified_filters


def _parse_filter_parameters(equality_filters=None, extended_filters=(), field_map=None):
    """
    Parse equality and extended filters into breakable and unbreakable filters.

    The distinction between breakable and unbreakable filters is necessary because the AssetCentral endpoints are
    generally queried via `GET` requests with filter parameters passed in the header, and there is a limit to the
    header size. This allows breaking a query into multiple queries of shorter length while still retrieving the
    minimal result set the filters requested.
    """
    unified_filters = _unify_filters(equality_filters, extended_filters, field_map)

    breakable_filters = []      # always required
    unbreakable_filters = []    # can be broken into sub-filters if length is exceeded

    for key, op, value in unified_filters:
        if _is_non_string_iterable(value):
            breakable_filters.append([f"{key} {op} {elem}" for elem in value])
        else:
            unbreakable_filters.append(f"{key} {op} {value}")

    return unbreakable_filters, breakable_filters


def _apply_filters_post_request(data, equality_filters, extended_filters, field_map):
    """Allow filtering of the results returned by an AssetCentral query if the endpoint doesn't implement `filter`."""
    unified_filters = _unify_filters(equality_filters, extended_filters, field_map)
    result = []

    def strip_quote_marks(value):
        if value[0] == "'" and value[-1] == "'":
            return value[1:-1]
        return value

    for elem in data:
        for key, op, value in unified_filters:
            if _is_non_string_iterable(value):
                value = [strip_quote_marks(v) for v in value]
                if elem[key] not in value:
                    break
            else:
                value = strip_quote_marks(value)
                if not getattr(operator, op)(elem[key], value):
                    break
        else:
            result.append(elem)

    return result


def _ac_application_url():
    """Return the Assetcentral application URL from the SailorConfig."""
    return SailorConfig.get('asset_central', 'application_url')


class AssetcentralEntity:
    """Common base class for Assetcentral entities."""

    _field_map = {}

    @classmethod
    def get_available_properties(cls):
        """Return the available Assetcentral properties for this class."""
        return set([field.our_name for field in cls._field_map.values() if field.is_exposed])

    @classmethod
    def get_property_mapping(cls):
        """Return a mapping from assetcentral terminology to our terminology.

        .. deprecated:: 1.4.0
        Use :meth:`get_available_properties` instead.
        """
        # TODO: remove method in future version
        msg = ("'get_property_mapping': deprecated. Method will be removed after September 01, 2021. " +
               "use 'get_available_properties' instead")
        warnings.warn(msg, FutureWarning)
        return {field.our_name: (field.their_name_get, None, None, None) for field in cls._field_map.values()
                if field.is_exposed}

    def __init__(self, ac_json: dict):
        """Create a new entity."""
        self.raw = ac_json

    @property
    def id(self):
        """Return the ID of the object."""
        return self.raw.get('id')

    def __repr__(self) -> str:
        """Return a very short string representation."""
        name = getattr(self, 'name', getattr(self, 'short_description', None))
        return f'"{self.__class__.__name__}(name="{name}", id="{self.id}")'

    def __eq__(self, obj):
        """Compare two objects based on instance type and id."""
        return isinstance(obj, self.__class__) and obj.id == self.id

    def __hash__(self):
        """Hash of an asset central object is the hash of it's id."""
        return self.id.__hash__()


class ResultSet(Sequence):
    """Baseclass to be used in all Sets of AssetCentral objects."""

    _element_type = AssetcentralEntity
    _method_defaults = {}

    def __init__(self, elements, generating_query_params=None):
        """Create a new ResultSet from the passed elements."""
        self.elements = list(set(elements))
        if len(self.elements) != len(elements):
            duplicate_elements = [k for k, v in Counter(elements).items() if v > 1]
            LOG.info(f'Duplicate elements encountered when creating {type(self).__name__}, discarding duplicates. '
                     f'Duplicates of the following elements were discarded: %s', duplicate_elements)

        bad_elements = [element for element in self.elements if not type(element) == self._element_type]
        if bad_elements:
            bad_types = ' or '.join({element.__class__.__name__ for element in bad_elements})
            raise RuntimeError(f'{self.__class__.__name__} may only contain elements of type '
                               f'{self._element_type.__name__}, not {bad_types}')

        self.__generating_query_params = generating_query_params

    def __len__(self) -> int:
        """Return the number of objects stored in the ResultSet to implement the `Sequence` interface."""
        return self.elements.__len__()

    def __eq__(self, other):
        """Two ResultSets are equal if all of their elements are equal (order is ignored)."""
        if isinstance(self, other.__class__):
            return set(self.elements) == set(other.elements)
        return False

    def __getitem__(self, arg: Union[int, slice]):
        """Return a subset of the ResultSet to implement the `Sequence` interface."""
        selection = self.elements.__getitem__(arg)
        if isinstance(arg, int):
            return selection
        else:
            return self.__class__(selection)

    def __add__(self, other):
        """Combine two ResultSets as the sum of all elements, required to implement the `Sequence` interface."""
        if not isinstance(other, type(self)):
            raise TypeError('Only ResultSets of the same type can be added.')
        return self.__class__(self.elements + other.elements, 'set-summation')

    def as_df(self, columns=None):
        """Return all information on the objects stored in the ResultSet as a pandas dataframe."""
        if columns is None:
            columns = [field.our_name for field in self._element_type._field_map.values() if field.is_exposed]
        return pd.DataFrame({
            prop: [element.__getattribute__(prop) for element in self.elements] for prop in columns
        })

    def filter(self, **kwargs) -> 'ResultSet':
        """Select a subset of the ResultSet based on named filter criteria for the attributes of the elements.

        All keyword arguments are concatenated as filters with OR operator, i.e., only one of the supplied filters
        must match for an entity to be selected.

        Returns a new ResultSet object.
        """
        selection = []

        for element in self.elements:
            for attribute, value in kwargs.items():
                if _is_non_string_iterable(value) and getattr(element, attribute) not in value:
                    break
                elif not _is_non_string_iterable(value) and getattr(element, attribute) != value:
                    break
            else:
                selection.append(element)
        return self.__class__(selection)

    def plot_distribution(self, by=None, fill=None, dropna=False):
        """
        Plot the distribution of elements of a ResultSet based on their properties.

        This effectively creates a histogram with the number of elements per group on the y-axis, and the group
        (given by the `by` parameter) on the x-axis. Additionally, the fill colour of the bar can be used to
        distinguish a second dimension.
        """
        by = self._method_defaults['plot_distribution']['by'] if by is None else by
        display_name = self._element_type.__name__ + 's'

        columns = [by]
        aes = {'x': by}
        if fill is not None:
            columns.append(fill)
            aes['fill'] = fill

        data = self.as_df(columns)
        if dropna:
            data = data.dropna(subset=[by])
            if len(data) == 0:
                raise RuntimeError(f'No {display_name} with non-empty "{by}" found. Can not create plot.')

        data = data.fillna('NA')
        if data.dtypes[by] == 'O':  # strings/objects, we treat these as categorical
            plot_function = p9.geom_bar()
        else:
            plot_function = p9.geom_histogram(color='white', bins=20)  # anything else, treated as continuous

        plot = (
                p9.ggplot(data, p9.aes(**aes)) +
                plot_function +
                _default_plot_theme() +
                p9.ggtitle(f'Number of {display_name} per {by}')
                )
        return plot


def _is_non_string_iterable(obj):
    if issubclass(obj.__class__, str):
        return False
    return isinstance(obj, Iterable)


class _AssetcentralWriteRequest(UserDict):
    """Used for building the dictionary for create and update requests."""

    def __init__(self, field_map, *args, **kwargs):
        self.field_map = field_map
        super().__init__(*args, **kwargs)

    def insert_user_input(self, input_dict, forbidden_fields=()):
        """Validate user input and update request if successful."""
        for field_name in forbidden_fields:
            their_name_put = self.field_map[field_name].their_name_put
            offender = field_name if field_name in input_dict else None
            offender = their_name_put if their_name_put in input_dict else offender
            if offender:
                raise RuntimeError(f"You cannot set '{offender}' in this request.")
        self.update(input_dict)

    def validate(self):
        """Validate that mandatory fields are set."""
        missing_keys = [field.our_name for field in self.field_map.values()
                        if field.is_mandatory and field.their_name_put not in self.data]
        if missing_keys:
            raise AssetcentralRequestValidationError(
                "Error when creating request. Missing values for mandatory parameters.", missing_keys)

    def __setitem__(self, key, value):
        """Transform item to AC API terminology before writing the underlying dict.

        If a key cannot be found using the mapping no transformation is done.
        """
        if field := self.field_map.get(key):
            if field.is_writable:
                field.put_setter(self.data, value)
        else:
            warnings.warn(f"Unknown name for {type(self).__name__} parameter found: '{key}'.")
            self.data[key] = value

    @classmethod
    def from_object(cls, ac_entity: AssetcentralEntity):
        """Create a new request object using an existing AC object."""
        raw = deepcopy(ac_entity.raw)
        request = cls(ac_entity._field_map)

        for field in request.field_map.values():
            if field.is_writable:
                try:
                    request[field.our_name] = raw.pop(field.their_name_get)
                except KeyError:
                    msg = ("Error when creating request object. Please try again. If the error persists "
                           "please raise an issue with the developers including the stacktrace."
                           "\n\n==========================  Debug information =========================="
                           f"\nCould not find key '{field.their_name_get}'."
                           f"\nAC entity keys: {raw.keys()}")
                    raise RuntimeError(msg)
            else:
                raw.pop(field.their_name_get, None)
        if raw.keys():
            LOG.debug("raw keys for %s not known to mapping or deletelist:\n%s", type(ac_entity), raw.keys())
        request.update(raw)
        return request


class AssetcentralRequestValidationError(Exception):  # noqa: D101 (self-explanatory)
    pass


class _AssetcentralField:
    """Specify a field in Assetcentral."""

    def __init__(self, our_name, their_name_get, their_name_put=None, is_mandatory=False,
                 get_extractor=None, put_setter=None):
        self.our_name = our_name
        self.their_name_get = their_name_get
        self.their_name_put = their_name_put
        self.is_exposed = not our_name.startswith('_')
        self.is_writable = their_name_put is not None
        self.is_mandatory = is_mandatory

        self.names = (our_name, their_name_get, their_name_put)

        self.get_extractor = get_extractor or self._default_get_extractor
        self.put_setter = put_setter or self._default_put_setter

    def _default_put_setter(self, payload, value):
        payload[self.their_name_put] = value
        return

    def _default_get_extractor(self, value):
        return value


def _nested_put_setter(*nested_names):
    def setter(payload, value):
        next_dict = payload
        for nested_name in nested_names[:-1]:
            next_dict = next_dict.setdefault(nested_name, {})
        next_dict[nested_names[-1]] = value
    return setter


def _add_properties(cls):
    """Add properties to the entity class based on the field template defined by the request mapper."""
    # This is the new function to be used for all AssetcentralEntities.
    # TODO: remove this comment block once everything is refactored
    for field in cls._field_map.values():

        # the assignment of the default value (`field=field`)
        # is necessary due to the closure rules in loops
        def getter(self, field=field):
            return field.get_extractor(self.raw.get(field.their_name_get))

        setattr(cls, field.our_name, property(getter, None, None))
    return cls
