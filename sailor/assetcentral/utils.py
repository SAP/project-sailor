"""Module for various utility functions, in particular those related to fetching data from remote oauth endpoints."""

from copy import deepcopy
from collections import UserDict
import logging
import time
import warnings

from sailor import _base
from sailor.utils.oauth_wrapper.OAuthServiceImpl import RequestError
from ..utils.config import SailorConfig

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


def _ac_fetch_data(endpoint_url, unbreakable_filters=(), breakable_filters=()):
    try:
        return _base.fetch_data('asset_central', _ac_response_handler,
                                endpoint_url, unbreakable_filters, breakable_filters)
    except RequestError as e:
        if e.status_code == 429:
            LOG.debug('AssetCentral request was rate limited, will re-try once in 1s.')
            time.sleep(1)
            return _base.fetch_data('asset_central', _ac_response_handler,
                                    endpoint_url, unbreakable_filters, breakable_filters)
        else:
            raise


def _ac_response_handler(result_list, endpoint_data):
    if isinstance(endpoint_data, list):
        result_list.extend(endpoint_data)
    else:
        result_list.append(endpoint_data)
    return result_list


def _ac_application_url():
    """Return the Assetcentral application URL from the SailorConfig."""
    return SailorConfig.get('asset_central', 'application_url')


class _AssetcentralField(_base.MasterDataField):
    """Specify a field in Assetcentral."""

    pass


class AssetcentralEntity(_base.MasterDataEntity):
    """Common base class for AssetCentral entities."""

    def __repr__(self) -> str:
        """Return a very short string representation."""
        name = getattr(self, 'name', getattr(self, 'short_description', None))
        return f'{self.__class__.__name__}(name="{name}", id="{self.id}")'


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
                warnings.warn(f"Parameter '{key}' is not available for create or update requests and will be ignored.",
                              stacklevel=5)
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
