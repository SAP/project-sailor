from sailor.assetcentral.failure_mode import FailureMode


def test_expected_public_attributes_are_present():
    expected_attributes = ['name', 'short_description', 'status_text', 'long_description', 'id']

    fieldmap_public_attributes = [
        field.our_name for field in FailureMode._field_map.values() if not field.our_name.startswith('_')
    ]

    assert expected_attributes == fieldmap_public_attributes
