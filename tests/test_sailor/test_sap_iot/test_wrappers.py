import math

import pytest
from numpy.random import default_rng
import pandas as pd

from sailor.assetcentral.indicators import IndicatorSet
from sailor.assetcentral.equipment import EquipmentSet
from sailor.sap_iot.wrappers import TimeseriesDataset


@pytest.fixture
def simple_dataset(make_indicator, make_equipment_set):
    indicator_1 = make_indicator(propertyId='indicator_id_1', indicatorName='row_id')
    indicator_2 = make_indicator(propertyId='indicator_id_2', indicatorName='row_id_per_equipment')
    indicator_set = IndicatorSet([indicator_1, indicator_2])
    equipment_set = make_equipment_set(equipmentId=('equipment_id_1', 'equipment_id_2'))
    nominal_start_date = pd.Timestamp('2021-01-01', tz='Etc/UTC')
    nominal_end_date = pd.Timestamp('2021-01-03', tz='Etc/UTC')
    rows_per_equipment = 100

    generator = default_rng(seed=42)

    def make_random_timestamps():
        start_u = nominal_start_date.value // 10 ** 9
        end_u = nominal_end_date.value // 10 ** 9
        epochs = generator.integers(start_u, end_u, rows_per_equipment)
        return pd.to_datetime(epochs, unit='s', utc=True).tz_convert('Etc/UTC')

    data = pd.DataFrame({
        'equipment_id': ['equipment_id_1'] * rows_per_equipment + ['equipment_id_2'] * rows_per_equipment,
        'model_id': ('equipment_model_id_1', ) * rows_per_equipment * 2,
        'timestamp': [*make_random_timestamps(), *make_random_timestamps()],
        indicator_1._unique_id: range(rows_per_equipment*2),
        indicator_2._unique_id: list(range(rows_per_equipment))*2
    }).sort_values(['equipment_id', 'model_id', 'timestamp'])
    return TimeseriesDataset(data, indicator_set, equipment_set, nominal_start_date, nominal_end_date)


@pytest.mark.parametrize('description,aggregation_functions,expected_indicator_count', [
    ('one function string', 'mean', 2),
    ('one function callable', max, 2),
    ('two functions string', ['min', 'max'], 4),
    ('two functions callable', [min, max], 4),
    ('mixed function type', ['min', max], 4)
])
def test_aggregation_happy_path(simple_dataset, aggregation_functions, expected_indicator_count, description):
    interval = pd.Timedelta('20min')

    aggregate_dataset = simple_dataset.aggregate(interval, aggregation_functions=aggregation_functions)

    assert len(aggregate_dataset._indicator_set) == expected_indicator_count
    assert aggregate_dataset._df.timestamp.min() <= simple_dataset._df.timestamp.min()
    assert aggregate_dataset._df.timestamp.min() > simple_dataset._df.timestamp.min() - interval
    assert aggregate_dataset._df.timestamp.max() <= simple_dataset._df.timestamp.max()
    assert aggregate_dataset._df.timestamp.max() > simple_dataset._df.timestamp.max() - interval


def test_interpolation_happy_path(simple_dataset):
    interval = pd.Timedelta('20min')
    expected_count = math.ceil((simple_dataset.nominal_data_end - simple_dataset.nominal_data_start) / interval)

    interpolated_dataset = simple_dataset.interpolate(interval)

    assert all(interpolated_dataset._df.groupby('equipment_id').timestamp.count() == expected_count)
    assert interpolated_dataset._indicator_set == simple_dataset._indicator_set
    assert interpolated_dataset._df.timestamp.min() == simple_dataset.nominal_data_start
    assert interpolated_dataset._df.timestamp.max() < simple_dataset.nominal_data_end


@pytest.mark.parametrize('method,expect_ffill,expect_bfill', [
    ('pad', True, False),
    ('slinear', False, False),
    ('bfill', False, True)
])
def test_interpolate_missing_data(simple_dataset, method, expect_ffill, expect_bfill):
    test_dataset = simple_dataset.filter(['equipment_id_1'])
    actual_start = test_dataset._df.timestamp.min()
    actual_end = test_dataset._df.timestamp.max()

    test_dataset.nominal_data_start = (actual_start - pd.Timedelta('1h')).round('1h')
    test_dataset.nominal_data_end = actual_end + pd.Timedelta('1h')
    remove_times = ((test_dataset._df.timestamp >= actual_start + pd.Timedelta('1h')) &
                    (test_dataset._df.timestamp < actual_start + pd.Timedelta('3h')))
    for indicator in test_dataset._indicator_set:
        test_dataset._df.loc[remove_times, indicator._unique_id] = float('NaN')

    # this is not an regular test assert, but makes sure that during setup we actually introduced a 'hole' in the data
    assert test_dataset._df.loc[remove_times].isnull().all().any()

    interpolated_dataset = test_dataset.interpolate('1h', method=method)

    assert interpolated_dataset._df.timestamp.min() == test_dataset.nominal_data_start
    assert interpolated_dataset._df.timestamp.max() < test_dataset.nominal_data_end
    remove_times = ((interpolated_dataset._df.timestamp >= actual_start + pd.Timedelta('1h')) &
                    (interpolated_dataset._df.timestamp < actual_start + pd.Timedelta('3h')))
    assert not interpolated_dataset._df.loc[remove_times].isnull().any().any()

    if expect_bfill:
        assert not interpolated_dataset._df[interpolated_dataset._df.timestamp < actual_start].isnull().any().any()
    if expect_ffill:
        assert not interpolated_dataset._df[interpolated_dataset._df.timestamp > actual_end].isnull().any().any()


def test_as_df_no_indicators():
    df = pd.DataFrame({'equipment_id': [], 'model_id': [], 'timestamp': pd.to_datetime([], utc=True)})
    data = TimeseriesDataset(df, IndicatorSet([]), EquipmentSet([]),
                             pd.Timestamp('2021-01-01', tz='Etc/UTC'), pd.Timestamp('2021-01-03', tz='Etc/UTC'))

    data.as_df(speaking_names=True)  # this used to lead to a TypeError, we're effectively testing that doesn't happen.
