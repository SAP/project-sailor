"""Module for various utility functions, in particular those related to fetching data from remote oauth endpoints."""

from copy import deepcopy
from collections import UserDict
from itertools import product
import operator
import logging
import warnings
import re

from sailor import _base
from ..utils.oauth_wrapper import get_oauth_client
from ..utils.config import SailorConfig
from ..utils.utils import DataNotFoundWarning, _is_non_string_iterable

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
    # known fields are put through the query transformer
    # unknown fields are never transformed
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
            query_transformer = field_map[k].query_transformer
        else:
            key = k
            not_our_term.append(key)
            query_transformer = str

        if _is_non_string_iterable(v):
            v = [query_transformer(x) for x in v]
        else:
            v = query_transformer(v)

        unified_filters.append((key, 'eq', v))

    quoted_pattern = re.compile(r'^(\w+) *?(>|<|==|<=|>=|!=) *?([\"\'])((?:\\?.)*?)\3$')
    unquoted_pattern = re.compile(r'^(\w+) *?(>|<|==|<=|>=|!=) *?(\S+)$')
    for filter_entry in extended_filters:
        quote_char = None
        if match := quoted_pattern.fullmatch(filter_entry):
            k, o, quote_char, v = match.groups()
        elif match := unquoted_pattern.fullmatch(filter_entry):
            k, o, v = match.groups()
        else:
            raise RuntimeError(f'Failed to parse filter entry {filter_entry}')

        if k in field_map:
            key = field_map[k].their_name_get
            if not quote_char and v in field_map:
                v = field_map[v].their_name_get
                query_transformer = str     # equals identity, since field name must be unquoted string
            else:
                query_transformer = field_map[k].query_transformer
        else:
            key = k
            not_our_term.append(key)

            if quote_char:
                # if quoted, then the user must mean that it is a string
                def quote_same(x, q=quote_char):
                    return f'{q}{x}{q}'
                query_transformer = quote_same
            else:
                # unknown unquoted fields are put through completely unchanged. Examples:
                # abc == 3.4
                # abc == null
                # abc == some-string-value-but-user-forgot-to-quote-it
                # abc == datetimeoffset'blub'
                query_transformer = str     # equals identity, since end result is always a string

        v = query_transformer(v)

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


class _AssetcentralField(_base.MasterDataField):
    """Specify a field in Assetcentral."""

    pass


class AssetcentralEntity(_base.MasterDataEntity):
    """Common base class for AssetCentral entities."""

    pass


class AssetcentralEntitySet(_base.MasterDataEntitySet):
    """Baseclass to be used in all Sets of AssetCentral objects."""

    pass


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


def _nested_put_setter(*nested_names):
    def setter(payload, value):
        next_dict = payload
        for nested_name in nested_names[:-1]:
            next_dict = next_dict.setdefault(nested_name, {})
        next_dict[nested_names[-1]] = value
    return setter
