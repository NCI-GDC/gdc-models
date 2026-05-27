import enum
from collections.abc import Set
from importlib import abc, resources

from backports import strenum

MAPPINGS_FILE = "mapping.yaml"
VESTIGIAL_FILE = "vestigial.yaml"
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


class Index(strenum.StrEnum):
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
        if self in GRAPH_INDICES:
            return "gdc_from_graph", self

        return self, self

    @property
    def namespace(self) -> str:
        if self in GRAPH_INDICES:
            return "graph"
        if self in VIZ_INDICES:
            return "viz"

        raise ValueError(f"Unknown namespace for index: {self}.")

    @property
    def models_dir(self) -> abc.Traversable:
        base = resources.files("gdcmodels.esmodels")

        if self in GRAPH_INDICES:
            return base / "gdc_from_graph" / self

        return base / self

    @property
    def unnormalized_properties(self) -> Set[str]:
        if self in GRAPH_INDICES:
            return GRAPH_UNNORMALIZED_PROPERTIES
        elif self in VIZ_INDICES:
            return VIZ_UNNORMALIZED_PROPERTIES

        return frozenset()

    def overlay_file(self, overlay: str) -> abc.Traversable:
        base = resources.files("gdcmodels.sync.overlays")

        return base / overlay / self.namespace / f"{self}.yaml"


GRAPH_INDICES = frozenset({Index.ANNOTATION, Index.CASE, Index.FILE, Index.PROJECT})
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
