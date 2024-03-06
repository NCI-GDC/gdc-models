import functools
from typing import IO, Any, Dict, Iterable, Mapping, Union

import yaml

load_yaml = functools.partial(yaml.load, Loader=yaml.CSafeLoader)
dump_yaml = functools.partial(yaml.dump, Dumper=yaml.CBaseDumper)


def expand_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    keys: Iterable[str] = tuple(settings.keys())
    keys = filter(lambda k: "." in k, keys)

    for key in keys:
        parent_key, child = key.split(".", maxsplit=1)
        parent = settings.setdefault(parent_key, {})
        parent[child] = settings.pop(key)

    for key, value in ((k, v) for k, v in settings.items() if isinstance(v, dict)):
        settings[key] = expand_settings(value)

    return settings


def load_settings(data: Union[str, bytes, IO[str], IO[bytes]]) -> Mapping[str, Any]:
    settings = load_yaml(data)

    return expand_settings(settings)
