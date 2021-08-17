import warnings


class MasterDataEntity:
    """Common base class for Masterdata entities."""

    _field_map = {}

    @classmethod
    def get_available_properties(cls):
        """Return the available Assetcentral properties for this class."""
        return set([field.our_name for field in cls._field_map.values() if field.is_exposed])

    @classmethod
    def get_property_mapping(cls):
        """Return a mapping from assetcentral terminology to our terminology.

        .. deprecated:: 1.4.0
        Use :meth:`get_available_properties` instead.
        """
        # TODO: remove method in future version
        msg = ("'get_property_mapping': deprecated. Method will be removed after September 01, 2021. " +
               "use 'get_available_properties' instead")
        warnings.warn(msg, FutureWarning)
        return {field.our_name: (field.their_name_get, None, None, None) for field in cls._field_map.values()
                if field.is_exposed}

    def __init__(self, ac_json: dict):
        """Create a new entity."""
        self.raw = ac_json

    @property
    def id(self):
        """Return the ID of the object."""
        return self.raw.get('id')

    def __repr__(self) -> str:
        """Return a very short string representation."""
        name = getattr(self, 'name', getattr(self, 'short_description', None))
        return f'"{self.__class__.__name__}(name="{name}", id="{self.id}")'

    def __eq__(self, obj):
        """Compare two objects based on instance type and id."""
        return isinstance(obj, self.__class__) and obj.id == self.id

    def __hash__(self):
        """Hash of an asset central object is the hash of it's id."""
        return self.id.__hash__()


class MasterDataField:
    """Common base class for all masterdata fields."""

    def __init__(self, our_name, their_name_get, their_name_put=None, is_mandatory=False,
                 get_extractor=None, put_setter=None):
        self.our_name = our_name
        self.their_name_get = their_name_get
        self.their_name_put = their_name_put
        self.is_exposed = not our_name.startswith('_')
        self.is_writable = their_name_put is not None
        self.is_mandatory = is_mandatory

        self.names = (our_name, their_name_get, their_name_put)

        self.get_extractor = get_extractor or self._default_get_extractor
        self.put_setter = put_setter or self._default_put_setter

    def _default_put_setter(self, payload, value):
        payload[self.their_name_put] = value
        return

    def _default_get_extractor(self, value):
        return value


def add_properties(cls):
    """Add properties to the entity class based on the field template defined by the request mapper."""
    for field in cls._field_map.values():

        # the assignment of the default value (`field=field`)
        # is necessary due to the closure rules in loops
        def getter(self, field=field):
            return field.get_extractor(self.raw.get(field.their_name_get))

        setattr(cls, field.our_name, property(getter, None, None))
    return cls
