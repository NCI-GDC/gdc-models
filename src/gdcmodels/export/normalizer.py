from typing import Container, Optional

from typing_extensions import Protocol

import gdcmodels
from gdcmodels import utils


class Normalizer(Protocol):
    """A class which applies normalizers to the appropriate fields withing a mapping."""

    def normalize(self, mapping: gdcmodels.ESMapping) -> gdcmodels.ESMapping:  # type: ignore
        """Set the appropriate normalizer to the mapping.

        Notes:
            Normalizers can only be applied to KEYWORDS and it's assumed that there is a
            singular normalizer for an index.

        Args:
            mapping: The mapping which should be updated with a normalizer.

        """
        pass


DEFAULT_EXCLUDED_PROPERTIES = frozenset(
    (
        "biotype",
        "code",
        "consequence_type",
        "data_type",
        "experimental_strategy",
        "gene_id",
        "name",
        "program",
        "program_name",
        "project",
        "project_code",
        "project_id",
        "project_name",
        "submitter_id",
        "uuid",
        "workflow_type",
    )
)


class DefaultNormalizer(Normalizer):
    """The default normalizer used for all indices."""

    __slots__ = ("_normalizer_name", "_excluded_properties", "_default_mapping")

    def __init__(
        self,
        normalizer_name: str = "clinical_normalizer",
        excluded_properties: Container[str] = DEFAULT_EXCLUDED_PROPERTIES,
        default_mapping: Optional[dict] = None,
    ) -> None:
        self._normalizer_name = normalizer_name
        self._excluded_properties = excluded_properties
        self._default_mapping = default_mapping or {
            "_size": {"enabled": True},
            "_source": {"excludes": ["__comment__"]},
            "dynamic": "strict",
        }

    def normalize(self, mapping: gdcmodels.ESMapping) -> gdcmodels.ESMapping:
        def update(properties: gdcmodels.Properties) -> None:
            for name, property in properties.items():
                if property.get("type") == "keyword" and name not in self._excluded_properties:
                    property["normalizer"] = self._normalizer_name
                elif "properties" in property:
                    update(property["properties"])

        mapping = utils.apply_defaults(mapping, self._default_mapping)

        update(mapping["properties"])

        return mapping


class GraphNormalizer(DefaultNormalizer):
    """Extends the default normalizer with several more excluded properties."""

    def __init__(self) -> None:
        super().__init__(
            excluded_properties=frozenset(
                ("case_submitter_id", "entity_submitter_id", *DEFAULT_EXCLUDED_PROPERTIES)
            )
        )


def normalize(
    mapping: gdcmodels.ESMapping, normalizer: Optional[Normalizer] = None
) -> gdcmodels.ESMapping:
    """
    Normalize the given mapping using the given normalizer.

    Args:
        mapping: The elasticsearch mapping.
        normalizer: The normalizer which will be used to normalize the mapping. If none is
            provided, then the default normalizer will be applied.

    Returns:
        An updated mapping with the normalized properties of the input mapping.
    """
    normalizer = normalizer or DefaultNormalizer()

    return normalizer.normalize(mapping)
