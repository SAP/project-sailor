from sailor.assetcentral.functional_location import FunctionalLocation


def test_expected_public_attributes_are_present():
    expected_attributes = [
        'name', 'model_name', 'status_text', 'short_description', 'manufacturer', 'operator',
        'crititcality_description', 'id', 'model_id', 'template_id', 'serial_number', 'batch_number']

    fieldmap_public_attributes = [
        field.our_name for field in FunctionalLocation._field_map.values() if field.is_exposed
    ]

    assert expected_attributes == fieldmap_public_attributes
