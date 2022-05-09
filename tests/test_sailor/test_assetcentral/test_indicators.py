import pytest

from sailor.assetcentral.indicators import Indicator, AggregatedIndicatorSet, IndicatorSet


class TestIndicatorSet:
    def test_get_name_mapping(self, make_indicator_set):
        indicator_set = make_indicator_set(categoryID=['template_id1', 'template_id2', 'template_id3'],
                                           indicatorGroupName=['group_name1', 'group_name2', 'group_name3'],
                                           indicatorName=['name1', 'name2', 'name3'],
                                           pstid=['group_id1', 'group_id2', 'group_id3'],
                                           propertyId=['id1', 'id2', 'id3'])
        expected = {
            '28167b628f42ab17d4e5c3b24aad45dc32591d7f47504a24fb3f728861849441':
                ('template_id1', 'group_name1', 'name1'),
            'dc2e887dbd74b179bc91e5d4bcd09ee9e438071c9b1258a44cbfce6060c2795f':
                ('template_id2', 'group_name2', 'name2'),
            '46039714247942c841944bbb6b0c528a415461567b0898c736c35e74917ba1d2':
                ('template_id3', 'group_name3', 'name3')
        }

        actual = indicator_set._unique_id_to_names()

        assert actual == expected

    def test_get_id_mapping(self, make_indicator_set):
        indicator_set = make_indicator_set(categoryID=['template_id1', 'template_id2', 'template_id3'],
                                           indicatorGroupName=['group_name1', 'group_name2', 'group_name3'],
                                           indicatorName=['name1', 'name2', 'name3'],
                                           pstid=['group_id1', 'group_id2', 'group_id3'],
                                           propertyId=['id1', 'id2', 'id3'])
        expected = {
            '28167b628f42ab17d4e5c3b24aad45dc32591d7f47504a24fb3f728861849441':
                ('template_id1', 'group_id1', 'id1'),
            'dc2e887dbd74b179bc91e5d4bcd09ee9e438071c9b1258a44cbfce6060c2795f':
                ('template_id2', 'group_id2', 'id2'),
            '46039714247942c841944bbb6b0c528a415461567b0898c736c35e74917ba1d2':
                ('template_id3', 'group_id3', 'id3')
        }

        actual = indicator_set._unique_id_to_constituent_ids()

        assert actual == expected


class TestAggregatedIndicatorSet:
    def test_get_name_mapping(self, make_aggregated_indicator_set):
        indicator_set = make_aggregated_indicator_set(categoryID=['template_id1', 'template_id2', 'template_id3'],
                                                      indicatorGroupName=['group_name1', 'group_name2', 'group_name3'],
                                                      indicatorName=['name1', 'name2', 'name3'],
                                                      pstid=['group_id1', 'group_id2', 'group_id3'],
                                                      propertyId=['id1', 'id2', 'id3'])
        expected = {
            'cd820aff501856801b804c76212e72e6f57d53e952ba6b54b36945278d94ed7a':
                ('template_id1', 'group_name1', 'name1', 'mean'),
            'c9e1c62ef7f6047e0b031ed9afa916d2c2e5642163d05d51cdddc0d2ff4fe98b':
                ('template_id2', 'group_name2', 'name2', 'mean'),
            '948b55399afb5675d367ac36154616bf081a3c5fb9c2cb5e1812fd01386a0633':
                ('template_id3', 'group_name3', 'name3', 'mean')
        }

        actual = indicator_set._unique_id_to_names()

        assert actual == expected

    def test_get_id_mapping(self, make_aggregated_indicator_set):
        indicator_set = make_aggregated_indicator_set(categoryID=['template_id1', 'template_id2', 'template_id3'],
                                                      indicatorGroupName=['group_name1', 'group_name2', 'group_name3'],
                                                      indicatorName=['name1', 'name2', 'name3'],
                                                      pstid=['group_id1', 'group_id2', 'group_id3'],
                                                      propertyId=['id1', 'id2', 'id3'])
        expected = {
            'cd820aff501856801b804c76212e72e6f57d53e952ba6b54b36945278d94ed7a':
                ('template_id1', 'group_id1', 'id1', 'mean'),
            'c9e1c62ef7f6047e0b031ed9afa916d2c2e5642163d05d51cdddc0d2ff4fe98b':
                ('template_id2', 'group_id2', 'id2', 'mean'),
            '948b55399afb5675d367ac36154616bf081a3c5fb9c2cb5e1812fd01386a0633':
                ('template_id3', 'group_id3', 'id3', 'mean')
        }

        actual = indicator_set._unique_id_to_constituent_ids()

        assert actual == expected


class TestSystemIndicatorSet:
    def test_get_name_mapping(self, make_system_indicator_set):
        indicator_set = make_system_indicator_set(categoryID=['template_id1', 'template_id2', 'template_id3'],
                                                  indicatorGroupName=['group_name1', 'group_name2', 'group_name3'],
                                                  indicatorName=['name1', 'name2', 'name3'],
                                                  pstid=['group_id1', 'group_id2', 'group_id3'],
                                                  propertyId=['id1', 'id2', 'id3'])
        expected = {
            'f8ab63e7bfd4d50e0d48457c552a66e8e67de6f31c8bee666d43faf2a689993b':
                ('template_id1', 'group_name1', 'name1', 42),
            'e5c9ad2f4e00f95906fab478a6a7e667aeac2c7b74a304b3938d01cdef50cb7d':
                ('template_id2', 'group_name2', 'name2', 42),
            '5c9945c4eedaa4abdf2287eb9434d082af28b1e31cf471056a26cb3f1891143d':
                ('template_id3', 'group_name3', 'name3', 42)
        }

        actual = indicator_set._unique_id_to_names()

        assert actual == expected

    def test_get_id_mapping(self, make_system_indicator_set):
        indicator_set = make_system_indicator_set(categoryID=['template_id1', 'template_id2', 'template_id3'],
                                                  indicatorGroupName=['group_name1', 'group_name2', 'group_name3'],
                                                  indicatorName=['name1', 'name2', 'name3'],
                                                  pstid=['group_id1', 'group_id2', 'group_id3'],
                                                  propertyId=['id1', 'id2', 'id3'])
        expected = {
            'f8ab63e7bfd4d50e0d48457c552a66e8e67de6f31c8bee666d43faf2a689993b':
                ('template_id1', 'group_id1', 'id1', 42),
            'e5c9ad2f4e00f95906fab478a6a7e667aeac2c7b74a304b3938d01cdef50cb7d':
                ('template_id2', 'group_id2', 'id2', 42),
            '5c9945c4eedaa4abdf2287eb9434d082af28b1e31cf471056a26cb3f1891143d':
                ('template_id3', 'group_id3', 'id3', 42)
        }

        actual = indicator_set._unique_id_to_constituent_ids()

        assert actual == expected


class TestSystemAggregatedIndicatorSet:
    def test_get_name_mapping(self, make_system_aggregated_indicator_set):
        indicator_set = make_system_aggregated_indicator_set(categoryID=['template_id1', 'template_id2',
                                                                         'template_id3'],
                                                             indicatorGroupName=['group_name1', 'group_name2',
                                                                                 'group_name3'],
                                                             indicatorName=['name1', 'name2', 'name3'],
                                                             pstid=['group_id1', 'group_id2', 'group_id3'],
                                                             propertyId=['id1', 'id2', 'id3'])
        expected = {
            '7fb80e20b84327debdbb7d720850c80d7f988b27df52e318feb38ac048d80ea1':
                ('template_id1', 'group_name1', 'name1', 'mean', 42),
            'c98eea24824ecbf34133e649a79c00985df765de8179fab338949d35e39cb6c5':
                ('template_id2', 'group_name2', 'name2', 'mean', 42),
            '6d6e475c82438dc6e11accca81c79f2be6264b643dcc8b9401a29e7c6168712f':
                ('template_id3', 'group_name3', 'name3', 'mean', 42)
        }

        actual = indicator_set._unique_id_to_names()

        assert actual == expected

    def test_get_id_mapping(self, make_system_aggregated_indicator_set):
        indicator_set = make_system_aggregated_indicator_set(categoryID=['template_id1', 'template_id2',
                                                                         'template_id3'],
                                                             indicatorGroupName=['group_name1', 'group_name2',
                                                                                 'group_name3'],
                                                             indicatorName=['name1', 'name2', 'name3'],
                                                             pstid=['group_id1', 'group_id2', 'group_id3'],
                                                             propertyId=['id1', 'id2', 'id3'])
        expected = {
            '7fb80e20b84327debdbb7d720850c80d7f988b27df52e318feb38ac048d80ea1':
                ('template_id1', 'group_id1', 'id1', 'mean', 42),
            'c98eea24824ecbf34133e649a79c00985df765de8179fab338949d35e39cb6c5':
                ('template_id2', 'group_id2', 'id2', 'mean', 42),
            '6d6e475c82438dc6e11accca81c79f2be6264b643dcc8b9401a29e7c6168712f':
                ('template_id3', 'group_id3', 'id3', 'mean', 42)
        }

        actual = indicator_set._unique_id_to_constituent_ids()

        assert actual == expected


@pytest.mark.parametrize('set_class,expected_message', [
    (IndicatorSet, 'IndicatorSet may only contain elements of type Indicator, not AggregatedIndicator'),
    (AggregatedIndicatorSet, 'AggregatedIndicatorSet may only contain elements of type AggregatedIndicator'),
])
def test_mixed_sets_not_allowed(set_class, expected_message, make_indicator, make_aggregated_indicator):
    normal_indicator = make_indicator(propertyId='normal_indicator')
    aggregated_indicator = make_aggregated_indicator(propertyId='aggregated_indicator')

    with pytest.raises(RuntimeError, match=expected_message):
        set_class([normal_indicator, aggregated_indicator])


def test_expected_public_attributes_are_present():
    expected_attributes = [
        'name', 'indicator_group_name', 'type', 'uom_description', 'dimension_description',
        'description', 'indicator_group_description', 'uom', 'dimension', 'datatype', 'id',
        'dimension_id', 'model_id', 'indicator_group_id', 'template_id',
    ]

    fieldmap_public_attributes = [
        field.our_name for field in Indicator._field_map.values() if field.is_exposed
    ]

    assert expected_attributes == fieldmap_public_attributes
