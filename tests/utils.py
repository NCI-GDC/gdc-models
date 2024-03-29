import pathlib
from typing import Optional

import yaml


def load_model(
    models: pathlib.Path,
    index_name: str,
    mapping: dict,
    settings: Optional[dict] = None,
    doc_type: Optional[str] = None,
    descriptions: Optional[dict] = None,
    vestigial: Optional[dict] = None,
) -> None:
    """A util for loading an index/doc_type into the given models directory.

    Args:
        models: The directory containing all models.
        index_name: The name of the index to be created.
        mapping: The mappings to be associated with the doc_type.
        settings: The settings to be associated with the index.
        doc_type: The name of the doc_type within the index. By default this value is
            set to index_name if no value is provided.
        description: The descriptions associated with the index.
        vestigial: The vestigial properties associated with the doc_type mapping.
    """
    index_dir = models / index_name
    doc_type_dir = index_dir / doc_type if doc_type else index_dir

    doc_type_dir.mkdir(parents=True, exist_ok=True)

    with open(doc_type_dir / "mapping.yaml", "w+") as f:
        yaml.safe_dump(mapping, f)

    with open(doc_type_dir / "vestigial.yaml", "w+") as f:
        yaml.safe_dump(vestigial or {}, f)

    if settings:
        with open(index_dir / "settings.yaml", "w+") as f:
            yaml.safe_dump(settings, f)

    if descriptions is not None:
        with open(index_dir / "descriptions.yaml", "w+") as f:
            yaml.safe_dump(descriptions, f)
