import logging
from collections import Counter
from collections.abc import Sequence
from typing import Iterable, Union

import pandas as pd
import plotnine as p9

from ..utils.plot_helper import _default_plot_theme
from ..utils.utils import _is_non_string_iterable
from ..utils.timestamps import _any_to_timestamp, _timestamp_to_isoformat, _timestamp_to_date_string

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


class MasterDataField:
    """Common base class for all masterdata fields."""

    def __init__(self, our_name, their_name_get, their_name_put=None, is_mandatory=False,
                 get_extractor=None, put_setter=None, query_transformer=None):
        self.our_name = our_name
        self.their_name_get = their_name_get
        self.their_name_put = their_name_put
        self.is_exposed = not our_name.startswith('_')
        self.is_writable = their_name_put is not None
        self.is_mandatory = is_mandatory

        self.names = (our_name, their_name_get, their_name_put)

        self.query_transformer = query_transformer or self._default_query_transformer
        self.get_extractor = get_extractor or self._default_get_extractor
        self.put_setter = put_setter or self._default_put_setter

    def _default_put_setter(self, payload, value):
        payload[self.their_name_put] = value

    @staticmethod
    def _default_get_extractor(value):
        return value

    @staticmethod
    def _default_query_transformer(value):
        if value in [None, 'null']:
            return 'null'
        else:
            return f"'{str(value)}'"


def _qt_double(value):
    if value in [None, 'null']:
        return 'null'
    return f"{str(value)}d"


def _qt_timestamp(value):
    if value in [None, 'null']:
        return 'null'
    timestamp = _any_to_timestamp(value)
    timestamp = _timestamp_to_isoformat(timestamp, with_zulu=True)
    return f"'{timestamp}'"


def _qt_odata_datetimeoffset(value):
    """Return a timestamp in format 'datetimeoffset'yyyy-mm-ddThh:mm:ssZ'."""
    if value in [None, 'null']:
        return 'null'
    timestamp = _any_to_timestamp(value)
    timestamp = _timestamp_to_isoformat(timestamp, with_zulu=True)
    timestamp = f"datetimeoffset'{timestamp}'"
    return timestamp


def _qt_date(value):
    if value in [None, 'null']:
        return 'null'
    timestamp = _any_to_timestamp(value)
    timestamp = _timestamp_to_date_string(timestamp)
    return f"'{timestamp}'"


def _qt_boolean_int_string(value):
    if value in [None, 'null']:
        return 'null'
    return f"'{str(int(value))}'"


def _qt_non_filterable(field_name):
    def raiser(value):
        raise RuntimeError(f'Filtering on "{field_name}" is not supported by AssetCentral')
    return raiser


class MasterDataEntity:
    """Common base class for Masterdata entities."""

    _field_map = {}

    @classmethod
    def get_available_properties(cls):
        """Return the available properties for this class."""
        return set([field.our_name for field in cls._field_map.values() if field.is_exposed])

    def __init__(self, ac_json: dict):
        """Create a new entity."""
        self.raw = ac_json

    @property
    def id(self):
        """Return the ID of the object."""
        return self.raw.get('id')

    def __repr__(self) -> str:
        """Return a very short string representation."""
        return f'{self.__class__.__name__}(id="{self.id}")'

    def __eq__(self, obj):
        """Compare two objects based on instance type and id."""
        return isinstance(obj, self.__class__) and obj.id == self.id

    def __hash__(self):
        """Hash of an asset central object is the hash of it's id."""
        return self.id.__hash__()


class MasterDataEntitySet(Sequence):
    """Baseclass to be used in all Sets of MasterData objects."""

    _element_type = MasterDataEntity
    _method_defaults = {}

    def __init__(self, elements):
        """Create a new MasterDataEntitySet from the passed elements."""
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

    def __len__(self) -> int:
        """Return the number of objects stored in the collection to implement the `Sequence` interface."""
        return self.elements.__len__()

    def __eq__(self, other):
        """Two ResultSets are equal if all of their elements are equal (order is ignored)."""
        if isinstance(self, other.__class__):
            return set(self.elements) == set(other.elements)
        return False

    def __getitem__(self, arg: Union[int, slice]):
        """Return a subset of the MasterDataEntitySet to implement the `Sequence` interface."""
        selection = self.elements.__getitem__(arg)
        if isinstance(arg, int):
            return selection
        else:
            return self.__class__(selection)

    def __add__(self, other):
        """Combine two ResultSets as the sum of all elements, required to implement the `Sequence` interface."""
        if not isinstance(other, type(self)):
            raise TypeError('Only ResultSets of the same type can be added.')
        return self.__class__(self.elements + other.elements)

    def as_df(self, columns: Iterable[str] = None):
        """Return all information on the objects stored in the MasterDataEntitySet as a pandas dataframe.

        ``columns`` can be specified to select the columns (and their order) for the DataFrame.
        """
        if columns is None:
            columns = [field.our_name for field in self._element_type._field_map.values() if field.is_exposed]
        return pd.DataFrame({
            prop: [element.__getattribute__(prop) for element in self.elements] for prop in columns
        })

    def filter(self, **kwargs) -> 'MasterDataEntitySet':
        """Select a subset of the collection based on named filter criteria for the attributes of the elements.

        All keyword arguments are concatenated as filters with OR operator, i.e., only one of the supplied filters
        must match for an entity to be selected.

        Returns a new AssetcentralEntitySet object.
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
        Plot the distribution of elements of a MasterDataEntitySet based on their properties.

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


def add_properties(cls):
    """Add properties to the entity class based on the field template defined by the request mapper."""
    for field in cls._field_map.values():

        # the assignment of the default value (`field=field`)
        # is necessary due to the closure rules in loops
        def getter(self, field=field):
            return field.get_extractor(self.raw.get(field.their_name_get))

        setattr(cls, field.our_name, property(getter, None, None))
    return cls


def _nested_put_setter(*nested_names):
    def setter(payload, value):
        next_dict = payload
        for nested_name in nested_names[:-1]:
            next_dict = next_dict.setdefault(nested_name, {})
        next_dict[nested_names[-1]] = value
    return setter
