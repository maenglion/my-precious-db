"""013N: branch 분류 (DL-013)."""

from src.review.branch import classify_branch, BRANCH_MAP, VALID_BRANCHES


def test_repair_types():
    for t in [
        "PARSER",
        "MISSING_FACT",
        "SOURCE_CONFLICT",
        "IDENTITY",
        "LAW_VERSION_CONFLICT",
    ]:
        assert classify_branch(t) == "REPAIR", t


def test_rule_coverage_maps_to_rule():
    assert classify_branch("RULE_COVERAGE") == "RULE"


def test_unmapped_source_type_maps_to_ontology():
    assert classify_branch("UNMAPPED_SOURCE_TYPE") == "ONTOLOGY"


def test_unknown_type_returns_none():
    assert classify_branch("BOGUS_TYPE") is None
    assert classify_branch("") is None


def test_all_mapped_branches_are_valid():
    for residual_type, branch in BRANCH_MAP.items():
        assert branch in VALID_BRANCHES, (residual_type, branch)