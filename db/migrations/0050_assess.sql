-- 0050_assess.sql
-- Ticket 006: 판정 + rule/predicate 평가 로그

CREATE TABLE assess.assessment (
    assessment_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id      uuid NOT NULL REFERENCES core.facility,
    assessed_at      timestamptz NOT NULL DEFAULT now(),
    as_of            date NOT NULL,
    result           text NOT NULL CHECK (result IN ('APPLICABLE','NOT_APPLICABLE','EXCLUDED','INDETERMINATE')),
    matched_rule_id  uuid REFERENCES rule.rule,
    engine_version   text NOT NULL
);

CREATE TABLE assess.rule_evaluation (
    rule_eval_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id    uuid NOT NULL REFERENCES assess.assessment,
    rule_id          uuid NOT NULL REFERENCES rule.rule,
    result           text NOT NULL CHECK (result IN ('TRUE','FALSE','UNKNOWN')),
    evaluated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE assess.predicate_evaluation (
    predicate_eval_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_eval_id      uuid NOT NULL REFERENCES assess.rule_evaluation,
    expr_id           uuid NOT NULL REFERENCES rule.expression,
    fact_id           uuid REFERENCES core.facility_fact,
    actual_value      jsonb,
    expected_value    jsonb,
    operator          text,
    result            text NOT NULL CHECK (result IN ('TRUE','FALSE','UNKNOWN')),
    reason            text
);

CREATE INDEX assessment_facility_idx
ON assess.assessment(facility_id);

CREATE INDEX assessment_result_idx
ON assess.assessment(result);

CREATE INDEX rule_evaluation_assessment_idx
ON assess.rule_evaluation(assessment_id);

CREATE INDEX predicate_evaluation_rule_eval_idx
ON assess.predicate_evaluation(rule_eval_id);