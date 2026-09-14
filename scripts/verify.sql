SELECT extname FROM pg_extension
WHERE extname IN ('ltree','pg_trgm','pgcrypto')
ORDER BY extname;

SELECT schema_name FROM information_schema.schemata
WHERE schema_name IN ('ingest','law','rule','core','assess','review','audit')
ORDER BY schema_name;

-- Ticket 002
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'ingest'
ORDER BY table_name;
-- Ticket 003
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'law'
ORDER BY table_name;

SELECT indexname
FROM pg_indexes
WHERE schemaname = 'law'
ORDER BY indexname;

SELECT extname, extversion
FROM pg_extension
WHERE extname = 'ltree';
-- Ticket 004
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'rule'
ORDER BY table_name;

SELECT indexname
FROM pg_indexes
WHERE schemaname = 'rule'
ORDER BY indexname;

SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'rule' AND table_name = 'expression'
ORDER BY ordinal_position;
-- Ticket 005
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'core'
ORDER BY table_name;

SELECT indexname
FROM pg_indexes
WHERE schemaname = 'core'
ORDER BY indexname;
-- Ticket 006
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'assess'
ORDER BY table_name;

SELECT indexname
FROM pg_indexes
WHERE schemaname = 'assess'
ORDER BY indexname;

SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'assess.assessment'::regclass
  AND contype = 'c'
ORDER BY conname;
-- Ticket 007
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'review'
ORDER BY table_name;

SELECT indexname
FROM pg_indexes
WHERE schemaname = 'review'
ORDER BY indexname;

SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'review.residual_item'::regclass
  AND contype = 'c'
ORDER BY conname;