-- 0070_audit.sql
-- Ticket 008: 감사 이벤트

CREATE TABLE audit.event (
    event_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_type        text NOT NULL CHECK (actor_type IN ('OWNER','ADMIN','BOT','SYSTEM')),
    actor_id          text,
    action            text NOT NULL,
    object_type       text NOT NULL,
    object_id         uuid,
    before_json       jsonb,
    after_json        jsonb,
    occurred_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX audit_event_object_idx
ON audit.event(object_type, object_id);

CREATE INDEX audit_event_occurred_idx
ON audit.event(occurred_at DESC);

CREATE INDEX audit_event_action_idx
ON audit.event(action);