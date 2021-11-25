
from sailor.assetcentral.workorder import Workorder


def test_expected_public_attributes_are_present():
    expected_attributes = [
        'name', 'type_description', 'priority_description', 'status_text', 'short_description',
        'equipment_name', 'location', 'plant', 'start_date', 'end_date', 'long_description',
        'id', 'equipment_id', 'model_id', 'type'
    ]

    fieldmap_public_attributes = [
        field.our_name for field in Workorder._field_map.values() if field.is_exposed
    ]

    assert expected_attributes == fieldmap_public_attributes
