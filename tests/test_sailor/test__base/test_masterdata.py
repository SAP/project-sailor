from unittest.mock import patch

import pandas as pd
import pytest

import sailor._base as _base
from sailor.assetcentral.utils import AssetcentralEntity
from sailor.pai.utils import PredictiveAssetInsightsEntity


@pytest.mark.parametrize('input,expected', [
    (1, '1d'),
    ('1', '1d'),
    (1.333, '1.333d'),
    ('1.333', '1.333d'),
    ('null', 'null'),
    (None, 'null')
])
def test_qt_double(input, expected):
    actual = _base.masterdata._qt_double(input)
    assert actual == expected


@pytest.mark.parametrize('input,expected', [
    (1, "'1'"),
    ('1', "'1'"),
    (True, "'1'"),
    (0, "'0'"),
    ('0', "'0'"),
    (False, "'0'"),
    ('null', 'null'),
    (None, 'null')
])
def test_qt_boolean_int_string(input, expected):
    actual = _base.masterdata._qt_boolean_int_string(input)
    assert actual == expected


@pytest.mark.parametrize('input,expected', [
    ('2020-01-01', "'2020-01-01'"),
    ('2020-01-01 12:15:00+02:00', "'2020-01-01'"),
    ("'2020-01-01'", "'2020-01-01'"),
    ("'2020-01-01 12:15:00+02:00'", "'2020-01-01'"),
    (pd.Timestamp('2020-01-01 00:00:00+00:00'), "'2020-01-01'"),
    (pd.Timestamp('2020-01-01 00:00:00+02:00'), "'2019-12-31'"),
    ('null', 'null'),
    (None, 'null')
])
@pytest.mark.filterwarnings('ignore:Trying to parse non-timezone-aware timestamp')
@pytest.mark.filterwarnings('ignore:Casting timestamp to date, this operation will lose time-of-day information')
def test_qt_date(input, expected):
    actual = _base.masterdata._qt_date(input)
    assert actual == expected


@pytest.mark.parametrize('input,expected', [
    ('2020-01-01', "'2020-01-01T00:00:00Z'"),
    ('2020-01-01 12:15:00+02:00', "'2020-01-01T10:15:00Z'"),
    ("'2020-01-01'", "'2020-01-01T00:00:00Z'"),
    ("'2020-01-01 12:15:00+02:00'", "'2020-01-01T10:15:00Z'"),
    (pd.Timestamp('2020-01-01 00:00:00+00:00'), "'2020-01-01T00:00:00Z'"),
    (pd.Timestamp('2020-01-01 00:00:00+02:00'), "'2019-12-31T22:00:00Z'"),
    ('null', 'null'),
    (None, 'null')
])
@pytest.mark.filterwarnings('ignore:Trying to parse non-timezone-aware timestamp')
def test_qt_timestamp(input, expected):
    actual = _base.masterdata._qt_timestamp(input)
    assert actual == expected


@pytest.mark.parametrize('input,expected', [
    ('2020-01-01', "datetimeoffset'2020-01-01T00:00:00Z'"),
    ('2020-01-01 12:15:00+02:00', "datetimeoffset'2020-01-01T10:15:00Z'"),
    ("'2020-01-01'", "datetimeoffset'2020-01-01T00:00:00Z'"),
    ("'2020-01-01 12:15:00+02:00'", "datetimeoffset'2020-01-01T10:15:00Z'"),
    (pd.Timestamp('2020-01-01 00:00:00+00:00'), "datetimeoffset'2020-01-01T00:00:00Z'"),
    (pd.Timestamp('2020-01-01 00:00:00+02:00'), "datetimeoffset'2019-12-31T22:00:00Z'"),
    ('null', 'null'),
    (None, 'null')
])
@pytest.mark.filterwarnings('ignore:Trying to parse non-timezone-aware timestamp')
def test_qt_odata_datetimeoffset(input, expected):
    actual = _base.masterdata._qt_odata_datetimeoffset(input)
    assert actual == expected


def test_qt_non_filterable():
    with pytest.raises(RuntimeError, match='Filtering on "my_field" is not supported by AssetCentral'):
        _base.masterdata._qt_non_filterable('my_field')('ignored_value')


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

    def test_get_available_properties_is_not_empty(self):
        # note: __subclasses__ requires that all subclasses are imported
        # currently we ensure this transitively: see __init__.py in test_base
        abstract_classes = _base.MasterDataEntity.__subclasses__()
        classes = sum((class_.__subclasses__() for class_ in abstract_classes), start=list())
        for class_ in classes:
            actual = class_.get_available_properties()
            assert actual, f'actual result for {class_.__name__} is empty: {actual}'
            assert type(actual) == set

    def test_id_in_field_map(self):
        abstract_classes = _base.MasterDataEntity.__subclasses__()
        classes = sum((class_.__subclasses__() for class_ in abstract_classes), start=list())
        for class_ in classes:
            assert 'id' in class_._field_map

    def test_repr_starts_with_classname(self):
        abstract_classes = _base.MasterDataEntity.__subclasses__()
        classes = sum((class_.__subclasses__() for class_ in abstract_classes), start=list())
        for class_ in classes:
            object_ = class_({'id': 1})
            assert str(object_).startswith(class_.__name__)


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
