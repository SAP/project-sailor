"""
Indicators module can be used to retrieve Indicator information from AssetCentral.

Classes are provided for individual Indicators as well as groups of Indicators (IndicatorSet).
Note that the indicators here represent 'materialized' indicators, i.e. indicators attached to an equipment.
Hence they contain information on indicator_group and template used to attach it to the equipment. Currently there
is no support for unrealized 'Indicator Templates'.
"""
import hashlib
from functools import cached_property

from .utils import _add_properties, AssetcentralEntity, ResultSet


@_add_properties
class Indicator(AssetcentralEntity):
    """AssetCentral Indicator Object."""

    # Properties (in AC terminology) are: categoryID, propertyId, indicatorGroupName, indicatorName,
    # indicatorGroupDesc, objectId, indicatorSource, aggUpdatedTimestamp, indicatorCategory, colorCode,
    # thresholdDescription, convertedAggregatedValue, trend, dataType, indicatorType, convertedUOMDesc,
    # UOM, convertedUOM, indicatorDesc, indicatorColorCode, isFavorite, UOMDescription, Dimension, DimensionDesc,
    # uomdescription, dimension, dimensionDesc, pstid, uom
    # TODO update field list - I think e.g. template id is also part of hte API response

    @classmethod
    def get_property_mapping(cls):
        """Return a mapping from assetcentral terminology to our terminology."""
        # TODO: There is still some weird stuff here, e.g. UOM vs. uom or convertedXXX
        return {
            'id': ('propertyId', None, None, None),
            'name': ('indicatorName', None, None, None),
            'description': ('indicatorDesc', None, None, None),
            'dimension_description': ('DimensionDescription', None, None, None),
            'dimension_id': ('Dimension', None, None, None),
            'indicator_group_description': ('indicatorGroupDesc', None, None, None),
            'indicator_group_id': ('pstid', None, None, None),
            'indicator_group_name': ('indicatorGroupName', None, None, None),
            'model_id': ('objectId', None, None, None),
            'template_id': ('categoryID', None, None, None),
            'type': ('indicatorType', None, None, None),
            'uom': ('UOM', None, None, None),
            'uom_description': ('UOMDescription', None, None, None),
            '_liot_id': ('propertyId', lambda self: 'I_' + self.raw.get('propertyId', None), None, None),
            '_liot_group_id': ('pstid', lambda self: 'IG_' + self.raw.get('pstid', None), None, None),
        }

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


class IndicatorSet(ResultSet):
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

# while there is a generic '/services/api/v1/indicators' endpoint that allows to find indicators,
# that endpoint returns a very different object from the one that you can find via the equipment.
# it only has properties 'id', 'dataType', 'description' and 'internalId', which makes it incompatible
# with property mapping above. Therefore, `find_indicators` is not implemented here...
