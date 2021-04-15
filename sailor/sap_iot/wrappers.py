"""
Timeseries module can be used to retrieve timeseries data from the SAP iot abstract timeseries api.

Here we define some convenience wrappers for timeseries data.
"""

from __future__ import annotations

from collections.abc import Iterable
import warnings
from datetime import datetime
from typing import TYPE_CHECKING, Union, Any, Callable
import logging

import pandas as pd
from plotnine import ggplot, geom_point, aes, facet_grid, geom_line
from plotnine.themes import theme
from plotnine.scales import scale_x_datetime
from sklearn.preprocessing import StandardScaler

import sailor.assetcentral.indicators as ac_indicators
from ..utils.plot_helper import _default_plot_theme
from ..utils.timestamps import _any_to_timestamp, _calculate_nice_sub_intervals

if TYPE_CHECKING:
    from ..assetcentral.indicators import IndicatorSet
    from ..assetcentral.equipment import EquipmentSet

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


class TimeseriesDataset(object):
    """A Wrapper class to make accessing timeseries data from SAP iot more convenient."""

    def __init__(self, df: pd.DataFrame, indicator_set: IndicatorSet, equipment_set: EquipmentSet,
                 nominal_data_start: pd.Timestamp, nominal_data_end: pd.Timestamp,
                 is_normalized: bool = False):
        """
        Create a TimeseriesDataset.

        indicator_set must be an IndicatorSet containing all indicators occuring in the data columns of the
        dataframe, and equipment_set must be an EquipmentSet containing all equipments occuring in the equipment_id
        column of the data.
        """
        self._df = df
        self.is_normalized = is_normalized
        self._equipment_set = equipment_set
        self._indicator_set = indicator_set
        self.nominal_data_start = nominal_data_start
        self.nominal_data_end = nominal_data_end
        self.type = 'EQUIPMENT'  # current wrapper type is always 'equipment'

        df_equipment_ids = set(df['equipment_id'].unique())
        set_equipment_ids = set(equipment.id for equipment in equipment_set)
        if df_equipment_ids - set_equipment_ids:
            raise RuntimeError('Not all equipment ids in the data are provided in the equipment set.')
        if set_equipment_ids - df_equipment_ids:
            warnings.warn('There is no data in the dataframe for some of the equipments in the equipment set.')
            self._equipment_set = self._equipment_set.filter(id=df_equipment_ids)

        df_indicator_ids = set(df.columns) - set(self.get_index_columns())
        set_indicator_ids = set(indicator._unique_id for indicator in indicator_set)
        if df_indicator_ids - set_indicator_ids:
            raise RuntimeError('Not all indicator ids in the data are provided in the indicator set.')
        if set_indicator_ids - df_indicator_ids:
            warnings.warn('There is no data in the dataframe for some of the indicators in the indicator set.')
            self._indicator_set = self._indicator_set.filter(_unique_id=df_indicator_ids)

    def get_key_columns(self, speaking_names=False):
        """
        Return those columns of the data that identify the asset.

        Currently we only support asset type 'Equipment' so this will always return columns based on the equipment.
        In the future other types (like System) will be supported here.

        Parameters
        ----------
        speaking_names
            False, return key columns
            True, return corresponding names of key columns

        Example
        -------
        Get key columns of the indicator data set 'my_indicator_data'::

            my_indicator_data.get_key_columns()
        """
        if self.type != 'EQUIPMENT':
            raise NotImplementedError('Currently only Equipment is supported as base object for timeseries data.')

        if speaking_names:
            return ['model_name', 'equipment_name']
        else:
            return ['model_id', 'equipment_id']

    @staticmethod
    def get_time_column():
        """Return the name of the column containing the time information."""
        return 'timestamp'

    def get_feature_columns(self, speaking_names=False):
        """
        Get the names of all feature columns.

        Parameters
        ----------
        speaking_names
            False, returns feature columns of a data set
            True, returns corresponding names of feature columns

        Example
        -------
        Get Template id, Indicator group name and Indicator name of columns including indicator values in the
        data set 'my_indicator_data'::

            my_indicator_data.get_feature_columns(speaking_names=True)

        """
        if speaking_names:
            return list(self._indicator_set._unique_id_to_names().values())
        return list(self._indicator_set._unique_id_to_constituent_ids().keys())

    def get_index_columns(self, speaking_names=False):
        """Return the names of all index columns (key columns and time column)."""
        return [*self.get_key_columns(speaking_names), self.get_time_column()]

    def as_df(self, speaking_names=False):
        """
        Return the data stored within this TimeseriesDataset object as a pandas dataframe.

        By default the data is returned with opaque column headers. If speaking_names is set to true, the data is
        converted such that equipment_id and model_id are replaced by human-readable names, and the opaque
        column headers are replaced by a hierarchical index of template_id, indicator_group_name, indicator_name and
        aggregation_function.
        """
        if speaking_names:
            return self._transform(self._df)
        else:
            return self._df.set_index(self.get_index_columns())

    def _transform(self, df):
        translator = {'equipment_id': {}, 'model_id': {}}
        for equipment in self._equipment_set:
            translator['equipment_id'][equipment.id] = equipment.name
            translator['model_id'][equipment.model_id] = equipment.model_name

        static_column_mapping = {'equipment_id': 'equipment_name', 'model_id': 'model_name'}
        data = (
            df.replace(translator)
              .rename(columns=static_column_mapping)
              .set_index(self.get_index_columns(speaking_names=True))
              .rename(columns=self._indicator_set._unique_id_to_names())
        )
        data.columns = pd.MultiIndex.from_tuples(data.columns)

        return data

    def plot(self, start=None, end=None, indicator_set=None, equipment_set=None):
        """
        Plot the timeseries data stored within this wrapper.

        The plot will create different panels for each indicator_group_name and template in the data, as well as each
        indicator. Data from different equipment_set will be represented by different colors. The plotnine object
        returned by this method will be rendered in jupyter notebooks, but can also be further modified by the caller.

        Parameters
        ----------
        start
            Optional start time the timeseries data is plotted.
        end
            Optional end time the timeseries data is plotted.
        indicator_set
            Optional Indicators which are plotted.
        equipment_set
            optional equipment which indicator data is plotted.

        Returns
        -------
        plot
            Line charts of timeseries data.

        Example
        -------
        Plot all Indicators for a period from 2020-07-02 to 2020-09-01 in the data set 'my_indicator_data'::

            my_indicator_data.plot('2020-07-02','2020-09-01')
        """
        key_vars = self.get_index_columns()
        time_column = self.get_time_column()

        if indicator_set is None:
            indicator_set = self._indicator_set
        feature_vars = [indicator._unique_id for indicator in indicator_set]
        name_mapping = indicator_set._unique_id_to_names()

        if equipment_set is None:
            equipment_set = self._equipment_set
        equipment_mapping = {equipment.id: equipment.name for equipment in equipment_set}
        selected_equipment_ids = equipment_mapping.keys()

        start = _any_to_timestamp(start, default=self._df[time_column].min())
        end = _any_to_timestamp(end, default=self._df[time_column].max())

        if self._df.empty:
            raise RuntimeError('There is no data in this dataset.')

        data = self._df \
            .query(f'({time_column} >= @start) & ({time_column} <= @end)') \
            .query('equipment_id in @selected_equipment_ids') \
            .filter(items=key_vars + feature_vars)
        result_equipment_ids = set(data['equipment_id'])

        if data.empty:
            raise RuntimeError('There is no data in the dataset for the selected equipments and indicators.')

        # find equipment_set that are dropped from the plot and log them to the user
        empty_equipment_ids = set(selected_equipment_ids) - result_equipment_ids
        if empty_equipment_ids:
            warnings.warn(f'Following equipment show no data and are removed from the plot: {empty_equipment_ids}')
            selected_equipment_ids = set(selected_equipment_ids) - empty_equipment_ids
        # also indicators without data need to be removed from the plot due to unknown Y axis limits
        empty_indicators = data.columns[data.isna().all()].tolist()
        if empty_indicators:
            # Todo: speaking names in the log below? Currently using our uuid
            warnings.warn(f'Following indicators show no data and are removed from the plot: {empty_indicators}')
            feature_vars = set(feature_vars) - set(empty_indicators)

        query_timedelta = end - start
        break_interval = _calculate_nice_sub_intervals(query_timedelta, 5)  # at least 5 axis breaks
        first_break = start.floor(break_interval, ambiguous=False, nonexistent='shift_backward')
        last_break = end.ceil(break_interval, ambiguous=False, nonexistent='shift_forward')
        x_breaks = pd.date_range(first_break, last_break, freq=break_interval)

        if break_interval < pd.Timedelta('1 day'):
            date_labels = '%Y-%m-%d %H:%M:%S'
        else:
            date_labels = '%Y-%m-%d'

        facet_grid_definition = 'indicator + template + indicator_group ~ .'
        facet_assignment = dict(
            template=lambda x: x.Feature.apply(lambda row: name_mapping[row][0]),
            indicator_group=lambda x: x.Feature.apply(lambda row: name_mapping[row][1]),
            indicator=lambda x: x.Feature.apply(lambda row: name_mapping[row][2])
        )

        if isinstance(self._indicator_set, ac_indicators.AggregatedIndicatorSet):
            facet_grid_definition = 'aggregation + indicator + template + indicator_group ~ .'
            facet_assignment['aggregation'] = lambda x: x.Feature.apply(lambda row: name_mapping[row][3])

        aggregation_interval = _calculate_nice_sub_intervals(query_timedelta, 100)  # at leat 100 data points
        groupers = [*self.get_key_columns(), pd.Grouper(key=time_column, freq=aggregation_interval)]
        molten_data = (
            data.groupby(groupers)
                .agg('mean')
                .reset_index()
                .dropna(1, 'all')
                .melt(id_vars=key_vars, value_vars=feature_vars, var_name='Feature')
                .assign(**facet_assignment)
                .replace({'equipment_id': equipment_mapping})
                .rename(columns={'equipment_id': 'equipment'})
        )

        facet_row_count = len(feature_vars) + len(molten_data.groupby(['template', 'indicator_group']))

        plot = (
                ggplot(molten_data, aes(x=self.get_time_column(), y='value', color='equipment')) +
                geom_point() + geom_line() +
                facet_grid(facet_grid_definition, scales='free') +
                _default_plot_theme() +
                theme(figure_size=(10, 3 * facet_row_count)) +
                scale_x_datetime(limits=(start, end), date_labels=date_labels, breaks=x_breaks)
        )

        return plot

    def normalize(self, fitted_scaler=None, scaler=StandardScaler(copy=True, with_mean=True, with_std=True)) \
            -> tuple[TimeseriesDataset, Any]:
        """
        Normalize a data frame using scaler in normalization_factors.

        Parameters
        ----------
        fitted_scaler
            Optional fitted scaler, to be used to normalize self._df
        scaler
            Type of scaler to use for normalization. Default settings implies x -> (x-m)/s, m= mean and s=std.
            Properties are computed along the columns.

        Returns
        -------
        new_wrapper
            TimeseriesDataset with self._df updated to be the normalized dataframe.
        fitted_scaler
            Fitted scaler to be used to normalize the data.

        Example
        -------
        Get normalized values for indicators in the indicator data set 'My_indicator_data'::

            My_indicator_data.normalize()[0]
        """
        features = [column for column in self._df.columns if column not in self.get_index_columns()]
        if fitted_scaler is None and self.is_normalized:
            raise RuntimeError("There is no fitted scaler but dataset is already normalized.")
        if fitted_scaler is None:
            # normalize the data and save normalization factors to normalization_factors
            fitted_scaler = scaler.fit(self._df[features])
            LOG.debug('No scaler provided for normalization, fitting scaler to dataset: %s', fitted_scaler)

        normalized_df = self._df.copy()
        normalized_df[features] = fitted_scaler.transform(normalized_df[features])
        new_wrapper = TimeseriesDataset(normalized_df, self._indicator_set,
                                        self._equipment_set,
                                        self.nominal_data_start, self.nominal_data_end,
                                        is_normalized=True)

        return new_wrapper, fitted_scaler

    def filter(self, equipment_ids: Iterable[str] = None, start: Union[str, pd.Timestamp, datetime] = None,
               end: Union[str, pd.Timestamp, datetime] = None) -> TimeseriesDataset:
        """Return a new TimeseriesDataset extracted from an original data with filter parameters.

        Only indicator data specified in filters are returned.

        Parameters
        ----------
        equipment_ids
            Optional equipment set ids to filter timeseries data.
        start
            Optional start time of timeseries data are returned.
        end
            Optional end time until timeseries data are returned.

        Example
        -------
        Filter out indicator data for an equipment 'MyEquipmentId' from the indicator data 'My_indicator_data'::

            My_indicator_data.filter(MyEquipmentId)
        """
        if isinstance(equipment_ids, str):
            equipment_ids = [equipment_ids]

        if equipment_ids is None:
            equipment_ids = [equipment.id for equipment in self._equipment_set]
        start_time = _any_to_timestamp(start, default=self.nominal_data_start)
        end_time = _any_to_timestamp(end, default=self.nominal_data_end)
        selected_equi_set = self._equipment_set.filter(id=equipment_ids)

        selected_df = self._df.query('(equipment_id in @equipment_ids) &'
                                     '(timestamp >= @start_time) & (timestamp < @end_time)')

        if len(selected_df) == 0:
            warnings.warn('The selected filters removed all data, the resulting TimeseriesDataset is empty.')
        LOG.debug('Filtered Dataset contains %s rows.', len(selected_df))

        return TimeseriesDataset(selected_df, self._indicator_set, selected_equi_set,
                                 start_time, end_time, self.is_normalized)

    def aggregate(self,
                  aggregation_interval: str,
                  aggregation_functions: Union[Iterable[Union[str, Callable]], str, Callable] = 'mean')\
            -> TimeseriesDataset:
        """
        Aggregate the TimeseriesDataset to a fixed interval, returning a new TimeseriesDataset.

        This operation will change the unique feature IDs, as the new IDs need to encode the additional information on
        the aggregation function. Accordingly there will also be an additional column index level for the
        aggregation function on the DataFrame returned by :meth:`sailor.timeseries.wrappers.TimeseriesDataset.as_df`
        when using ``speaking_names=True``.
        Note that the resulting timeseries is not equidistant if gaps larger than the aggregation interval are
        present in the original timeseries.

        Parameters
        ----------
        aggregation_interval
            String specifying the aggregation interval, e.g. '1h' or '30min'. Follows the same rules as the ``freq``
            parameter in a ``pandas.Grouper`` object.
        aggregation_functions
            Aggregation function or iterable of aggregation functions to use.
            Each aggregation_function can be a string (e.g. 'mean', 'min' etc) or a function (e.g. np.max etc).
        """
        if isinstance(aggregation_functions, str) or isinstance(aggregation_functions, Callable):
            aggregation_functions = (aggregation_functions, )

        new_indicators = []
        aggregation_definition = {}
        for indicator in self._indicator_set:
            for aggregation_function in aggregation_functions:
                new_indicator = ac_indicators.AggregatedIndicator(indicator.raw, str(aggregation_function))
                new_indicators.append(new_indicator)
                aggregation_definition[new_indicator._unique_id] = (indicator._unique_id, aggregation_function)
        new_indicator_set = ac_indicators.AggregatedIndicatorSet(new_indicators)

        grouper = [*self.get_key_columns(),
                   pd.Grouper(key=self.get_time_column(), closed='left', freq=aggregation_interval)]
        df = self._df.groupby(grouper).agg(**aggregation_definition)

        return TimeseriesDataset(df.reset_index(), new_indicator_set, self._equipment_set,
                                 self.nominal_data_start, self.nominal_data_end, self.is_normalized)
