from sailor.assetcentral.location import Location


def test_expected_public_attributes_are_present():
    expected_attributes = ['name', 'short_description', 'type_description', 'id', 'type']

    fieldmap_public_attributes = [
        field.our_name for field in Location._field_map.values() if not field.our_name.startswith('_')
    ]

    assert expected_attributes == fieldmap_public_attributes
