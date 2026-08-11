-- ============================================================================
-- SALUD CERCA - 03. Capa Gold: Modelo Dimensional en Estrella (OLAP / BI)
-- ----------------------------------------------------------------------------
-- Modelo dimensional Kimball para consultas de inteligencia de negocio:
--
--                          dim_ipress
--                              |
--   dim_tiempo -------- fact_atenciones_medicas ------- dim_ubigeo
--
-- Los hechos son agregados pre-calculados (grains: IPRESS x día x ubigeo)
-- que permiten KPIs de saturación, ocupación y cobertura sin escanear la
-- tabla particionada transaccional de millones de filas.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Dimensión Tiempo
-- ---------------------------------------------------------------------------
CREATE TABLE dim_tiempo (
    tiempo_key         DATE PRIMARY KEY,
    anio               SMALLINT NOT NULL,
    mes                SMALLINT NOT NULL,
    dia                SMALLINT NOT NULL,
    trimestre          SMALLINT NOT NULL,
    semana_iso         SMALLINT,
    nombre_mes         VARCHAR(12),
    nombre_dia         VARCHAR(12),
    es_fin_de_semana   BOOLEAN
);

COMMENT ON TABLE dim_tiempo IS 'Dimensión calendario (grain diario) para análisis temporal de atenciones.';

-- ---------------------------------------------------------------------------
-- Dimensión Ubigeo
-- ---------------------------------------------------------------------------
CREATE TABLE dim_ubigeo (
    ubigeo_key          INTEGER PRIMARY KEY,       -- Surrogate = id de ubigeo transaccional
    codigo_ubigeo       VARCHAR(6) UNIQUE NOT NULL,
    departamento        VARCHAR(60) NOT NULL,
    provincia           VARCHAR(60) NOT NULL,
    distrito            VARCHAR(60) NOT NULL,
    latitud_centroide   DOUBLE PRECISION,
    longitud_centroide  DOUBLE PRECISION,
    geom_centroide      geometry(Point, 4326)
);

COMMENT ON TABLE dim_ubigeo IS 'Dimensión geográfica INEI (dept/prov/dist) con centroide espacial.';

-- ---------------------------------------------------------------------------
-- Dimensión IPRESS (denormalizada para BI)
-- ---------------------------------------------------------------------------
CREATE TABLE dim_ipress (
    ipress_key           INTEGER PRIMARY KEY,      -- Surrogate = id de ipress transaccional
    codigo_renipress     VARCHAR(12) UNIQUE NOT NULL,
    nombre               VARCHAR(200) NOT NULL,
    categoria            VARCHAR(8) NOT NULL,
    nivel_atencion       SMALLINT NOT NULL,
    capacidad_resolutiva SMALLINT NOT NULL,
    departamento         VARCHAR(60),
    provincia            VARCHAR(60),
    distrito             VARCHAR(60),
    latitud              DOUBLE PRECISION,
    longitud             DOUBLE PRECISION,
    geom                 geometry(Point, 4326),
    estado_operativo     VARCHAR(20),
    capacidad_camas      INTEGER,
    propietario          VARCHAR(60)
);

COMMENT ON TABLE dim_ipress IS
    'Dimensión de establecimientos denormalizada (categoría + ubicación + operatividad) para BI.';

-- ---------------------------------------------------------------------------
-- Tabla de Hechos: atenciones médicas agregadas por día
-- ---------------------------------------------------------------------------
CREATE TABLE fact_atenciones_medicas (
    fact_id                    BIGSERIAL PRIMARY KEY,
    ipress_key                 INTEGER NOT NULL REFERENCES dim_ipress (ipress_key),
    tiempo_key                 DATE NOT NULL REFERENCES dim_tiempo (tiempo_key),
    ubigeo_key                 INTEGER NOT NULL REFERENCES dim_ubigeo (ubigeo_key),
    num_atenciones             BIGINT NOT NULL DEFAULT 0,
    num_emergencias            BIGINT NOT NULL DEFAULT 0,
    num_hospitalizaciones      BIGINT NOT NULL DEFAULT 0,
    num_derivaciones           BIGINT NOT NULL DEFAULT 0,
    ocupacion_promedio         NUMERIC(6,2),        -- Ocupación estimada de camas (0-100%)
    tiempo_espera_promedio     NUMERIC(7,2),        -- Minutos promedio de espera
    tasa_saturacion            NUMERIC(5,2),        -- 0..100: sobrecarga del establecimiento
    UNIQUE (ipress_key, tiempo_key, ubigeo_key)
);

COMMENT ON TABLE fact_atenciones_medicas IS
    'Hechos OLAP: agregados de atenciones por (IPRESS, día, ubigeo) con métricas de saturación.';
COMMENT ON COLUMN fact_atenciones_medicas.tasa_saturacion IS
    'Indicador 0-100 que combina ocupación y tiempo de espera; alimenta el motor de recomendación anti-saturación.';

-- Índices de las claves foráneas de la tabla de hechos
CREATE INDEX idx_fact_tiempo     ON fact_atenciones_medicas (tiempo_key);
CREATE INDEX idx_fact_ubigeo     ON fact_atenciones_medicas (ubigeo_key);
CREATE INDEX idx_fact_ipress     ON fact_atenciones_medicas (ipress_key);
