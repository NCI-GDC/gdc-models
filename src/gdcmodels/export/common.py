from typing import Any, Container, DefaultDict, Mapping, TypeVar, cast

from typing_extensions import Protocol

import gdcmodels

__all__ = ("NestedDict", "ESProperty", "Exporter")

T = TypeVar("T", bound=Mapping[str, Any])


class NestedDict(DefaultDict[str, Any]):
    """A default dictionary whose values default to a nested instance of itself."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(NestedDict)

        self.update(args)
        self.update(kwargs)

    @staticmethod
    def as_dict(mapping: T) -> T:
        """Make a copy of the given mapping and insures all values are a standard dict.

        Args:
            mapping: The mapping with mixed types of dictionaries.

        Returns:
            A copy of the mapping and any sub-mappings contained all constructed with
            standard dictionaries.
        """
        return cast(
            T,
            {k: NestedDict.as_dict(v) if isinstance(v, dict) else v for k, v in mapping.items()},
        )


class ESProperty:
    """A class for managing standard elasticsearch property values."""

    @classmethod
    def _get_prop(cls, es_type: str) -> NestedDict:
        """Build a property description with the given type.

        Args:
            es_type: The type of the property

        Returns:
            A property description with the given type.
        """
        mapping = NestedDict()
        mapping["type"] = es_type

        return mapping

    @classmethod
    def double(cls) -> NestedDict:
        """Get a double property description."""
        return cls._get_prop("double")

    @classmethod
    def long(cls) -> NestedDict:
        """Get a long property description."""
        return cls._get_prop("long")

    @classmethod
    def string(cls) -> NestedDict:
        """Get a keyword property description."""
        return cls._get_prop("keyword")

    @classmethod
    def translate_python(cls, types: Container[type]) -> NestedDict:
        """Translate the given set up python types to an elasticsearch property.

        Args:
            types: A set of types which represents the python data.

        Returns:
            A float or int property if they are contained in the given types. Otherwise,
            a string property is returned.
        """
        if float in types:
            return cls.double()
        elif int in types:
            return cls.long()
        else:
            return cls.string()


class Exporter(Protocol):
    """A class for exporting a model from some source."""

    def export_mapping(self) -> gdcmodels.ESMapping: ...
