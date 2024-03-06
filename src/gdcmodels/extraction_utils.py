import functools
from typing import IO, Any, Dict, Iterable, Mapping, Union

import yaml

load_yaml = functools.partial(yaml.load, Loader=yaml.CSafeLoader)
dump_yaml = functools.partial(yaml.dump, Dumper=yaml.CBaseDumper)


def _expand_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Expand any dot notations in the given settings.

    EXAMPLE:
        {"index.mapping.nested_fields.limit": 100}
        # becomes
        {"index": {"mapping": {"nested_fields": {"limit": 100}}}}

    Args:
        settings: The settings that need to have their keys expanded.

    Returns:
        The expanded settings.
    """
    keys: Iterable[str] = tuple(settings.keys())
    keys = filter(lambda k: "." in k, keys)

    for key in keys:
        parent_key, child = key.split(".", maxsplit=1)
        parent = settings.setdefault(parent_key, {})
        parent[child] = settings.pop(key)

    for key, value in ((k, v) for k, v in settings.items() if isinstance(v, dict)):
        settings[key] = _expand_settings(value)

    return settings


def load_settings(stream: Union[str, bytes, IO[str], IO[bytes]]) -> Mapping[str, Any]:
    """Load the settings contained in the stream.

    NOTE: This will expand any settings which use dot notation in their key values.

    EXAMPLE:
        {"index.mapping.nested_fields.limit": 100}
        # becomes
        {"index": {"mapping": {"nested_fields": {"limit": 100}}}}

    Args:
        stream: The stream containing the yaml formatted settings.

    Returns:
        The expanded settings.
    """
    settings = load_yaml(stream)

    return _expand_settings(settings)
