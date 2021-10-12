from itertools import product
import operator
from typing import List
import warnings
import re
import logging

from ..utils.oauth_wrapper import get_oauth_client
from ..utils.utils import DataNotFoundWarning, _is_non_string_iterable

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


_OPERATOR_MAP = {
    '>': 'gt',
    '<': 'lt',
    '>=': 'ge',
    '<=': 'le',
    '!=': 'ne',
    '==': 'eq'
}

_EXTENDED_FILTER_PATTERN = re.compile(r'^(\w+) *?(>=|<=|==|!=|<|>) *(.*?)$')


def fetch_data(client_name, response_handler, endpoint_url, unbreakable_filters=(), breakable_filters=()) -> List:
    """Retrieve data from a supported odata service.

    A response_handler function needs to be passed which must extract the results
    returned from the odata service endpoint response into a list.
    """
    filters = _compose_queries(unbreakable_filters, breakable_filters)
    oauth_client = get_oauth_client(client_name)

    if not filters:
        filters = ['']

    result = []
    for filter_string in filters:
        result_filter = []

        params = {'$filter': filter_string} if filter_string else {}
        params.update({'$format': 'json'})

        endpoint_data = oauth_client.request('GET', endpoint_url, params=params)
        result_filter = response_handler(result_filter, endpoint_data)

        result.extend(result_filter)

    if len(result) == 0:
        warnings.warn(DataNotFoundWarning(), stacklevel=2)

    return result


def parse_filter_parameters(equality_filters=None, extended_filters=(), field_map=None):
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


def apply_filters_post_request(data, equality_filters, extended_filters, field_map):
    """Allow filtering of the results returned by an AssetCentral query if the endpoint doesn't implement `filter`."""
    result = []

    # the following code (until filtering) is partly similar to _unify_filters but leaves out query_transformers.
    # this is done mainly to not further complicate the _unify_filters code.

    if equality_filters is None:
        equality_filters = {}
    if extended_filters is None:
        extended_filters = []
    if field_map is None:
        field_map = {}

    unified_filters = []
    for k, v in equality_filters.items():
        if k in field_map:
            k = field_map[k].their_name_get
        unified_filters.append((k, 'eq', v))

    for filter_entry in extended_filters:
        match = _EXTENDED_FILTER_PATTERN.fullmatch(filter_entry)
        k, o, v = match.groups()
        if k in field_map:
            k = field_map[k].their_name_get
        unified_filters.append((k, _OPERATOR_MAP[o], v))

    # filtering starts here
    for elem in data:
        for key, op, value in unified_filters:
            if _is_non_string_iterable(value):
                value = [_strip_quote_marks(v) for v in value]
                if elem[key] not in value:
                    break
            else:
                value = _strip_quote_marks(value)
                if not getattr(operator, op)(elem[key], value):
                    break
        else:
            result.append(elem)

    return result


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


def _unify_filters(equality_filters, extended_filters, field_map):
    # known field values are put through the query transformer
    # unknown field values are never transformed

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

    for filter_entry in extended_filters:
        if match := _EXTENDED_FILTER_PATTERN.fullmatch(filter_entry):
            k, o, v = match.groups()
        else:
            raise RuntimeError(f'Failed to parse filter entry {filter_entry}')

        if k in field_map:
            key = field_map[k].their_name_get
            if v in field_map:
                v = field_map[v].their_name_get
                query_transformer = str         # equals identity, since field name must be unquoted string
            else:
                query_transformer = field_map[k].query_transformer
                v = _strip_quote_marks(v)
        else:
            key = k
            not_our_term.append(key)
            # unknown field values are put through completely unchanged
            query_transformer = str

        v = query_transformer(v)

        unified_filters.append((key, _OPERATOR_MAP[o], v))

    if len(not_our_term) > 0:
        warnings.warn(f'Following parameters are not in our terminology: {not_our_term}', stacklevel=3)

    return unified_filters


def _strip_quote_marks(value):
    if not isinstance(value, str):
        return value
    quoted_value_pattern = re.compile(r'^([\"\'])(.*)\1$')
    if match := quoted_value_pattern.fullmatch(value):
        _, value = match.groups()
    return value
