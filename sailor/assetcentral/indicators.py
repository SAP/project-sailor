"""
Indicators module can be used to retrieve Indicator information from AssetCentral.

Classes are provided for individual Indicators as well as groups of indicators (IndicatorSet).
Note that the indicators here represent 'materialized' indicators, i.e. indicators attached to an equipment.
Hence they contain information on indicator_group and template used to attach it to the equipment. Currently there
is no support for unrealized 'Indicator Templates'.
"""

from .utils import add_properties, AssetcentralEntity, ResultSet


@add_properties
class Indicator(AssetcentralEntity):
    """
    AssetCentral Indicator Object.

    Properties (in AC terminology) are: categoryID, propertyId, indicatorGroupName, indicatorName,
    indicatorGroupDesc, objectId, indicatorSource, aggUpdatedTimestamp, indicatorCategory, colorCode,
    thresholdDescription, convertedAggregatedValue, trend, dataType, indicatorType, convertedUOMDesc,
    UOM, convertedUOM, indicatorDesc, indicatorColorCode, isFavorite, UOMDescription, Dimension, DimensionDesc,
    uomdescription, dimension, dimensionDesc, pstid, uom
    """  # TODO update field list - I think e.g. template id is also part of hte API response

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

    def __eq__(self, other):
        """Determine whether two (materialized) indicator instances are equal."""
        return (super().__eq__(other) and
                other.indicator_group_id == self.indicator_group_id and other.template_id == self.template_id)


class IndicatorSet(ResultSet):
    """Class representing a group of indicators."""

    _element_name = 'Indicator'
    _set_name = 'IndicatorSet'
    _method_defaults = {
        'plot_distribution': {
            'by': 'group_name',
        },
        'as_df': {
            'properties': Indicator.get_property_mapping().keys()
        }
    }


# while there is a generic '/services/api/v1/indicators' endpoint that allows to find indicators,
# that endpoint returns a very different object from the one that you can find via the equipment.
# it only has properties 'id', 'dataType', 'description' and 'internalId', which makes it incompatible
# with property mapping above. Therefore, `find_indicators` is not implemented here...
