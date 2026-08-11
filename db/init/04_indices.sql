-- ============================================================================
-- SALUD CERCA - 04. Índices espaciales (GIST), vectoriales (HNSW/IVFFlat)
--                 y de rendimiento (BTREE / BRIN)
-- ----------------------------------------------------------------------------
-- Estrategia de indexación para consultas masivas:
--   * GIST  sobre columnas GEOMETRY -> búsquedas ST_DWithin / ST_Distance / KNN
--   * HNSW  sobre embeddings pgvector -> búsqueda semántica ANN sub-10ms
--   * IVFFlat (alternativa) -> ANN más ligero, requiere entrenamiento previo
--   * BTREE sobre claves de negocio y FKs
--   * BRIN  sobre la columna de partición de la tabla masiva (compacto)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 4.1 Índices ESPACIALES (GIST) - núcleo de las consultas geográficas
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_ipress_geom
    ON ipress USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_ubigeo_geom
    ON ubigeo USING GIST (geom_centroide);

CREATE INDEX IF NOT EXISTS idx_dim_ipress_geom
    ON dim_ipress USING GIST (geom);

-- ---------------------------------------------------------------------------
-- 4.2 Índices VECTORIALES (HNSW) - búsqueda semántica pgvector
--     Algoritmo de grafo jerárquico navegable: precisión alta, latencia baja.
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_ipress_emb
    ON ipress USING hnsw (descripcion_emb vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_especialidades_emb
    ON especialidades USING hnsw (descripcion_emb vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 4.3 ALTERNATIVA IVFFlat (comentada por requerir entrenamiento previo con datos)
--     Inverted File Flat: más ligera, menos precisa; útil para conjuntos grandes
--     de embeddings cuando HNSW consume demasiada memoria.
--     IMPORTANTE: debe crearse LUEGO de cargar datos (usa K-means interno).
--
-- CREATE INDEX IF NOT EXISTS idx_ipress_emb_ivfflat
--     ON ipress USING ivfflat (descripcion_emb vector_cosine_ops)
--     WITH (lists = 100);
--
-- CREATE INDEX IF NOT EXISTS idx_especialidades_emb_ivfflat
--     ON especialidades USING ivfflat (descripcion_emb vector_cosine_ops)
--     WITH (lists = 16);

-- ---------------------------------------------------------------------------
-- 4.4 Índices BTREE (claves de negocio, FKs y filtros de BI)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_ipress_categoria   ON ipress (categoria_id);
CREATE INDEX IF NOT EXISTS idx_ipress_ubigeo      ON ipress (ubigeo_id);
CREATE INDEX IF NOT EXISTS idx_ipress_estado      ON ipress (estado_operativo);
CREATE INDEX IF NOT EXISTS idx_ipress_dept        ON ipress (departamento, provincia);
CREATE INDEX IF NOT EXISTS idx_ipress_nombre_trgm ON ipress USING gin (nombre gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- 4.5 Índices de la tabla masiva particionada (BRIN para pruning eficiente)
-- ---------------------------------------------------------------------------
-- BRIN es ideal para columnas correlacionadas físicamente (fecha en tabla
-- particionada por rango): ocupa kB en lugar de MB y acelera agregaciones.
CREATE INDEX IF NOT EXISTS idx_atenciones_his_fecha ON atenciones_his USING brin (fecha_atencion);
CREATE INDEX IF NOT EXISTS idx_atenciones_his_ipress ON atenciones_his (codigo_ipress);
CREATE INDEX IF NOT EXISTS idx_atenciones_his_esp    ON atenciones_his (especialidad_id);
CREATE INDEX IF NOT EXISTS idx_atenciones_his_ubigeo ON atenciones_his (codigo_ubigeo);
CREATE INDEX IF NOT EXISTS idx_atenciones_his_tipo   ON atenciones_his (tipo_atencion);
