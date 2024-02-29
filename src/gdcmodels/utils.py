from typing import IO, Any, Mapping, TypeVar, Union, cast

import mergedeep
import yaml


def load_yaml(data: Union[str, bytes, IO[str], IO[bytes]]) -> Any:
    """Load the yaml data provided.

    Args:
        data: a string, bytes, or file from which to extract the yaml data.

    Returns:
        The loaded data.
    """
    return yaml.load(data, Loader=yaml.CSafeLoader)


TMapping = TypeVar("TMapping", bound=Mapping[str, Any])


def apply_defaults(mapping: TMapping, defaults: Mapping[str, object]) -> TMapping:
    """Apply all of the defaulted values to the mapping if the do not exist.

    This creates a new mapping containing all of the data within the given mapping. Any
    values from the defaults which are not found within the mapping are added to this
    new mapping. The defaults are applied in a recursive manor so nested values will be
    applied appropriately.

    Args:
        mapping: the mapping object which should have the defaults applied.
        defaults: the default values which should be used to update the provided
            settings.

    Returns:
        A copy of the data in the mapping with all default values applied.
    """
    return cast(TMapping, mergedeep.merge({}, defaults, mapping))
