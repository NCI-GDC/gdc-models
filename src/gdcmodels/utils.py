from typing import IO, Any, Union

import yaml


def load_yaml(data: Union[str, bytes, IO[str], IO[bytes]]) -> Any:
    """Load the yaml data provided.

    Args:
        data: a string, bytes, or file from which to extract the yaml data.

    Returns:
        The loaded data.
    """
    return yaml.load(data, Loader=yaml.CSafeLoader)
