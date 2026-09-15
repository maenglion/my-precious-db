"""engine 유닛 테스트 (fake conn, DB 없이)."""

from datetime import date

from src.assessment.engine import (
    evaluate_rule,
    load_facts,
    load_rules_for_scope,
    run_assessment,
)
from src.assessment.loader import LoadedRule, rows_to_tree
from src.assessment.logic import TruthValue
from src.assessment.verdict import Verdict

T = TruthValue.TRUE
F = TruthValue.FALSE
U = TruthValue.UNKNOWN

AS_OF = date(2026, 9, 15)


class FakeCursor:
    def __init__(self, mapping):
        self._mapping = mapping
        self._rows = []
        self._last = None

    def __enter__(self): return self
    def __exit__(self, *a): pass

    def execute(self, sql, params=None):
        self._last = (" ".join(sql.split()).lower(), params or ())
        key = self._key(*self._last)
        self._rows = list(self._mapping.get(key, []))

    def fetchall(self): return self._rows
    def fetchone(self): return self._rows[0] if self._rows else None

    def _key(self, sql, params):
        if "from core.facility_fact" in sql and "fact_key = " in sql:
            return ("scope_fact", str(params[0]))
        if "from core.facility_fact" in sql:
            return ("facts", str(params[0]))
        if "from rule.scope" in sql:
            return ("scope", str(params[0]))
        if "from rule.rule" in sql:
            return ("rules", str(params[0]))
        if "from rule.expression" in sql:
            return ("exprs", str(params[0]))
        return ("?",)


class FakeConn:
    def __init__(self, mapping):
        self._mapping = mapping
        self._cur = FakeCursor(mapping)

    def cursor(self): return self._cur
    def commit(self): pass


def make_facts(*triples):
    return [
        {"fact_id": fid, "fact_key": k, "value_json": v}
        for fid, k, v in triples
    ]


def rule_row(rule_id, name, effect, *, scope_id="s1",
             priority=100, source_node_id="n1"):
    return {
        "rule_id": rule_id, "name": name, "effect": effect,
        "priority": priority, "source_node_id": source_node_id,
        "scope_id": scope_id,
    }


def expr_row(expr_id, rule_id, parent, expr_type, *,
             fact_key=None, operator=None, compare_value=None, sort_order=0):
    return {
        "expr_id": expr_id, "rule_id": rule_id, "parent_expr_id": parent,
        "expr_type": expr_type, "bool_op": None,
        "fact_key": fact_key, "operator": operator,
        "compare_value": compare_value, "unit": None,
        "sort_order": sort_order,
    }


def scope_row(scope_id, key, *, coverage="COMPLETE", status="ACTIVE",
              ef=date(2020, 1, 1), et=None):
    return {
        "scope_id": scope_id, "scope_key": key,
        "coverage_status": coverage, "status": status,
        "effective_from": ef, "effective_to": et,
    }


class TestLoadFacts:
    def test_loads_and_unwraps_value(self):
        conn = FakeConn({("facts", "fac1"): make_facts(
            ("f1", "area", 3500),
            ("f2", "use_type", "OFFICE"),
        )})
        facts, ids = load_facts(conn, "fac1", AS_OF)
        assert facts == {"area": 3500, "use_type": "OFFICE"}
        assert ids == {"area": "f1", "use_type": "f2"}


class TestLoadRules:
    def test_loads_tree(self):
        conn = FakeConn({
            ("rules", "s1"): [rule_row("r1", "office_include", "INCLUDE")],
            ("exprs", "r1"): [
                expr_row("e1", "r1", None, "PREDICATE",
                         fact_key="area", operator=">=", compare_value=3000),
            ],
        })
        rules = load_rules_for_scope(conn, "s1", AS_OF)
        assert len(rules) == 1
        assert rules[0].rule_id == "r1"
        assert rules[0].effect == "INCLUDE"


class TestEvaluateRule:
    def test_include_true_with_fact_id(self):
        rows = [expr_row("e1", "r1", None, "PREDICATE",
                         fact_key="area", operator=">=", compare_value=3000)]
        rule = LoadedRule(
            rule_id="r1", name="office_include", effect="INCLUDE",
            priority=100, source_node_id="n1", root=rows_to_tree(rows),
        )
        rec = evaluate_rule(rule, {"area": 3500}, {"area": "f1"})
        assert rec.result is T
        assert rec.predicate_evals[0].fact_id == "f1"
        assert rec.predicate_evals[0].reason is None


class TestRunAssessment:
    def _scope_complete(self):
        return scope_row("s1", "OFFICE")

    def _scope_fact(self, key="OFFICE"):
        return [{"fact_id": "sf1", "value_json": key,
                 "effective_from": None, "effective_to": None}]

    def test_t01_general_office_applicable(self):
        conn = FakeConn({
            ("scope_fact", "fac1"): self._scope_fact("OFFICE"),
            ("scope", "OFFICE"): [self._scope_complete()],
            ("facts", "fac1"): make_facts(("f_area", "area", 3500)),
            ("rules", "s1"): [rule_row("r1", "office_include", "INCLUDE")],
            ("exprs", "r1"): [
                expr_row("e1", "r1", None, "PREDICATE",
                         fact_key="area", operator=">=", compare_value=3000),
            ],
        })
        out = run_assessment(conn, "fac1", AS_OF, persist=False)
        assert out.verdict is Verdict.APPLICABLE
        assert out.matched_rule_id == "r1"
        assert out.scope.resolved is True

    def test_t03_area_below_not_applicable(self):
        conn = FakeConn({
            ("scope_fact", "fac1"): self._scope_fact("OFFICE"),
            ("scope", "OFFICE"): [self._scope_complete()],
            ("facts", "fac1"): make_facts(("f_area", "area", 2000)),
            ("rules", "s1"): [rule_row("r1", "office_include", "INCLUDE")],
            ("exprs", "r1"): [
                expr_row("e1", "r1", None, "PREDICATE",
                         fact_key="area", operator=">=", compare_value=3000),
            ],
        })
        out = run_assessment(conn, "fac1", AS_OF, persist=False)
        assert out.verdict is Verdict.NOT_APPLICABLE

    def test_t07_medical_unknown(self):
        conn = FakeConn({
            ("scope_fact", "fac1"): self._scope_fact("MEDICAL"),
            ("scope", "MEDICAL"): [self._scope_complete()],
            ("facts", "fac1"): make_facts(("f_area", "area", 1000)),
            ("rules", "s1"): [rule_row("r1", "medical_include", "INCLUDE")],
            ("exprs", "r1"): [
                expr_row("e1", "r1", None, "OR"),
                expr_row("e2", "r1", "e1", "PREDICATE",
                         fact_key="area", operator=">=", compare_value=2000, sort_order=0),
                expr_row("e3", "r1", "e1", "PREDICATE",
                         fact_key="beds", operator=">=", compare_value=100, sort_order=1),
            ],
        })
        out = run_assessment(conn, "fac1", AS_OF, persist=False)
        assert out.verdict is Verdict.INDETERMINATE

    def test_scope_unresolved_no_rules(self):
        conn = FakeConn({
            ("scope_fact", "fac1"): [],
            ("facts", "fac1"): [],
        })
        out = run_assessment(conn, "fac1", AS_OF, persist=False)
        assert out.verdict is Verdict.INDETERMINATE
        assert out.scope.resolved is False
        assert out.scope.reason == "MISSING_SCOPE_FACT"
        assert out.rule_evals == []

    def test_scope_partial_coverage_indeterminate(self):
        conn = FakeConn({
            ("scope_fact", "fac1"): self._scope_fact("OFFICE"),
            ("scope", "OFFICE"): [
                scope_row("s1", "OFFICE", coverage="PARTIAL")
            ],
            ("facts", "fac1"): [],
        })
        out = run_assessment(conn, "fac1", AS_OF, persist=False)
        assert out.verdict is Verdict.INDETERMINATE
        assert out.scope.reason == "RULE_COVERAGE"

    def test_scope_complete_no_rules_not_applicable(self):
        conn = FakeConn({
            ("scope_fact", "fac1"): self._scope_fact("OFFICE"),
            ("scope", "OFFICE"): [self._scope_complete()],
            ("facts", "fac1"): [],
            ("rules", "s1"): [],
        })
        out = run_assessment(conn, "fac1", AS_OF, persist=False)
        assert out.verdict is Verdict.NOT_APPLICABLE
        assert out.scope.resolved is True