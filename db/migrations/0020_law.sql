-- 0020_law.sql
-- Ticket 003: 법령 계층 + 참조 그래프

CREATE TABLE law.statute (
    statute_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name             text NOT NULL,
    statute_type     text NOT NULL,
    ministry         text,
    promulgated_at   date,
    effective_from   date NOT NULL,
    effective_to     date,
    revision_type    text
);

CREATE TABLE law.node (
    node_id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    statute_id        uuid NOT NULL REFERENCES law.statute,
    source_block_id   uuid REFERENCES ingest.source_block,
    path              ltree NOT NULL,
    node_type         text NOT NULL,
    text              text NOT NULL,
    effective_from    date NOT NULL,
    effective_to      date,
    UNIQUE (statute_id, path, effective_from)
);

CREATE INDEX law_node_path_gist
ON law.node USING GIST(path);

CREATE TABLE law.reference_edge (
    edge_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    from_node_id     uuid NOT NULL REFERENCES law.node,
    to_node_id       uuid NOT NULL REFERENCES law.node,
    edge_type        text NOT NULL,
    effective_from   date NOT NULL,
    effective_to     date,
    source_note      text
);