"""The common functionality for syncing indices."""

import functools
import sys
from typing import Any, Container, Dict, Iterable, Mapping, Optional, Tuple, TypeVar, cast

import mergedeep
from typing_extensions import Protocol

import gdcmodels
from gdcmodels import common, esmodels, extraction_utils, mapper

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources


Export = Tuple[esmodels.ESMapping, Mapping[str, Any]]
TMapping = TypeVar("TMapping", bound=Mapping[str, Any])


@functools.lru_cache(None)
def load_models() -> Mapping[str, Mapping[str, mapper.ModelMapper]]:
    """Call get_es_models and manage cache of the results.

    Returns:
        The loaded models.
    """
    return gdcmodels.get_es_models(vestigial_included=True)


def apply_defaults(mapping: TMapping, *defaults: Mapping[str, object]) -> TMapping:
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
    return cast(TMapping, mergedeep.merge({}, *defaults, mapping))


class Synchronizer(Protocol):
    def sync(self, mappings: esmodels.ESMapping, settings: Mapping[str, Any]) -> Export:
        """Synchronize the data in the models w/ external and default values.

        Args:
            mappings: The mappings associated with the model.
            settings: The settings associated with the model.

        Returns:
            An updated mappings/settings to update the existing data with.
        """
        ...


class CompositeSynchronizer(Synchronizer):
    """A synchronizer which chains several sub-sync commands together."""

    def __init__(self, synchronizers: Iterable[Synchronizer]) -> None:
        self._synchronizers = synchronizers

    def sync(self, mappings: esmodels.ESMapping, settings: Mapping[str, Any]) -> Export:
        return functools.reduce(
            lambda args, e: e.sync(*args), self._synchronizers, (mappings, settings)
        )


class DefaultSettingsSynchronizer(Synchronizer):
    """A synchronizer which sets the default settings values for the graph/viz indices."""

    def __init__(self) -> None:
        self._default_settings: Optional[Mapping[str, Any]] = None

    @property
    def default_settings(self) -> Mapping[str, Any]:
        if not self._default_settings:
            settings_file = resources.files(common) / "settings.yaml"

            self._default_settings = cast(
                Mapping[str, Any], extraction_utils.load_settings(settings_file.read_bytes())
            )

        return self._default_settings

    def sync(self, mappings: esmodels.ESMapping, settings: Mapping[str, Any]) -> Export:
        return mappings, apply_defaults(settings, self.default_settings)


class DefaultMappingsSynchronizer(Synchronizer):
    """A synchronizer which sets the default mapping values for the viz/graph indices."""

    def __init__(self) -> None:
        self._default_mappings: Optional[Mapping[str, Any]] = None

    @property
    def default_mappings(self) -> Mapping[str, Any]:
        if not self._default_mappings:
            settings_file = resources.files(common) / "mapping.yaml"

            self._default_mappings = cast(
                Mapping[str, Any], extraction_utils.load_yaml(settings_file.read_bytes())
            )

        return self._default_mappings

    def sync(self, mappings: esmodels.ESMapping, settings: Mapping[str, Any]) -> Export:
        return apply_defaults(mappings, self.default_mappings), settings


class DefaultNormalizerSynchronizer(Synchronizer):
    """A synchronizer which adds the clinical normalizer to keyword properties."""

    DEFAULT_EXCLUDED_PROPERTIES = frozenset(
        (
            "biotype",
            "case_submitter_id",
            "code",
            "consequence_type",
            "data_type",
            "entity_submitter_id",
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

    def __init__(
        self,
        normalizer_name: str = "clinical_normalizer",
        excluded_properties: Container[str] = DEFAULT_EXCLUDED_PROPERTIES,
    ) -> None:
        self._normalizer_name = normalizer_name
        self._excluded_properties = excluded_properties

    def _build_normalized_tree(self, mapping: esmodels.ESMapping) -> Mapping[str, Any]:
        def get_paths(
            properties: esmodels.Properties, path: Iterable[str] = ()
        ) -> Iterable[Iterable[str]]:
            for name, property in properties.items():
                sub_path = (*path, name)

                if property.get("type") == "keyword" and name not in self._excluded_properties:
                    yield sub_path
                elif "properties" in property:
                    yield from get_paths(property["properties"], sub_path)

        def get_property(mapping: dict, property: str) -> dict:
            return mapping.setdefault("properties", {}).setdefault(property, {})

        normalizer_paths = get_paths(mapping["properties"])
        tree: Dict[str, Any] = {}

        for path in normalizer_paths:
            property: dict = functools.reduce(get_property, path, tree)
            property["normalizer"] = self._normalizer_name

        return tree

    def sync(self, mapping: esmodels.ESMapping, settings: Mapping[str, Any]) -> Export:
        normalized_tree = self._build_normalized_tree(mapping)

        return apply_defaults(mapping, normalized_tree), settings
