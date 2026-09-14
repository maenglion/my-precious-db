-- 0040_core.sql
-- Ticket 005: 시설 + facts

CREATE TABLE core.facility (
    facility_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name             text NOT NULL,
    external_ref     text,
    address          text,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.facility_fact (
    fact_id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id       uuid NOT NULL REFERENCES core.facility,
    fact_key          text NOT NULL,
    value_json        jsonb NOT NULL,
    unit              text,
    source_block_id   uuid REFERENCES ingest.source_block,
    observed_at       timestamptz,
    effective_from    date,
    effective_to      date,
    confidence        numeric,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX facility_fact_facility_idx
ON core.facility_fact(facility_id);

CREATE INDEX facility_fact_key_idx
ON core.facility_fact(fact_key);

CREATE INDEX facility_fact_value_gin
ON core.facility_fact USING GIN(value_json);