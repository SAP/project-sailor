import pandas as pd
from numpy.random import default_rng

from sailor.sap_iot import TimeseriesDataset


def make_dataset(indicator_set, equipment_set, rows_per_equipment=100,
                 nominal_start_date=pd.Timestamp('2021-01-01', tz='Etc/UTC'),
                 nominal_end_date=pd.Timestamp('2021-01-03', tz='Etc/UTC')):
    generator = default_rng(seed=42)

    def make_random_timestamps():
        start_u = nominal_start_date.value // 10 ** 9
        end_u = nominal_end_date.value // 10 ** 9
        epochs = generator.integers(start_u, end_u, rows_per_equipment*len(equipment_set))
        return pd.to_datetime(epochs, unit='s', utc=True).tz_convert('Etc/UTC')

    equipment_ids = [equipment.id for equipment in equipment_set]

    data = pd.DataFrame({
        'equipment_id': equipment_ids * rows_per_equipment,
        'timestamp': make_random_timestamps(),
    }).sort_values(['equipment_id', 'timestamp']).reset_index(drop=True)
    for indicator in indicator_set:
        data[indicator._unique_id] = generator.uniform(size=len(data))
    return TimeseriesDataset(data, indicator_set, equipment_set, nominal_start_date, nominal_end_date)


def get_template(indicator_group_id, indicator_group_name, indicators):
    template = [{ 'indicatorGroups': [{ 'id': indicator_group_id,
                                     'internalId' : indicator_group_name,
                                     'indicators' : indicators}]}]
    return template
