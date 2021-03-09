import pytest
import pandas as pd

from sailor.assetcentral.indicators import IndicatorSet
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
    data = pd.DataFrame({
        'equipment_id': ['equipment_id_1'] * rows_per_equipment + ['equipment_id_2'] * rows_per_equipment,
        'model_id': ('equipment_model_id_1', ) * rows_per_equipment * 2,
        'timestamp': list(pd.date_range(nominal_start_date, freq='10min', periods=rows_per_equipment, tz='Etc/UTC'))*2,
        indicator_1._unique_id: range(rows_per_equipment*2),
        indicator_2._unique_id: list(range(rows_per_equipment))*2
    })
    return TimeseriesDataset(data, indicator_set, equipment_set, nominal_start_date, nominal_end_date)


@pytest.mark.parametrize('description,aggregation_functions,expected_indicator_count', [
    ('one function string', 'mean', 2),
    ('one function callable', max, 2),
    ('two functions string', ['min', 'max'], 4),
    ('two functions callable', [min, max], 4),
    ('mixed function type', ['min', max], 4)
])
def test_aggregation_happy_path(simple_dataset, aggregation_functions, expected_indicator_count, description):
    aggregate_dataset = simple_dataset.aggregate('20min', aggregation_functions=aggregation_functions)
    assert all(aggregate_dataset._df.groupby('equipment_id').timestamp.count() == 50)
    assert len(aggregate_dataset._indicator_set) == expected_indicator_count
    assert aggregate_dataset._df.timestamp.min() == simple_dataset._df.timestamp.min()
    assert aggregate_dataset._df.timestamp.max() <= simple_dataset._df.timestamp.max()
