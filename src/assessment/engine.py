"""Assessment Engine (Ticket 013b).

v0.2 10장 4-state + 12.1 coverage guard를 실제 DB에서 수행.

흐름:
    facility_id
    -> load_facts
    -> load_scope_resolution (Ticket 013a)
    -> load rules (scope_id 기반)
    -> evaluate each rule (expression tree + trace)
    -> final_verdict(candidate_scope_resolved=scope.resolved)
    -> INSERT assessment + rule_evaluation + predicate_evaluation
    -> (resolved=False) residual_item INSERT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import psycopg
from psycopg.types.json import Jsonb 

from src.assessment.expression import Node, evaluate_tree_with_trace
from src.assessment.loader import LoadedRule, rows_to_tree
from src.assessment.logic import TruthValue
from src.assessment.scope import (
    ScopeResolution,
    load_scope_resolution,
    scope_failure_to_residual_type,
)
from src.assessment.verdict import RuleResult, Verdict, final_verdict

ENGINE_VERSION = "0.2.0"


@dataclass
class PredicateEvalRecord:
    expr_id: str | None
    fact_id: str | None
    actual_value: Any
    expected_value: Any
    operator: str
    result: TruthValue
    reason: str | None


@dataclass
class RuleEvalRecord:
    rule: LoadedRule
    result: TruthValue
    predicate_evals: list[PredicateEvalRecord] = field(default_factory=list)


@dataclass
class AssessmentOutcome:
    verdict: Verdict
    rule_evals: list[RuleEvalRecord]
    matched_rule_id: str | None
    scope: ScopeResolution
    assessment_id: str | None = None
    residual_id: str | None = None


def load_facts(
    conn: psycopg.Connection,
    facility_id: str,
    as_of: date,
) -> tuple[dict[str, Any], dict[str, str]]:
    sql = """
        SELECT fact_id, fact_key, value_json
        FROM core.facility_fact
        WHERE facility_id = %s
          AND (effective_from IS NULL OR effective_from <= %s)
          AND (effective_to IS NULL OR effective_to > %s)
        ORDER BY created_at DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (facility_id, as_of, as_of))
        rows = cur.fetchall()

    facts: dict[str, Any] = {}
    fact_ids: dict[str, str] = {}
    for row in rows:
        key = row["fact_key"]
        if key not in facts:
            v = row["value_json"]
            if isinstance(v, dict) and "value" in v:
                v = v["value"]
            facts[key] = v
            fact_ids[key] = str(row["fact_id"])
    return facts, fact_ids


def load_rules_for_scope(
    conn: psycopg.Connection,
    scope_id: str,
    as_of: date,
) -> list[LoadedRule]:
    rule_sql = """
        SELECT rule_id, name, effect, priority, source_node_id
        FROM rule.rule
        WHERE scope_id = %s
          AND status = 'ACTIVE'
          AND effective_from <= %s
          AND (effective_to IS NULL OR effective_to > %s)
        ORDER BY priority, name
    """
    expr_sql = """
        SELECT expr_id, parent_expr_id, expr_type, bool_op,
               fact_key, operator, compare_value, unit, sort_order
        FROM rule.expression
        WHERE rule_id = %s
        ORDER BY sort_order
    """
    loaded: list[LoadedRule] = []
    with conn.cursor() as cur:
        cur.execute(rule_sql, (scope_id, as_of, as_of))
        rule_rows = cur.fetchall()
        for r in rule_rows:
            cur.execute(expr_sql, (r["rule_id"],))
            expr_rows = cur.fetchall()
            if not expr_rows:
                continue
            tree = rows_to_tree(expr_rows)
            loaded.append(LoadedRule(
                rule_id=str(r["rule_id"]),
                name=r["name"],
                effect=r["effect"],
                priority=r["priority"],
                source_node_id=str(r["source_node_id"]),
                root=tree,
            ))
    return loaded


def evaluate_rule(
    rule: LoadedRule,
    facts: dict[str, Any],
    fact_ids: dict[str, str],
) -> RuleEvalRecord:
    result, traces = evaluate_tree_with_trace(rule.root, facts)
    pred_evals: list[PredicateEvalRecord] = []
    for t in traces:
        pred_evals.append(PredicateEvalRecord(
            expr_id=t.expr_id,
            fact_id=fact_ids.get(t.fact_key),
            actual_value=t.actual_value,
            expected_value=t.expected_value,
            operator=t.operator,
            result=t.result,
            reason=t.reason,
        ))
    return RuleEvalRecord(rule=rule, result=result, predicate_evals=pred_evals)


def run_assessment(
    conn: psycopg.Connection,
    facility_id: str,
    as_of: date,
    *,
    persist: bool = True,
) -> AssessmentOutcome:
    facts, fact_ids = load_facts(conn, facility_id, as_of)
    scope = load_scope_resolution(conn, facility_id, as_of)

    if not scope.resolved:
        outcome = AssessmentOutcome(
            verdict=Verdict.INDETERMINATE,
            rule_evals=[],
            matched_rule_id=None,
            scope=scope,
        )
        if persist:
            _persist_assessment(conn, facility_id, as_of, outcome)
            _persist_residual(conn, facility_id, outcome)
        return outcome

    rules = load_rules_for_scope(conn, scope.scope_id, as_of)  # type: ignore[arg-type]
    rule_evals = [evaluate_rule(r, facts, fact_ids) for r in rules]

    verdict = final_verdict(
        [RuleResult(rule_id=re.rule.rule_id,
                    name=re.rule.name,
                    effect=re.rule.effect,
                    result=re.result)
         for re in rule_evals],
        candidate_scope_resolved=True,
    )

    matched_rule_id = None
    if verdict is Verdict.EXCLUDED:
        for re in rule_evals:
            if re.rule.effect == "EXCLUDE" and re.result is TruthValue.TRUE:
                matched_rule_id = re.rule.rule_id
                break
    elif verdict is Verdict.APPLICABLE:
        for re in rule_evals:
            if re.rule.effect == "INCLUDE" and re.result is TruthValue.TRUE:
                matched_rule_id = re.rule.rule_id
                break

    outcome = AssessmentOutcome(
        verdict=verdict,
        rule_evals=rule_evals,
        matched_rule_id=matched_rule_id,
        scope=scope,
    )

    if persist:
        _persist_assessment(conn, facility_id, as_of, outcome)

    return outcome


def _persist_assessment(
    conn: psycopg.Connection,
    facility_id: str,
    as_of: date,
    outcome: AssessmentOutcome,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO assess.assessment
                (facility_id, as_of, result, matched_rule_id, engine_version)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING assessment_id
            """,
            (facility_id, as_of, outcome.verdict.value,
             outcome.matched_rule_id, ENGINE_VERSION),
        )
        assessment_id = str(cur.fetchone()["assessment_id"])
        outcome.assessment_id = assessment_id

        for re in outcome.rule_evals:
            cur.execute(
                """
                INSERT INTO assess.rule_evaluation
                    (assessment_id, rule_id, result)
                VALUES (%s, %s, %s)
                RETURNING rule_eval_id
                """,
                (assessment_id, re.rule.rule_id, re.result.value),
            )
            rule_eval_id = str(cur.fetchone()["rule_eval_id"])

            for pe in re.predicate_evals:
                cur.execute(
                    """
                    INSERT INTO assess.predicate_evaluation
                        (rule_eval_id, expr_id, fact_id,
                         actual_value, expected_value, operator,
                         result, reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (rule_eval_id,
                     pe.expr_id,
                     pe.fact_id,
                     Jsonb(pe.actual_value),
                     Jsonb(pe.expected_value),
                     pe.operator,
                     pe.result.value,
                     pe.reason),
                )
    conn.commit()


def _persist_residual(
    conn: psycopg.Connection,
    facility_id: str,
    outcome: AssessmentOutcome,
) -> None:
    residual_type = scope_failure_to_residual_type(outcome.scope.reason)
    if residual_type is None:
        return
    signature = f"scope:{outcome.scope.scope_key}:{outcome.scope.reason}"
    details = {
        "scope_key": outcome.scope.scope_key,
        "reason": outcome.scope.reason,
        "scope_id": outcome.scope.scope_id,
    }
    with conn.cursor() as cur:
        # 같은 (facility_id, signature)가 ACCUMULATING 상태로 있으면 누적
        cur.execute(
            """
            SELECT residual_id
            FROM review.residual_item
            WHERE facility_id = %s
              AND signature = %s
              AND status = 'ACCUMULATING'
            LIMIT 1
            """,
            (facility_id, signature),
        )
        existing = cur.fetchone()

        if existing is not None:
            # 누적
            cur.execute(
                """
                UPDATE review.residual_item
                SET occurrence_count = occurrence_count + 1,
                    last_seen_at = now(),
                    assessment_id = %s,
                    details = %s
                WHERE residual_id = %s
                """,
                (outcome.assessment_id, Jsonb(details),
                 existing["residual_id"]),
            )
            outcome.residual_id = str(existing["residual_id"])
        else:
            cur.execute(
                """
                INSERT INTO review.residual_item
                    (facility_id, assessment_id, residual_type,
                     signature, details, status)
                VALUES (%s, %s, %s, %s, %s, 'ACCUMULATING')
                RETURNING residual_id
                """,
                (facility_id, outcome.assessment_id, residual_type,
                 signature, Jsonb(details)),
            )
            outcome.residual_id = str(cur.fetchone()["residual_id"])
    conn.commit()