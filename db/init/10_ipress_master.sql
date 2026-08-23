-- ============================================================================
-- 10_ipress_master.sql — Catálogo nacional real de establecimientos (F-C1)
-- ----------------------------------------------------------------------------
-- Proyecto : SaludCerca
-- Fase     : F-C1 (portal ciudadano, datos nacionales)
-- Fuente   : data-mining/ fusiona RENIPRESS SUSALUD (mensual, ODC-BY) + OSM
--
-- NOTAS:
--   * Complementa la tabla `ipress` sintética usada por pipeline/QA/demos;
--     NO la reemplaza (los tests Gold dependen de sus conteos exactos).
--   * Registros sin geom = candidatos naturales para tareas de contribuidores.
--   * pg_trgm habilita búsqueda fuzzy del portal ciudadano.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS ipress_master (
    id               SERIAL PRIMARY KEY,
    codigo_renipress VARCHAR(20) UNIQUE,
    nombre           VARCHAR(250) NOT NULL,
    nombre_norm      VARCHAR(250),
    tipo             VARCHAR(30)  NOT NULL DEFAULT 'OTRO',
    sector           VARCHAR(15)  NOT NULL DEFAULT 'OTRO',
    clasificacion    VARCHAR(120),
    categoria        VARCHAR(10),
    departamento     VARCHAR(60),
    provincia        VARCHAR(60),
    distrito         VARCHAR(60),
    ubigeo           CHAR(6),
    direccion        TEXT,
    telefono         VARCHAR(80),
    horario          TEXT,
    abierto_24h      BOOLEAN NOT NULL DEFAULT FALSE,
    latitud          DOUBLE PRECISION,
    longitud         DOUBLE PRECISION,
    geom             GEOMETRY(Point, 4326)
                     GENERATED ALWAYS AS (
                         CASE WHEN latitud IS NOT NULL AND longitud IS NOT NULL
                              THEN ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)
                              ELSE NULL END
                     ) STORED,
    osm_id           VARCHAR(30),
    fuente           VARCHAR(12) NOT NULL DEFAULT 'RENIPRESS'
                     CHECK (fuente IN ('RENIPRESS', 'OSM', 'MIXTO')),
    confianza        SMALLINT NOT NULL DEFAULT 70
                     CHECK (confianza BETWEEN 0 AND 100),
    verificacion     VARCHAR(20) NOT NULL DEFAULT 'SIN_VERIFICAR'
                     CHECK (verificacion IN ('OFICIAL', 'SIN_VERIFICAR',
                                             'VERIFICADO_CONTRIBUIDOR',
                                             'RECHAZADO')),
    activo           BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_master_coords CHECK (
        latitud IS NULL OR (latitud BETWEEN -19 AND 0.5
                            AND longitud BETWEEN -82 AND -68)
    )
);

COMMENT ON TABLE ipress_master IS
    'Catalogo nacional real de IPRESS (RENIPRESS+OSM). Base del buscador ciudadano.';

-- Índices: geo KNN, búsqueda fuzzy y filtros del portal
CREATE INDEX IF NOT EXISTS idx_master_geom ON ipress_master USING GIST (geom);
-- Índice geography para ST_DWithin/ST_Distance en metros (búsqueda por radio)
CREATE INDEX IF NOT EXISTS idx_master_geom_geog ON ipress_master
    USING GIST ((geom::geography));
CREATE INDEX IF NOT EXISTS idx_master_nombre_trgm ON ipress_master
    USING GIN (nombre_norm gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_master_ubigeo ON ipress_master (ubigeo);
CREATE INDEX IF NOT EXISTS idx_master_tipo_activo ON ipress_master (tipo, activo);
CREATE INDEX IF NOT EXISTS idx_master_departamento ON ipress_master (departamento);

-- ============================================================================
-- VISTA de apoyo para el buscador ciudadano: solo activos con ubicación
-- ============================================================================
DROP VIEW IF EXISTS v_establecimientos_busqueda;
CREATE VIEW v_establecimientos_busqueda AS
SELECT id, nombre, nombre_norm, tipo, sector, categoria,
       departamento, provincia, distrito,
       direccion, telefono, horario, abierto_24h,
       latitud, longitud, confianza, verificacion
  FROM ipress_master
 WHERE activo
 ORDER BY id;
