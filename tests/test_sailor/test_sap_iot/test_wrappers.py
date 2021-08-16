import math

import pytest
import pandas as pd

from sailor.assetcentral.indicators import IndicatorSet
from sailor.assetcentral.equipment import EquipmentSet
from sailor.sap_iot.wrappers import TimeseriesDataset
from ..data_generators import make_dataset


@pytest.fixture
def simple_dataset(make_indicator_set, make_equipment_set):
    indicator_set = make_indicator_set(propertyId=('indicator_id_1', 'indicator_id_2'))
    equipment_set = make_equipment_set(
        equipmentId=('equipment_id_1', 'equipment_id_2'),
        modelId=('equipment_model_id_1', 'equipment_model_id_1')
    )

    return make_dataset(indicator_set, equipment_set)


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

    assert len(aggregate_dataset.indicator_set) == expected_indicator_count
    assert aggregate_dataset._df.timestamp.min() <= simple_dataset._df.timestamp.min()
    assert aggregate_dataset._df.timestamp.min() > simple_dataset._df.timestamp.min() - interval
    assert aggregate_dataset._df.timestamp.max() <= simple_dataset._df.timestamp.max()
    assert aggregate_dataset._df.timestamp.max() > simple_dataset._df.timestamp.max() - interval


def test_interpolation_happy_path(simple_dataset):
    interval = pd.Timedelta('20min')
    expected_count = math.ceil((simple_dataset.nominal_data_end - simple_dataset.nominal_data_start) / interval)

    interpolated_dataset = simple_dataset.interpolate(interval)

    assert all(interpolated_dataset._df.groupby('equipment_id').timestamp.count() == expected_count)
    assert interpolated_dataset.indicator_set == simple_dataset.indicator_set
    assert interpolated_dataset._df.timestamp.min() == simple_dataset.nominal_data_start
    assert interpolated_dataset._df.timestamp.max() < simple_dataset.nominal_data_end


@pytest.mark.parametrize('method,expect_ffill,expect_bfill', [
    ('pad', True, False),
    ('slinear', False, False),
    ('bfill', False, True)
])
def test_interpolate_missing_data(simple_dataset, method, expect_ffill, expect_bfill):
    test_dataset = simple_dataset.filter(equipment_set=simple_dataset.equipment_set.filter(id='equipment_id_1'))
    actual_start = test_dataset._df.timestamp.min()
    actual_end = test_dataset._df.timestamp.max()

    test_dataset.nominal_data_start = (actual_start - pd.Timedelta('1h')).round('1h')
    test_dataset.nominal_data_end = actual_end + pd.Timedelta('1h')
    remove_times = ((test_dataset._df.timestamp >= actual_start + pd.Timedelta('1h')) &
                    (test_dataset._df.timestamp < actual_start + pd.Timedelta('3h')))
    for indicator in test_dataset.indicator_set:
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


@pytest.mark.filterwarnings('ignore:Passing equipment_ids to the TimeseriesDataset filter is deprecated')
def test_filter_equipment_id_only(simple_dataset):
    filtered_dataset = simple_dataset.filter(equipment_ids=['equipment_id_1'])

    assert len(filtered_dataset.equipment_set) == 1
    assert len(filtered_dataset._df) == 100
    assert filtered_dataset._df.equipment_id.unique() == ['equipment_id_1']
    assert filtered_dataset.indicator_set == simple_dataset.indicator_set


def test_filter_equipment_set_only(simple_dataset):
    filtered_dataset = simple_dataset.filter(equipment_set=simple_dataset.equipment_set.filter(id='equipment_id_1'))

    assert len(filtered_dataset.equipment_set) == 1
    assert len(filtered_dataset._df) == 100
    assert filtered_dataset._df.equipment_id.unique() == ['equipment_id_1']
    assert filtered_dataset.indicator_set == simple_dataset.indicator_set


@pytest.mark.filterwarnings('ignore:Passing equipment_ids to the TimeseriesDataset filter is deprecated')
def test_filter_equipment_set_and_id(simple_dataset):
    filtered_dataset = simple_dataset.filter(equipment_ids=['equipment_id_2'],
                                             equipment_set=simple_dataset.equipment_set.filter(id='equipment_id_1'))

    assert len(filtered_dataset.equipment_set) == 1
    assert len(filtered_dataset._df) == 100
    assert filtered_dataset._df.equipment_id.unique() == ['equipment_id_1']
    assert filtered_dataset.indicator_set == simple_dataset.indicator_set


def test_filter_indicator_set(simple_dataset):
    selected_indicators = simple_dataset.indicator_set.filter(id='indicator_id_1')

    filtered_dataset = simple_dataset.filter(indicator_set=selected_indicators)

    assert len(filtered_dataset.equipment_set) == 2
    assert len(filtered_dataset._df) == len(simple_dataset._df)
    assert filtered_dataset.indicator_set == selected_indicators
    assert len(filtered_dataset._df.columns) == 3
    assert all(filtered_dataset._df.columns == (filtered_dataset.get_index_columns(include_model=False) +
                                                [indicator._unique_id for indicator in selected_indicators]))


@pytest.mark.parametrize('include_model', [True, False])
def test_as_df_no_indicators(include_model):
    df = pd.DataFrame({'equipment_id': [], 'timestamp': pd.to_datetime([], utc=True)})
    df = df.astype({'equipment_id': 'object'})
    data = TimeseriesDataset(df, IndicatorSet([]), EquipmentSet([]),
                             pd.Timestamp('2021-01-01', tz='Etc/UTC'), pd.Timestamp('2021-01-03', tz='Etc/UTC'))

    data.as_df(speaking_names=True, include_model=include_model)
    # this used to lead to a TypeError, we're effectively testing that doesn't happen.


def test_plotting_happy_path(simple_dataset):
    simple_dataset.plot()


def test_normalize_happy_path(simple_dataset):
    normalized_dataset, _ = simple_dataset.normalize()

    assert all(normalized_dataset._df.columns == simple_dataset._df.columns)
    assert len(normalized_dataset._df) == len(simple_dataset._df)
