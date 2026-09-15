-- 0065_review_ontology.sql
-- Ticket 013f: ontology 후보 큐

CREATE TABLE review.ontology_candidate (
    candidate_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    residual_id      uuid NOT NULL REFERENCES review.residual_item,
    candidate_type   text NOT NULL CHECK (candidate_type IN (
                         'ALIAS',
                         'CLASS',
                         'MAPPING',
                         'SCOPE'
                     )),
    proposed_value   text NOT NULL,
    parent_value     text,
    rationale        text,
    confidence       numeric,
    status           text NOT NULL DEFAULT 'PENDING'
                     CHECK (status IN (
                         'PENDING',
                         'APPROVED',
                         'REJECTED',
                         'DEFERRED'
                     )),
    reviewed_by      text,
    reviewed_at      timestamptz,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ontology_candidate_status_idx
ON review.ontology_candidate(status);

CREATE INDEX ontology_candidate_residual_idx
ON review.ontology_candidate(residual_id);

CREATE INDEX ontology_candidate_type_idx
ON review.ontology_candidate(candidate_type);