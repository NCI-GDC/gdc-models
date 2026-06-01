"""A set of constants for use throughout the gdcmodels library."""

import enum
from collections.abc import Set
from importlib import abc, resources

from backports import strenum

MAPPING_FILE = "mapping.yaml"
"""The name of the mapping file in the directory for a model."""
VESTIGIAL_FILE = "vestigial.yaml"
"""The name of the vestigial file in the directory for a model."""
GRAPH_UNNORMALIZED_PROPERTIES = frozenset(
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
"""A set of properties which should NOT be normalized in the graph mappings."""
VIZ_UNNORMALIZED_PROPERTIES = frozenset(
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
"""A set of properties which should NOT be normalized in the viz mappings."""
GRAPH_NAMESPACE = "gdc_from_graph"
"""The namespace of the graph models from when the indices were formerly driven on doc_type."""


class Index(strenum.StrEnum):
    """The various indices represented in the models."""

    # GRAPH
    ANNOTATION = enum.auto()
    CASE = enum.auto()
    FILE = enum.auto()
    PROJECT = enum.auto()

    # VIZ
    CASE_CENTRIC = enum.auto()
    CNV_CENTRIC = enum.auto()
    CNV_OCCURRENCE_CENTRIC = enum.auto()
    GENE_CENTRIC = enum.auto()
    SEGMENT_CNV_CENTRIC = enum.auto()
    SEGMENT_CNV_OCCURRENCE_CENTRIC = enum.auto()
    SSM_CENTRIC = enum.auto()
    SSM_OCCURRENCE_CENTRIC = enum.auto()

    @property
    def components(self) -> tuple[str, str]:
        """The index name & doc type associated with his index."""
        if self in GRAPH_INDICES:
            return GRAPH_NAMESPACE, self

        return self, self

    @property
    def index_group(self) -> str:
        """The index group name (graph/viz) associated with this index."""
        if self in GRAPH_INDICES:
            return "graph"
        if self in VIZ_INDICES:
            return "viz"

        raise ValueError(f"Unknown grouping for index: {self}.")

    @property
    def models_dir(self) -> abc.Traversable:
        """The directory in the models where the files associated with an index are stored."""
        base = resources.files("gdcmodels.esmodels")

        if self in GRAPH_INDICES:
            return base / GRAPH_NAMESPACE / self

        return base / self

    @property
    def unnormalized_properties(self) -> Set[str]:
        """The set of unnormalized properties which are associated with this index."""
        if self in GRAPH_INDICES:
            return GRAPH_UNNORMALIZED_PROPERTIES
        elif self in VIZ_INDICES:
            return VIZ_UNNORMALIZED_PROPERTIES

        return frozenset()

    def overlay_file(self, overlay: str) -> abc.Traversable:
        """Gets the resource representing the overlay file for this index.

        NOTE: This is only applicable for overlay groups which are based on yaml files.

        Args:
            overlay: The name of the overlay whose specific mapping file needs to be loaded.

        Returns:
            The yaml file resource for the given overlay which represents this index's
            mapping.
        """
        base = resources.files("gdcmodels.sync.overlays")

        return base / overlay / self.index_group / f"{self}.yaml"


GRAPH_INDICES = frozenset({Index.ANNOTATION, Index.CASE, Index.FILE, Index.PROJECT})
"""The set of indices which represent the Graph indices group."""
VIZ_INDICES = frozenset(
    {
        Index.CASE_CENTRIC,
        Index.CNV_CENTRIC,
        Index.CNV_OCCURRENCE_CENTRIC,
        Index.GENE_CENTRIC,
        Index.SEGMENT_CNV_CENTRIC,
        Index.SEGMENT_CNV_OCCURRENCE_CENTRIC,
        Index.SSM_CENTRIC,
        Index.SSM_OCCURRENCE_CENTRIC,
    }
)
"""The set of indices which represent the Viz indices group."""
