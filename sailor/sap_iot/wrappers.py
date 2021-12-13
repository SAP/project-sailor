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
    from ..assetcentral.indicators import IndicatorSet, AggregatedIndicatorSet
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
        self._df = df.query('(timestamp >= @nominal_data_start) & (timestamp < @nominal_data_end)')
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

        df_indicator_ids = set(df.columns) - set(self.get_index_columns(include_model=False))
        set_indicator_ids = set(indicator._unique_id for indicator in indicator_set)
        if df_indicator_ids - set_indicator_ids:
            raise RuntimeError('Not all indicator ids in the data are provided in the indicator set.')
        if set_indicator_ids - df_indicator_ids:
            warnings.warn('There is no data in the dataframe for some of the indicators in the indicator set.')
            self._indicator_set = self._indicator_set.filter(_unique_id=df_indicator_ids)

    @property
    def indicator_set(self):
        """Return all Indicators present in the TimeseriesDataset."""
        return self._indicator_set

    @property
    def equipment_set(self):
        """Return all equipment present in the TimeseriesDataset."""
        return self._equipment_set

    def get_key_columns(self, speaking_names=False, include_model=False):
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

        if include_model:
            if speaking_names:
                return ['equipment_name', 'model_name']
            else:
                return ['equipment_id', 'model_id']
        else:
            if speaking_names:
                return ['equipment_name']
            else:
                return ['equipment_id']

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

    def get_index_columns(self, speaking_names=False, include_model=False) -> list:
        """Return the names of all index columns (key columns and time column)."""
        return [*self.get_key_columns(speaking_names, include_model), self.get_time_column()]

    def as_df(self, speaking_names=False, include_model=False):
        """
        Return the data stored within this TimeseriesDataset object as a pandas dataframe.

        By default the data is returned with opaque column headers. If speaking_names is set to true, the data is
        converted such that equipment_id and model_id are replaced by human-readable names, and the opaque
        column headers are replaced by a hierarchical index of template_id, indicator_group_name, indicator_name and
        aggregation_function.
        """
        if include_model:
            model_ids = pd.DataFrame(
                [(equi.id, equi.model_id) for equi in self._equipment_set], columns=['equipment_id', 'model_id']
            )
            df = pd.merge(self._df, model_ids, on='equipment_id')
        else:
            df = self._df

        if speaking_names:
            return self._transform(df, include_model=include_model)
        else:
            return df.set_index(self.get_index_columns(include_model=include_model))

    def _transform(self, df, include_model):
        if include_model:
            static_column_mapping = {'equipment_id': 'equipment_name', 'model_id': 'model_name'}
            translator = {'equipment_id': {}, 'model_id': {}}
            for equipment in self._equipment_set:
                translator['equipment_id'][equipment.id] = equipment.name
                translator['model_id'][equipment.model_id] = equipment.model_name
        else:
            static_column_mapping = {'equipment_id': 'equipment_name'}
            translator = {'equipment_id': {}}
            for equipment in self._equipment_set:
                translator['equipment_id'][equipment.id] = equipment.name

        data = (
            df.replace(translator)
              .rename(columns=static_column_mapping)
              .set_index(self.get_index_columns(speaking_names=True, include_model=include_model))
              .rename(columns=self._indicator_set._unique_id_to_names())
        )
        if len(data.columns) > 0:
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
        key_vars = self.get_index_columns(include_model=False)
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
        groupers = [*self.get_key_columns(include_model=False), pd.Grouper(key=time_column, freq=aggregation_interval)]
        molten_data = (
            data.groupby(groupers)
                .agg('mean')
                .reset_index()
                .dropna(axis=1, how='all')
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
        features = [column for column in self._df.columns if column not in self.get_index_columns(include_model=False)]
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

    def filter(self, start: Union[str, pd.Timestamp, datetime] = None,
               end: Union[str, pd.Timestamp, datetime] = None, equipment_set: EquipmentSet = None,
               indicator_set: Union[IndicatorSet, AggregatedIndicatorSet] = None) -> TimeseriesDataset:
        """Return a new TimeseriesDataset extracted from an original data with filter parameters.

        Only indicator data specified in filters are returned.

        Parameters
        ----------
        start
            Optional start time of timeseries data are returned.
        end
            Optional end time until timeseries data are returned.
        equipment_set
            Optional EquipmentSet to filter timeseries data. Takes precedence over equipment_ids.
        indicator_set:
            Optional IndicatorSet to filter dataset columns.

        Example
        -------
        Filter out indicator data for an equipment 'MyEquipmentId' from the indicator data 'My_indicator_data'::

            My_indicator_data.filter(MyEquipmentId)
        """
        start_time = _any_to_timestamp(start, default=self.nominal_data_start)
        end_time = _any_to_timestamp(end, default=self.nominal_data_end)

        if equipment_set:
            # we need to filter the user's choice before creating a new TSDataset
            # since they can specify an arbitrary equipment set which could not be in the TSDataset
            equipment_ids = [equipment.id for equipment in equipment_set]
            selected_equi_set = self._equipment_set.filter(id=equipment_ids)
        else:
            selected_equi_set = self._equipment_set

        equipment_ids = [equipment.id for equipment in selected_equi_set]

        selected_df = self._df.query('(equipment_id in @equipment_ids) &'
                                     '(timestamp >= @start_time) & (timestamp < @end_time)')

        if indicator_set is not None:
            selected_column_ids = [indicator._unique_id for indicator in indicator_set]
            selected_df = selected_df[self.get_index_columns(include_model=False) + selected_column_ids]
            selected_indicator_set = indicator_set
        else:
            selected_indicator_set = self._indicator_set

        if len(selected_df) == 0:
            warnings.warn('The selected filters removed all data, the resulting TimeseriesDataset is empty.')
        LOG.debug('Filtered Dataset contains %s rows.', len(selected_df))

        return TimeseriesDataset(selected_df, selected_indicator_set, selected_equi_set,
                                 start_time, end_time, self.is_normalized)

    def aggregate(self,
                  aggregation_interval: Union[str, pd.Timedelta],
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
        aggregation_interval = pd.Timedelta(aggregation_interval)
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

        grouper = [*self.get_key_columns(include_model=False),
                   pd.Grouper(key=self.get_time_column(), closed='left', freq=aggregation_interval)]
        df = self._df.groupby(grouper).agg(**aggregation_definition)

        return TimeseriesDataset(df.reset_index(), new_indicator_set, self._equipment_set,
                                 self.nominal_data_start, self.nominal_data_end, self.is_normalized)

    def interpolate(self, interval: Union[str, pd.Timedelta], method='pad', **kwargs) -> TimeseriesDataset:
        """
        Interpolate the TimeseriesDataset to a fixed interval, returning a new TimeseriesDataset.

        Additional arguments for the interpolation function can be passed and are forwarded to the pandas `interpolate`
        function. The resulting TimeseriesDataset will always be equidistant with timestamps between
        `self.nominal_data_start` and `self.nominal_data_end`. However, values at these timestamps may be NA depending
        on the interpolation parameters.
        By default values will be forward-filled, with no limit to the number of interpolated points between two
        given values, and no extrapolation before the first known point. The following keyword arguments can be used to
        achieve some common behaviour:
          - method='slinear' will use linear interpolation between any two known points
          - method='index' will use a pandas interpolation method instead of the scipy-based method, which
          automatically forward-fills the last known value to the end of the time-series
          - fill_value='extrapolate' will extrapolate beyond the last known value (but not backwards before the first
          known value, only applicable to scipy-based interpolation methods.)
          - limit=`N` will limit the number of interpolated points between known points to N.
        Further details on this behaviour can be found in
        https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.interpolate.html
        """
        def _fill_group(grp):
            target_times = pd.date_range(self.nominal_data_start, self.nominal_data_end, freq=interval,
                                         closed='left').round(interval)

            new_index = pd.DatetimeIndex(target_times.union(grp.timestamp))
            with_all_timestamps = grp.set_index(self.get_time_column()).reindex(new_index).sort_index()

            if len(grp) <= kwargs.get('order', 1):
                group_identifier = [grp[key].iloc[0] for key in self.get_key_columns()]
                LOG.warning(f'Not enough datapoints for interpolation in group {group_identifier}!')
                return with_all_timestamps.loc[target_times]
            tmp = with_all_timestamps.interpolate(method=method, **kwargs).loc[target_times]
            tmp.index = tmp.index.set_names('timestamp')  # loc loses index name...
            return tmp

        interval = pd.Timedelta(interval)
        if interval > (self.nominal_data_end - self.nominal_data_start):
            raise RuntimeError('Can not interpolate to an interval larger than the data range.')

        df = (
            self._df
                .groupby(self.get_key_columns(include_model=False))
                .apply(_fill_group)
                .drop(columns=self.get_key_columns(include_model=False))
                .reset_index()
        )
        return TimeseriesDataset(df, self._indicator_set, self._equipment_set,
                                 self.nominal_data_start, self.nominal_data_end, self.is_normalized)
