"""
Indicators module can be used to retrieve Indicator information from AssetCentral.

Classes are provided for individual Indicators as well as groups of Indicators (IndicatorSet).
Note that the indicators here represent 'materialized' indicators, i.e. indicators attached to an equipment.
Hence they contain information on indicator_group and template used to attach it to the equipment. Currently there
is no support for unrealized 'Indicator Templates'.
"""
import hashlib
from functools import cached_property

from sailor import _base
from .utils import (AssetcentralEntity, _AssetcentralField, AssetcentralEntitySet)

_INDICATOR_FIELDS = [
    _AssetcentralField('name', 'indicatorName'),
    _AssetcentralField('indicator_group_name', 'indicatorGroupName'),
    _AssetcentralField('type', 'indicatorType'),
    _AssetcentralField('uom_description', 'UOMDescription'),
    _AssetcentralField('dimension_description', 'dimensionDesc'),
    _AssetcentralField('description', 'indicatorDesc'),
    _AssetcentralField('indicator_group_description', 'indicatorGroupDesc'),
    _AssetcentralField('uom', 'UOM'),
    _AssetcentralField('dimension', 'dimension'),
    _AssetcentralField('datatype', 'dataType'),
    _AssetcentralField('id', 'propertyId'),
    _AssetcentralField('dimension_id', 'Dimension'),
    _AssetcentralField('model_id', 'objectId'),
    _AssetcentralField('indicator_group_id', 'pstid'),
    _AssetcentralField('template_id', 'categoryID'),
    _AssetcentralField('_liot_id', 'propertyId', get_extractor=lambda v: 'I_' + v),
    _AssetcentralField('_liot_group_id', 'pstid', get_extractor=lambda v: 'IG_' + v),
    _AssetcentralField('_indicator_source', 'indicatorSource'),
    _AssetcentralField('_aggregate_update_timestamp', 'aggUpdatedTimestamp'),
    _AssetcentralField('_indicator_category', 'indicatorCategory'),
    _AssetcentralField('_color_code', 'colorCode'),
    _AssetcentralField('_threshold_description', 'thresholdDescription'),
    _AssetcentralField('_converted_aggregate_value', 'convertedAggregatedValue'),
    _AssetcentralField('_trend', 'trend'),
    _AssetcentralField('_converted_UOM_description', 'convertedUOMDesc'),
    _AssetcentralField('_converted_UOM', 'convertedUOM'),
    _AssetcentralField('_indicator_color_code', 'indicatorColorCode'),
    _AssetcentralField('_is_favorite', 'isFavorite'),
    _AssetcentralField('_dimension_description', 'DimensionDesc'),  # duplicate
    _AssetcentralField('_uom', 'uom'),  # duplicate
    _AssetcentralField('_uom_description', 'uomdescription'),  # duplicate
]


@_base.add_properties
class Indicator(AssetcentralEntity):
    """AssetCentral Indicator Object."""

    _field_map = {field.our_name: field for field in _INDICATOR_FIELDS}

    @cached_property
    def _unique_id(self):
        m = hashlib.sha256()
        unique_string = self.id + self.indicator_group_id + self.template_id
        m.update(unique_string.encode())
        return m.hexdigest()

    def __eq__(self, other):
        """Determine whether two (materialized) indicator instances are equal."""
        return isinstance(other, self.__class__) and other._unique_id == self._unique_id

    def __hash__(self):
        """Hash of an indicator object is the hash of it's unique id."""
        return self._unique_id.__hash__()


class AggregatedIndicator(Indicator):
    """An extension of the AssetCentral Indicator object that additionally holds aggregation information."""

    def __init__(self, ac_json, aggregation_function):
        super(AggregatedIndicator, self).__init__(ac_json)
        self.aggregation_function = aggregation_function

    @cached_property
    def _unique_id(self):
        m = hashlib.sha256()
        unique_string = self.id + self.indicator_group_id + self.template_id + self.aggregation_function
        m.update(unique_string.encode())
        return m.hexdigest()

    @property
    def _iot_column_header(self):
        return f'{self._liot_id}_{self.aggregation_function}'


class IndicatorSet(AssetcentralEntitySet):
    """Class representing a group of Indicators."""

    _element_type = Indicator
    _method_defaults = {
        'plot_distribution': {
            'by': 'indicator_group_name',
        },
    }

    def _unique_id_to_names(self):
        """Get details on an opaque column_id in terms of AssetCentral names."""
        mapping = {}
        for indicator in self:
            mapping[indicator._unique_id] = (
                indicator.template_id,  # apparently fetching the template name would need a remote call
                indicator.indicator_group_name,
                indicator.name,
            )
        return mapping

    def _unique_id_to_constituent_ids(self):
        """Get details on an opaque column_id in terms of AssetCentral IDs."""
        mapping = {}
        for indicator in self:
            mapping[indicator._unique_id] = (
                indicator.template_id,
                indicator.indicator_group_id,
                indicator.id,
            )
        return mapping


class AggregatedIndicatorSet(IndicatorSet):
    """Class representing a group of AggregatedIndicators."""

    _element_type = AggregatedIndicator

    def _unique_id_to_names(self):
        """Get details on an opaque column_id in terms of AssetCentral names and aggregation_function."""
        mapping = {}
        for indicator in self:
            mapping[indicator._unique_id] = (
                indicator.template_id,  # apparently fetching the template name would need a remote call
                indicator.indicator_group_name,
                indicator.name,
                indicator.aggregation_function,
            )
        return mapping

    def _unique_id_to_constituent_ids(self):
        """Get details on an opaque column_id in terms of AssetCentral IDs and aggregation_function."""
        mapping = {}
        for indicator in self:
            mapping[indicator._unique_id] = (
                indicator.template_id,
                indicator.indicator_group_id,
                indicator.id,
                indicator.aggregation_function,
            )
        return mapping

    @classmethod
    def _from_indicator_set_and_aggregation_functions(cls, indicators, aggregation_functions):
        aggregated_indicators = []
        for indicator in indicators:
            for aggregation_function in aggregation_functions:
                aggregated_indicators.append(AggregatedIndicator(indicator.raw.copy(), aggregation_function))

        return cls(aggregated_indicators)

# while there is a generic '/services/api/v1/indicators' endpoint that allows to find indicators,
# that endpoint returns a very different object from the one that you can find via the equipment.
# it only has properties 'id', 'dataType', 'description' and 'internalId', which makes it incompatible
# with property mapping above. Therefore, `find_indicators` is not implemented here...
