-- 0035_rule_scope.sql
-- Ticket 013a: Candidate Scope Registry + Coverage Resolution

CREATE TABLE rule.scope (
    scope_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_key         text NOT NULL,
    name              text NOT NULL,
    source_node_id    uuid NOT NULL REFERENCES law.node,
    coverage_status   text NOT NULL DEFAULT 'UNVERIFIED'
                      CHECK (coverage_status IN (
                          'UNVERIFIED',
                          'PARTIAL',
                          'COMPLETE'
                      )),
    effective_from    date NOT NULL,
    effective_to      date,
    verified_by       text,
    verified_at       timestamptz,
    status            text NOT NULL DEFAULT 'ACTIVE'
                      CHECK (status IN ('ACTIVE','DEPRECATED')),
    UNIQUE(scope_key, effective_from)
);

CREATE INDEX rule_scope_key_idx
ON rule.scope(scope_key);

CREATE INDEX rule_scope_source_node_idx
ON rule.scope(source_node_id);

ALTER TABLE rule.rule
ADD COLUMN scope_id uuid REFERENCES rule.scope(scope_id);

CREATE INDEX rule_rule_scope_idx
ON rule.rule(scope_id);