from unittest.mock import patch

import pytest

import sailor._base as _base
from sailor.assetcentral.utils import AssetcentralEntity
from sailor.pai.utils import PredictiveAssetInsightsEntity


class TestMasterDataEntity:

    def test_magic_eq_true(self):
        entity1 = _base.MasterDataEntity({'id': '1'})
        entity2 = _base.MasterDataEntity({'id': '1'})
        assert entity1 == entity2

    def test_magic_eq_false_id(self):
        entity1 = _base.MasterDataEntity({'id': '1'})
        entity2 = _base.MasterDataEntity({'id': '2'})
        assert entity1 != entity2

    def test_magic_eq_false_class(self):
        entity1 = AssetcentralEntity({'id': '1'})
        entity2 = PredictiveAssetInsightsEntity({'id': '1'})
        assert entity1 != entity2

    def test_integration_with_fields(self):
        def get_extractor(value):
            return pow(value, 2)
        fields = [_base.MasterDataField('our_name', 'their_name_get', 'their_name_put', get_extractor=get_extractor)]

        @_base.add_properties
        class FieldTestEntity(_base.MasterDataEntity):
            _field_map = {f.our_name: f for f in fields}
        entity = FieldTestEntity({'their_name_get': 9})

        assert entity.our_name == 81


class TestMasterDataEntitySet:
    test_classes = sum((class_.__subclasses__() for class_ in _base.MasterDataEntitySet.__subclasses__()), start=[])

    @patch('sailor._base.masterdata.p9')
    @pytest.mark.parametrize('cls', test_classes)
    def test_integration_with_subclasses(self, mock_p9, cls):
        result_set_obj = cls([])
        result_set_obj.as_df()
        result_set_obj.plot_distribution()

    @pytest.mark.parametrize('cls', test_classes)
    def test_resultset_method_defaults(self, cls):
        element_properties = cls._element_type._field_map
        assert cls._method_defaults['plot_distribution']['by'] in element_properties

    def test_magic_eq_type_not_equal(self):
        rs1 = _base.MasterDataEntitySet([_base.MasterDataEntity({'id': x}) for x in [1, 2, 3]])
        rs2 = (1, 2, 3)
        assert rs1 != rs2

    @pytest.mark.parametrize('testdescription,list1,list2,expected_result', [
        ('Order does not matter', [1, 2, 3], [2, 3, 1], True),
        ('Different content', [1, 2, 3], [1, 2, 4], False),
        ('Different size', [1, 2, 3, 4], [1, 2, 3], False),
        ('Equal content and order', [1, 2, 3], [1, 2, 3], True),
        ('Two empty sets are equal', [], [], True),
    ])
    def test_magic_eq_content(self, list1, list2, expected_result, testdescription):
        rs1 = _base.MasterDataEntitySet([_base.MasterDataEntity({'id': i}) for i in list1])
        rs2 = _base.MasterDataEntitySet([_base.MasterDataEntity({'id': i}) for i in list2])
        if expected_result:
            assert rs1 == rs2
        else:
            assert rs1 != rs2


def test_get_available_properties_is_not_empty():
    # note: __subclasses__ requires that all subclasses are imported
    # currently we ensure this transitively: see __init__.py in test_base
    abstract_classes = _base.MasterDataEntity.__subclasses__()
    classes = sum((class_.__subclasses__() for class_ in abstract_classes), start=list())
    for class_ in classes:
        actual = class_.get_available_properties()
        assert actual, f'actual result for {class_.__name__} is empty: {actual}'
        assert type(actual) == set
