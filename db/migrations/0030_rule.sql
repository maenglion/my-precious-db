-- 0030_rule.sql
-- Ticket 004: Rule Engine (AND/OR/NOT/PREDICATE 트리)

CREATE TABLE rule.rule (
    rule_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id   uuid NOT NULL REFERENCES law.node,
    name             text NOT NULL,
    effect           text NOT NULL CHECK (effect IN ('INCLUDE','EXCLUDE')),
    priority         integer NOT NULL DEFAULT 100,
    effective_from   date NOT NULL,
    effective_to     date,
    status           text NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE rule.expression (
    expr_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id          uuid NOT NULL REFERENCES rule.rule,
    parent_expr_id   uuid REFERENCES rule.expression,
    expr_type        text NOT NULL CHECK (expr_type IN ('AND','OR','NOT','PREDICATE')),
    bool_op          text,
    fact_key         text,
    operator         text,
    compare_value    jsonb,
    unit             text,
    sort_order       integer NOT NULL DEFAULT 0
);

CREATE INDEX rule_expression_rule_id_idx
ON rule.expression(rule_id);

CREATE INDEX rule_expression_parent_idx
ON rule.expression(parent_expr_id);

CREATE INDEX rule_rule_source_node_idx
ON rule.rule(source_node_id);