"""Elasticsearch DSL models that are a subset of the currently supported gdc-models object.

The aim to produce readable to codes that illustrates object nesting within a document.
"""

from elasticsearch_dsl import Boolean, Document, InnerDoc, Keyword, MetaField, Nested


class Observation(InnerDoc):
    observation_id = Keyword()
    src_file_id = Keyword()
    variant_status = Keyword()


class CNV(InnerDoc):
    chromosome = Keyword()
    cnv_id = Keyword()
    observation = Nested(Observation)


class Civic(InnerDoc):
    gene_id = Keyword()
    variant_id = Keyword()


class ClinicalAnnotation(InnerDoc):
    civic = Nested(Civic)


class SSM(InnerDoc):
    chromosome = Keyword()
    clinical_annotation = Nested(ClinicalAnnotation)


class Gene(InnerDoc):
    biotype = Keyword()
    gene_id = Keyword()
    is_cancer_gene_census = Boolean()
    cnv = Nested(CNV)
    ssm = Nested(SSM)
    symbol = Keyword()


class CaseCentricWithGeneExcluded(Document):
    case_id = Keyword()
    consent_type = Keyword()
    gene = Nested(Gene)

    class Meta:
        """Further customizes the index mapping."""

        dynamic = MetaField("strict")
        source = MetaField({"excludes": ["gene.*"], "enabled": True})
        size = MetaField(enabled=True)

    class Index:
        name = "case_centric__with_gene_excluded"
        settings = {
            "index": {
                "max_result_window": 100000000,
                "mapping": {
                    "nested_fields": {"limit": 100},
                    "nested_objects": {"limit": 100000000},
                },
            }
        }


class CaseCentricWithoutDeepNesting(CaseCentricWithGeneExcluded):
    class Meta:
        dynamic = MetaField("strict")
        source = MetaField({"excludes": ["gene.*.*"], "enabled": True})

    class Index:
        name = "case_centric__without_deep_nesting"


class CaseCentricWithWildcard(CaseCentricWithGeneExcluded):
    class Meta:
        dynamic = MetaField("strict")
        source = MetaField({"excludes": ["gene.*.*", "gene.b*", "gene.*_*_*"], "enabled": True})

    class Index:
        name = "case_centric__with_wildcard"
