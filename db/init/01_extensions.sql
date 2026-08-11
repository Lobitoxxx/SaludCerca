-- ============================================================================
-- SALUD CERCA - 01. Extensiones espaciales y vectoriales
-- ----------------------------------------------------------------------------
-- Habilita las extensiones del ecosistema Lakehouse:
--   * postgis         -> tipos GEOMETRY/GEOGRAPHY, ST_DWithin, ST_Distance...
--   * postgis_topology -> Topología opcional (redes, conectividad)
--   * vector          -> pgvector: embeddings y búsqueda semántica HNSW/IVFFlat
--   * pg_trgm         -> Similitud de texto (apoyo a búsqueda difusa)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verificación de versión (opcional, útil para el informe de evaluación)
SELECT 'postgis'  AS extension, extversion FROM pg_extension WHERE extname='postgis'
UNION ALL SELECT 'vector', extversion FROM pg_extension WHERE extname='vector'
UNION ALL SELECT 'pg_trgm', extversion FROM pg_extension WHERE extname='pg_trgm';
