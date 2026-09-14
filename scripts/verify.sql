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