"""This module tests the behavior of using excludes in elasticsearch mappings"""

import pytest

from tests import models_dsl as m


@pytest.fixture
def inner_gene_doc(es):
    cnv_1 = m.CNV(
        chromosome="chr-1",
        cnv_id="cnv-1",
        observation=[
            m.Observation(
                observation_id="obs-1", src_file_id="file-id-1", variant_status="ok"
            )
        ],
    )
    ca_1 = m.ClinicalAnnotation(civic=[m.Civic(gene_id="g1", variant_id="v1")])
    ssm_1 = m.SSM(chromosome="chr-1", clinical_annotation=[ca_1])

    return m.Gene(
        biotype="XY", gene_id="gene-id-1", symbol="AX", is_cancer_gene_census=True, ssm=[ssm_1], cnv=[cnv_1]
    )


@pytest.fixture
def case_centric_with_gene_excluded(es, inner_gene_doc):
    m.CaseCentricWithGeneExcluded.init(using=es)  # create mappings

    case_centric = m.CaseCentricWithGeneExcluded(
        meta={"id": "case-centric-1"},
        consent_type="doubt",
        case_id="d02309ed-045b-435e-a03b-6c7150cff3b8",
        gene=[inner_gene_doc],
    )

    case_centric.save(using=es, refresh="wait_for", skip_empty=False)


@pytest.fixture
def case_centric_without_deep_nesting(es, inner_gene_doc):
    m.CaseCentricWithoutDeepNesting.init(using=es)  # create mappings

    case_centric = m.CaseCentricWithoutDeepNesting(
        meta={"id": "case-centric-2"},
        consent_type="allowed",
        case_id="820a89d0-7480-4dca-a575-6a6637773134",
        gene=[inner_gene_doc],
    )

    case_centric.save(using=es, refresh="wait_for", skip_empty=False)


@pytest.fixture
def case_centric_with_wildcard(es, inner_gene_doc):
    m.CaseCentricWithWildcard.init(using=es)  # create mappings

    case_centric = m.CaseCentricWithWildcard(
        meta={"id": "case-centric-3"},
        consent_type="allowed",
        case_id="cc067cb8-6862-4520-9553-68222334671c",
        gene=[inner_gene_doc],
    )

    case_centric.save(using=es, refresh="wait_for", skip_empty=False)


@pytest.mark.usefixtures("case_centric_with_gene_excluded")
def test_index__with_excluded_genes(es):
    """Test excluding a nested property behaves as expected"""

    response = m.CaseCentricWithGeneExcluded.search(using=es).filter("term", _id="case-centric-1").execute()

    assert len(response.hits) == 1
    entry = response.hits[0]
    assert entry.meta.id == "case-centric-1"
    assert entry.consent_type == "doubt"
    assert entry.case_id == "d02309ed-045b-435e-a03b-6c7150cff3b8"
    assert entry.gene == [], "gene should be excluded from result"


@pytest.mark.usefixtures("case_centric_without_deep_nesting")
def test_index__without_deep_nesting(es):
    """Test excluding a nested property behaves as expected"""

    response = m.CaseCentricWithoutDeepNesting.search(using=es).filter("term", _id="case-centric-2").execute()

    assert len(response.hits) == 1
    entry = response.hits[0]
    assert entry.meta.id == "case-centric-2"
    assert entry.consent_type == "allowed"
    assert entry.case_id == "820a89d0-7480-4dca-a575-6a6637773134"
    assert entry.gene != [], "gene should some content"

    assert len(entry.gene) == 1
    gene_entry = entry.gene[0]

    assert gene_entry.gene_id == "gene-id-1"
    assert gene_entry.symbol == "AX"

    assert gene_entry.cnv == [], "nested field cnv should be excluded"
    assert gene_entry.ssm == [], "nested field ssm should be excluded"


@pytest.mark.usefixtures("case_centric_with_wildcard")
def test_index__with_wildcard(es):
    """Test excluding a nested property behaves as expected"""

    response = m.CaseCentricWithWildcard.search(using=es).filter("term", _id="case-centric-3").execute()

    assert len(response.hits) == 1
    entry = response.hits[0]
    assert entry.meta.id == "case-centric-3"
    assert entry.case_id == "cc067cb8-6862-4520-9553-68222334671c"
    assert entry.gene != [], "gene should some content"

    assert len(entry.gene) == 1
    gene_entry = entry.gene[0]

    assert gene_entry.gene_id == "gene-id-1"
    assert gene_entry.symbol == "AX"
    assert gene_entry.biotype is None
    assert gene_entry.is_cancer_gene_census is None

    assert gene_entry.cnv == [], "nested field cnv should be excluded"
    assert gene_entry.ssm == [], "nested field ssm should be excluded"
