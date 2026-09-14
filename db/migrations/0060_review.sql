-- 0060_review.sql
-- Ticket 007: residual — 판정 실패 원인 분류

CREATE TABLE review.residual_item (
    residual_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id       uuid REFERENCES core.facility,
    assessment_id     uuid REFERENCES assess.assessment,
    residual_type     text NOT NULL CHECK (residual_type IN (
                          'MISSING_FACT',
                          'UNMAPPED_SOURCE_TYPE',
                          'RULE_COVERAGE',
                          'SOURCE_CONFLICT',
                          'PARSER',
                          'IDENTITY',
                          'LAW_VERSION_CONFLICT'
                      )),
    signature         text,
    details           jsonb,
    first_seen_at     timestamptz NOT NULL DEFAULT now(),
    last_seen_at      timestamptz NOT NULL DEFAULT now(),
    occurrence_count  integer NOT NULL DEFAULT 1,
    status            text NOT NULL DEFAULT 'ACCUMULATING'
);

CREATE INDEX residual_item_type_idx
ON review.residual_item(residual_type);

CREATE INDEX residual_item_signature_idx
ON review.residual_item(signature);

CREATE INDEX residual_item_status_idx
ON review.residual_item(status);