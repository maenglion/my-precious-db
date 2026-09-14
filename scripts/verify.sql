SELECT extname FROM pg_extension
WHERE extname IN ('ltree','pg_trgm','pgcrypto')
ORDER BY extname;

SELECT schema_name FROM information_schema.schemata
WHERE schema_name IN ('ingest','law','rule','core','assess','review','audit')
ORDER BY schema_name;
