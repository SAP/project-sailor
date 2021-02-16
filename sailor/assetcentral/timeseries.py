"""
Timeseries module can be used to retrieve timeseries data from the SAP iot abstract timeseries api.

Interfaces for retrieval are aligned with AssetCentral objects such as equipments and indicators.
Timeseries data is generally stored in a pandas dataframe, wrapped in a convenience class to make it easier
to interact with the data in AssetCentral terms.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from math import ceil
from typing import Any, TYPE_CHECKING, Union
import logging
import warnings

import pandas as pd
from plotnine import ggplot, geom_point, aes, facet_grid, geom_line
from plotnine.themes import theme
from plotnine.scales import scale_x_datetime
from sklearn.preprocessing import StandardScaler

from .utils import any_to_timestamp
from ..utils.plot_helper import default_plot_theme

if TYPE_CHECKING:
    from .equipment import Equipment, EquipmentSet

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())

fixed_timeseries_columns = {
    'time': 'timestamp',
    'duration': 'duration',
    'modelId': 'equipment_model_id',
    'templateId': 'template_id',
    'indicatorGroupId': 'indicator_group_id',
    'equipmentId': 'equipment_id'
}


class FeatureDetails:
    """
    class stores the details of feature columns retrieved from the sap abstract timeseries api.

    Columns are generally identified by indicator_id, indicator_group_id, template_id and aggregation_function.
    Since it can be inconvenient at times to store all this information in pandas column headers, the column headers are
    based on an opaque hash, and this class can be used to map from column headers to semantics about the indicator.
    """

    def __init__(self):
        """Create an empty instance of FeatureDetails()."""
        self._details = {}

    def __add__(self, other):
        """Return an instance of FeatureDetails inluding information from both inputs."""
        if not self._details.keys().isdisjoint(other._details.keys()):
            raise ValueError("Cannot add. Both instances contain an intersection of columns.")
        new_details = FeatureDetails()
        for key, value in self._details.items():
            new_details.put(key, **value)
        for key, value in other._details.items():
            new_details.put(key, **value)
        return new_details

    def put(self, column_id, indicator, aggregation_function):
        """Insert details on a column_id to the FeatureDetails, overwriting existing details for column_id."""
        self._details[column_id] = {
            'indicator': indicator,
            'aggregation_function': aggregation_function
        }

    def get_name_mapping(self):
        """Get details on an opaque column_id in terms of AssetCentral names."""
        mapping = {}
        for column_id, column_info in self._details.items():
            mapping[column_id] = (
                column_info['indicator'].template_id,  # apparently fetching the template name would need a remote call
                column_info['indicator'].indicator_group_name,
                column_info['indicator'].name,
                column_info['aggregation_function']
            )
        return mapping

    def get_id_mapping(self):
        """Get details on an opaque column_id in terms of AssetCentral IDs."""
        mapping = {}
        for column_id, column_info in self._details.items():
            mapping[column_id] = (
                column_info['indicator'].template_id,
                column_info['indicator'].indicator_group_id,
                column_info['indicator'].id,
                column_info['aggregation_function']
            )
        return mapping

    def filter(self, indicator_set, aggregation_functions):
        """
        Filter the feature details stored in this class.

        The method returns a new instance of FeatureDetails() containing only those features which match the indicators
        and aggregation_functions passed in the parameters.
        """
        new_details = FeatureDetails()
        for column_id, column_info in self._details.items():
            if column_info['aggregation_function'] in aggregation_functions:
                if indicator_set is None or column_info['indicator'] in indicator_set:
                    new_details.put(column_id, **column_info)
        return new_details

    def __len__(self):
        """Return the number of features on which information is stored by this instance."""
        return len(self._details)


class DSCTimeseriesWrapper(object):
    """A Wrapper class to make accessing timeseries data from SAP iot more convenient."""

    def __init__(self, df: pd.DataFrame, feature_details: FeatureDetails, equipment_set: EquipmentSet,
                 nominal_interval: pd.Timedelta, nominal_data_start: pd.Timestamp, nominal_data_end: pd.Timestamp,
                 is_normalized: bool = False):
        """
        Create a DSCTimeseriesWrapper.

        feature_details must be an instance of FeatureDetails() containing information on all opaque column ids in the
        dataframe, and equipment_set must be an EquipmentSet contain all equipments occuring in the equipment_id
        column of the data.
        """
        df_equipment_ids = set(df['equipment_id'].unique())
        set_equipment_ids = set(equipment.id for equipment in equipment_set)
        if not df_equipment_ids <= set_equipment_ids:
            raise RuntimeError('Not all equipment ids in the data are provided in the equipment set')

        self._df = df
        self.is_normalized = is_normalized
        self._equipment_set = equipment_set
        self._feature_details = feature_details
        self.nominal_interval = nominal_interval
        self.nominal_data_start = nominal_data_start
        self.nominal_data_end = nominal_data_end
        self.type = 'EQUIPMENT'  # current wrapper type is always 'equipment'

    def get_key_columns(self, speaking_names=False):
        """
        Return those columns of the data that identify the asset.

        Currently we only support asset type 'Equipment' so this will always return columns based on the equipment.
        In the future other types (like System) will be supported here.
        """
        if self.type != 'EQUIPMENT':
            raise NotImplementedError('Currently only Equipment is supported as base object for timeseries data.')

        if speaking_names:
            return ['equipment_model_name', 'equipment_name']
        else:
            return ['equipment_model_id', 'equipment_id']

    def get_time_column(self):
        """Return the name of the column containing the time information."""
        return 'timestamp'

    def get_feature_columns(self, speaking_names=False):
        """Get the names of all feature columns."""
        if speaking_names:
            return pd.MultiIndex.from_tuples(self._feature_details.get_name_mapping().values())
        return self._feature_details.get_id_mapping().keys()

    def get_index_columns(self, speaking_names=False):
        """Return the names of all index columns (key columns and time column)."""
        return [*self.get_key_columns(speaking_names), self.get_time_column()]

    def as_df(self, speaking_names=False):
        """
        Return the data stored within this TimeseriesWrapper object as a pandas dataframe.

        By default the data is returned with opaque column headers. If speaking_names is set to true, the data is
        converted such that equipment_id and equipment_model_id are replaced by human-readable names, and the opaque
        column headers are replaced by a hierarchical index of template_id, indicator_group_name, indicator_name and
        aggregation_function.
        """
        if speaking_names:
            return self._transform(self._df)
        else:
            return self._df.set_index(self.get_index_columns())

    def _transform(self, df):
        translator = {'equipment_id': {}, 'equipment_model_id': {}}
        for equipment in self._equipment_set:
            translator['equipment_id'][equipment.id] = equipment.name
            translator['equipment_model_id'][equipment.equipment_model_id] = equipment.equipment_model_name

        static_column_mapping = {'equipment_id': 'equipment_name', 'equipment_model_id': 'equipment_model_name'}
        data = (
            df.replace(translator)
              .rename(columns=static_column_mapping)
              .set_index(self.get_index_columns(speaking_names=True))
              .rename(columns=self._feature_details.get_name_mapping())
        )
        data.columns = pd.MultiIndex.from_tuples(data.columns)

        return data

    def plot(self, start=None, end=None, aggregation_function='AVG', indicator_set=None, equipment_set=None):
        """
        Plot the timeseries data stored within this wrapper.

        The plot will create different panels for each indicator_group and template in the data, as well as each
        indicator. Data from different equipments will be represented by different colors. The plotnine object
        returned by this method will be rendered in jupyter notebooks, but can also be further modified by the caller.

        Parameters
        ----------
        start
            Optional start time the timeseries data is plotted.
        end
            Optional end time the timeseries data is plotted.
        aggregation_function
            Optional aggregation function indicating how time series data is aggregated.
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
        Plot all indicators in indicator data set 'my_indicator_data'::
            my_indicator_data(plot)
        """
        column_selection = self._feature_details.filter(indicator_set, [aggregation_function])
        name_mapping = column_selection.get_name_mapping()
        feature_vars = [*name_mapping.keys()]  # list of all uuid's selected as features

        key_vars = self.get_index_columns()
        time_column = self.get_time_column()

        if equipment_set is None:
            equipment_set = self._equipment_set
        equipment_mapping = {equipment.id: equipment.name for equipment in equipment_set}
        selected_equipment_ids = equipment_mapping.keys()

        start = any_to_timestamp(start, default=self._df[time_column].min())
        end = any_to_timestamp(end, default=self._df[time_column].max())

        if len(self._df) == 0:
            raise RuntimeError('There is no data in this dataset.')

        data = self._df \
            .query(f'({time_column} >= @start) & ({time_column} <= @end)') \
            .query('equipment_id in @selected_equipment_ids') \
            .filter(items=key_vars + feature_vars)
        result_equipment_ids = set(data['equipment_id'])

        # find equipments that are dropped from the plot and log them to the user
        empty_equipment_ids = set(selected_equipment_ids) - result_equipment_ids
        if empty_equipment_ids:
            warnings.warn(f'Following equipments show no data and are removed from the plot: {empty_equipment_ids}')
            selected_equipment_ids = set(selected_equipment_ids) - empty_equipment_ids
        # also indicators without data need to be removed from the plot due to unknown Y axis limits
        empty_indicators = data.columns[data.isna().all()].tolist()
        if empty_indicators:
            # Todo: speaking names in the log below? Currently using our uuid
            warnings.warn(f'Following indicators show no data and are removed from the plot: {empty_indicators}')
            feature_vars = set(feature_vars) - set(empty_indicators)

        molten_data = (
            data.melt(id_vars=key_vars, value_vars=feature_vars, var_name='Feature')
                .assign(template=lambda x: x.Feature.apply(lambda row: name_mapping[row][0]))
                .assign(indicator_group=lambda x: x.Feature.apply(lambda row: name_mapping[row][1]))
                .assign(indicator=lambda x: x.Feature.apply(lambda row: name_mapping[row][2]))
                .replace({'equipment_id': equipment_mapping})
                .rename(columns={'equipment_id': 'equipment'})
        )

        facet_column_count = 1
        facet_row_count = len(feature_vars) + len(molten_data.groupby(['template', 'indicator_group']))

        scale_x_datetime_kwargs = {
            'limits': (start, end)
        }
        query_timedelta = end - start
        if query_timedelta <= pd.Timedelta(days=2):
            LOG.debug('Using short-time logic for calculating time-axis breaks in plot.')
            # max 24 labels
            step_size_hours = (2 if query_timedelta.total_seconds() > 24 * 3600 else 1) * facet_column_count
            scale_x_datetime_kwargs['date_breaks'] = '%d hours' % step_size_hours
            scale_x_datetime_kwargs['labels'] = lambda breaks: [b.strftime("%Y-%m-%d %H:%M:%S") if b.hour == 0 else
                                                                b.strftime("%H:%M:%S") for b in breaks]
        else:
            LOG.debug('Using long-time logic for calculating time-axis breaks in plot.')
            max_stepsize_days = ceil(query_timedelta.days / 4)
            step_size_days = min(max(2, int(query_timedelta.days / 30) * 2) * facet_column_count,
                                 max_stepsize_days)  # at least 4, max 20 labels
            scale_x_datetime_kwargs['date_breaks'] = '%d days' % step_size_days
            scale_x_datetime_kwargs['labels'] = lambda breaks: [b.strftime("%Y-%m-%d") for b in breaks]

        plot = ggplot(molten_data, aes(x=self.get_time_column(), y='value', color='equipment')) + \
            geom_point() + geom_line() + \
            facet_grid('indicator + template + indicator_group ~ .', scales='free') + \
            default_plot_theme() + \
            theme(figure_size=(10 * facet_column_count, 3 * facet_row_count)) + \
            scale_x_datetime(**scale_x_datetime_kwargs)

        return plot

    def merge(self, other: DSCTimeseriesWrapper, leading_equipment: Equipment) -> DSCTimeseriesWrapper:
        """
        Join two timeseries datasets.

        The two datasets may both contain only a single equipment, merging datasets where each datset contains
        more than one equipment is currently not supported. The equipment used as identifier in the final dataset
        must be provided in the `leading_equipment` parameter. The resulting join is an 'outer' join of the
        two datasets, and will contain a row for each timestamp occuring in at least one of the input datasets.

        Parameters
        ----------
        other
            Timeseries data which is merged with an original timeseries.
        leading_equipment
            Equipment used as a identifier in a final dataset.
        """
        # required to avoid circular imports. which is aweful. not sure about the best way to approach this though
        from .equipment import EquipmentSet

        if other is None:
            warnings.warn('DSCTimeseriesWrapper merge: other is None, returning self.')
            return self

        left = self.as_df().reset_index()
        right = other.as_df().reset_index()

        if left['equipment_id'].nunique() != 1 or right['equipment_id'].nunique() != 1:
            raise NotImplementedError('Dataset merge currently only possible for datasets with unique equipments.')

        if self.nominal_interval != other.nominal_interval:
            raise RuntimeError('Dataset merge currently only possible for datasets with the same nominal_interval.')

        if self.nominal_data_start != other.nominal_data_start or self.nominal_data_end != other.nominal_data_end:
            raise RuntimeError('Dataset merge currently only possible for '
                               'datasets with the same nominal start and end timestamps.')

        left['equipment_id'] = leading_equipment.id
        left['equipment_model_id'] = leading_equipment.equipment_model_id
        right['equipment_id'] = leading_equipment.id
        right['equipment_model_id'] = leading_equipment.equipment_model_id

        new_df = pd.merge(left, right, how='outer')

        return DSCTimeseriesWrapper(new_df, self._feature_details + other._feature_details,
                                    EquipmentSet([leading_equipment]), self.nominal_interval,
                                    self.nominal_data_start, self.nominal_data_end)

    def union(self, other: DSCTimeseriesWrapper) -> DSCTimeseriesWrapper:
        """Calculate the union of two DSCTimeseriesWrappers.

        Parameters
        ----------
        other
            Second timeseries data to union with.
        """
        if self.nominal_interval != other.nominal_interval:
            raise RuntimeError('Dataset union currently only possible for datasets with the same nominal_interval.')

        if self.nominal_data_start != other.nominal_data_start or self.nominal_data_end != other.nominal_data_end:
            raise RuntimeError('Dataset merge currently only possible for '
                               'datasets with the same nominal start and end timestamps.')

        combined_equipment_set = self._equipment_set + other._equipment_set

        new_df = pd.concat([self._df, other._df], join='outer')
        return DSCTimeseriesWrapper(new_df, self._feature_details + other._feature_details,
                                    combined_equipment_set, self.nominal_interval,
                                    self.nominal_data_start, self.nominal_data_end)

    def normalize(self, fitted_scaler=None, scaler=StandardScaler(copy=True, with_mean=True, with_std=True)) \
            -> tuple[DSCTimeseriesWrapper, Any]:
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
            DSCTimeseriesWrapper with self._df updated to be the normalized dataframe.
        fitted_scaler
            Fitted scaler to be used to normalize the data.
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
        new_wrapper = DSCTimeseriesWrapper(normalized_df, self._feature_details,
                                           self._equipment_set, self.nominal_interval,
                                           self.nominal_data_start, self.nominal_data_end,
                                           is_normalized=True)

        return new_wrapper, fitted_scaler

    def filter(self, equipment_ids: Iterable[str] = None, start: Union[str, pd.Timestamp, datetime] = None,
               end: Union[str, pd.Timestamp, datetime] = None) -> DSCTimeseriesWrapper:
        """Return a new DSCTimeseriesWrapper extracted from an original data with filter parameters.

        Only indicator data specified in filters are returned.

        Parameters
        ----------
        equipment_ids
            Optional equipment set ids to filter timeseries data.
        start
            Optional start time of timeseries data are returned.
        end
            Optional end time until timeseries data are returned.
        """
        if isinstance(equipment_ids, str):
            equipment_ids = [equipment_ids]

        if equipment_ids is None:
            equipment_ids = [equipment.id for equipment in self._equipment_set]
        start_time = any_to_timestamp(start, default=self.nominal_data_start)
        end_time = any_to_timestamp(end, default=self.nominal_data_end)
        selected_equi_set = self._equipment_set.filter(id=equipment_ids)

        selected_df = self._df.query('(equipment_id in @equipment_ids) &'
                                     '(timestamp >= @start_time) & (timestamp <= @end_time)')

        if len(selected_df) == 0:
            warnings.warn('The selected filters removed all data, the resulting DSCTimeseriesWrapper is empty.')
        LOG.debug('Filtered Dataset contains %s rows.', len(selected_df))

        return DSCTimeseriesWrapper(selected_df, self._feature_details, selected_equi_set,
                                    self.nominal_interval, start_time, end_time, self.is_normalized)
