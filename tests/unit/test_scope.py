"""Ticket 013a: scope resolution + residual mapping 테스트."""

from datetime import date

import pytest

from src.assessment.scope import (
    REASON_LAW_VERSION_CONFLICT,
    REASON_MISSING_SCOPE_FACT,
    REASON_RULE_COVERAGE,
    REASON_SOURCE_CONFLICT,
    REASON_UNMAPPED_SCOPE,
    ScopeResolution,
    resolve_scope_from_rows,
    scope_failure_to_residual_type,
)

AS_OF = date(2026, 9, 15)


def sc(scope_id, key, *, coverage="COMPLETE", status="ACTIVE",
       ef=date(2020, 1, 1), et=None):
    return {
        "scope_id": scope_id,
        "scope_key": key,
        "coverage_status": coverage,
        "status": status,
        "effective_from": ef,
        "effective_to": et,
    }


class TestMissingScopeFact:
    def test_none_key(self):
        r = resolve_scope_from_rows(
            scope_key=None, scope_rows=[], as_of=AS_OF
        )
        assert r.resolved is False
        assert r.reason == REASON_MISSING_SCOPE_FACT
        assert r.scope_id is None


class TestUnmappedScope:
    def test_unknown_key(self):
        rows = [sc("s1", "MEDICAL")]
        r = resolve_scope_from_rows(
            scope_key="OFFICE", scope_rows=rows, as_of=AS_OF
        )
        assert r.resolved is False
        assert r.reason == REASON_UNMAPPED_SCOPE
        assert r.scope_key == "OFFICE"
        assert r.scope_id is None


class TestCoverageStatus:
    def test_unverified(self):
        rows = [sc("s1", "MEDICAL", coverage="UNVERIFIED")]
        r = resolve_scope_from_rows(
            scope_key="MEDICAL", scope_rows=rows, as_of=AS_OF
        )
        assert r.resolved is False
        assert r.reason == REASON_RULE_COVERAGE
        assert r.scope_id == "s1"

    def test_partial(self):
        rows = [sc("s1", "MEDICAL", coverage="PARTIAL")]
        r = resolve_scope_from_rows(
            scope_key="MEDICAL", scope_rows=rows, as_of=AS_OF
        )
        assert r.resolved is False
        assert r.reason == REASON_RULE_COVERAGE

    def test_complete(self):
        rows = [sc("s1", "MEDICAL", coverage="COMPLETE")]
        r = resolve_scope_from_rows(
            scope_key="MEDICAL", scope_rows=rows, as_of=AS_OF
        )
        assert r.resolved is True
        assert r.scope_id == "s1"
        assert r.scope_key == "MEDICAL"
        assert r.reason is None


class TestEffectiveWindow:
    def test_future_effective_from(self):
        rows = [sc("s1", "MEDICAL", ef=date(2027, 1, 1))]
        r = resolve_scope_from_rows(
            scope_key="MEDICAL", scope_rows=rows, as_of=AS_OF
        )
        assert r.resolved is False
        assert r.reason == REASON_LAW_VERSION_CONFLICT

    def test_expired_effective_to(self):
        rows = [sc("s1", "MEDICAL",
                   ef=date(2020, 1, 1), et=date(2025, 1, 1))]
        r = resolve_scope_from_rows(
            scope_key="MEDICAL", scope_rows=rows, as_of=AS_OF
        )
        assert r.resolved is False
        assert r.reason == REASON_LAW_VERSION_CONFLICT

    def test_effective_to_exactly_as_of_is_expired(self):
        # effective_to 는 exclusive (as_of < effective_to)
        rows = [sc("s1", "MEDICAL",
                   ef=date(2020, 1, 1), et=AS_OF)]
        r = resolve_scope_from_rows(
            scope_key="MEDICAL", scope_rows=rows, as_of=AS_OF
        )
        assert r.resolved is False
        assert r.reason == REASON_LAW_VERSION_CONFLICT


class TestDeprecated:
    def test_deprecated_scope(self):
        rows = [sc("s1", "MEDICAL", status="DEPRECATED")]
        r = resolve_scope_from_rows(
            scope_key="MEDICAL", scope_rows=rows, as_of=AS_OF
        )
        assert r.resolved is False
        assert r.reason == REASON_LAW_VERSION_CONFLICT


class TestCompleteIndependenceFromRuleCount:
    def test_complete_scope_no_rules_resolved_true(self):
        # COMPLETE scope 라면 rule row 가 0개여도 resolved=True.
        # coverage 완전성은 scope.coverage_status 로 판단한다.
        rows = [sc("s1", "MEDICAL", coverage="COMPLETE")]
        r = resolve_scope_from_rows(
            scope_key="MEDICAL", scope_rows=rows, as_of=AS_OF
        )
        assert r.resolved is True

    def test_complete_scope_with_multiple_versions(self):
        rows = [
            sc("s_old", "MEDICAL", coverage="COMPLETE",
               ef=date(2015, 1, 1), et=date(2020, 1, 1)),
            sc("s_new", "MEDICAL", coverage="COMPLETE",
               ef=date(2020, 1, 1)),
        ]
        r = resolve_scope_from_rows(
            scope_key="MEDICAL", scope_rows=rows, as_of=AS_OF
        )
        assert r.resolved is True
        assert r.scope_id == "s_new"  # latest effective_from


class TestResidualMapping:
    def test_none_reason_returns_none(self):
        assert scope_failure_to_residual_type(None) is None

    def test_missing_scope_fact(self):
        assert scope_failure_to_residual_type(
            REASON_MISSING_SCOPE_FACT
        ) == "MISSING_FACT"

    def test_unmapped_scope(self):
        assert scope_failure_to_residual_type(
            REASON_UNMAPPED_SCOPE
        ) == "UNMAPPED_SOURCE_TYPE"

    def test_rule_coverage(self):
        assert scope_failure_to_residual_type(
            REASON_RULE_COVERAGE
        ) == "RULE_COVERAGE"

    def test_source_conflict(self):
        assert scope_failure_to_residual_type(
            REASON_SOURCE_CONFLICT
        ) == "SOURCE_CONFLICT"

    def test_law_version_conflict(self):
        assert scope_failure_to_residual_type(
            REASON_LAW_VERSION_CONFLICT
        ) == "LAW_VERSION_CONFLICT"

    def test_unknown_reason_returns_none(self):
        assert scope_failure_to_residual_type("WHATEVER") is None


class TestDataclassFrozen:
    def test_immutable(self):
        r = ScopeResolution(True, "s1", "MEDICAL", None)
        with pytest.raises(Exception):
            r.resolved = False  # type: ignore