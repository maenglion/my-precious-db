-- 0010_ingest.sql
-- Ticket 002: 원문/파싱 적재

CREATE TABLE ingest.source_document (
    document_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name        text NOT NULL,
    file_type        text NOT NULL,
    sha256           text NOT NULL,
    parser_name      text NOT NULL,
    parser_version   text NOT NULL,
    parsed_at        timestamptz NOT NULL,
    source_uri       text,
    UNIQUE (sha256, parser_version)
);

CREATE TABLE ingest.source_block (
    block_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id      uuid NOT NULL REFERENCES ingest.source_document,
    block_no         integer NOT NULL,
    block_type       text NOT NULL,
    heading_path     jsonb,
    text             text NOT NULL,
    page_no          integer,
    raw_meta         jsonb,
    UNIQUE (document_id, block_no)
);