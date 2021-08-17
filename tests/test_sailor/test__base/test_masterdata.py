from sailor._base.masterdata import MasterDataEntity, MasterDataField, add_properties
from sailor.assetcentral.utils import AssetcentralEntity
from sailor.pai.utils import PredictiveAssetInsightsEntity


class TestMasterDataEntity:

    def test_magic_eq_true(self):
        entity1 = MasterDataEntity({'id': '1'})
        entity2 = MasterDataEntity({'id': '1'})
        assert entity1 == entity2

    def test_magic_eq_false_id(self):
        entity1 = MasterDataEntity({'id': '1'})
        entity2 = MasterDataEntity({'id': '2'})
        assert entity1 != entity2

    def test_magic_eq_false_class(self):
        entity1 = AssetcentralEntity({'id': '1'})
        entity2 = PredictiveAssetInsightsEntity({'id': '1'})
        assert entity1 != entity2

    def test_integration_with_fields(self):
        def get_extractor(value):
            return pow(value, 2)
        fields = [MasterDataField('our_name', 'their_name_get', 'their_name_put', get_extractor=get_extractor)]

        @add_properties
        class FieldTestEntity(MasterDataEntity):
            _field_map = {f.our_name: f for f in fields}
        entity = FieldTestEntity({'their_name_get': 9})

        assert entity.our_name == 81


def test_get_available_properties_is_not_empty():
    # note: __subclasses__ requires that all subclasses are imported
    # currently we ensure this transitively: see __init__.py in test_base
    abstract_classes = MasterDataEntity.__subclasses__()
    classes = sum((class_.__subclasses__() for class_ in abstract_classes), start=list())
    for class_ in classes:
        actual = class_.get_available_properties()
        assert actual, f'actual result for {class_.__name__} is empty: {actual}'
        assert type(actual) == set
