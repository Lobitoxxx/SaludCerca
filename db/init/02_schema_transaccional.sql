-- ============================================================================
-- SALUD CERCA - 02. Esquema transaccional (Capa de ingesta / ODS)
-- ----------------------------------------------------------------------------
-- Representa el modelo operacional normalizado (OLTP-ish) que alimenta el
-- Lakehouse. Las capas Silver (Parquet) y Gold (PostgreSQL) se construyen a
-- partir de estas tablas vía el pipeline PySpark.
--   * categorizaciones   -> Catálogo MINSA de categorías I-1 .. III-E
--   * especialidades     -> Catálogo de especialidades médicas
--   * ubigeo             -> División política INEI (dept/prov/dist) + centroides
--   * ipress             -> Establecimientos de salud (RENIPRESS) + geometría
--   * atenciones_his     -> Atenciones HIS-MINSA (PARTICIONADA por fecha)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Catálogo de categorías de establecimientos (capacidad resolutiva)
-- ---------------------------------------------------------------------------
CREATE TABLE categorizaciones (
    id                  SERIAL PRIMARY KEY,
    codigo              VARCHAR(8)  NOT NULL UNIQUE,          -- I-1, I-2, ..., III-1, III-E
    nombre              VARCHAR(120) NOT NULL,                -- Puesto de Salud, Hospital I, ...
    nivel_atencion      INTEGER     NOT NULL,                 -- 1 (primario) .. 3 (altamente complejo)
    capacidad_resolutiva INTEGER    NOT NULL CHECK (capacidad_resolutiva BETWEEN 1 AND 10),
    descripcion         TEXT,
    descripcion_emb     vector(384)                           -- Embedding semántico (pgvector)
);

COMMENT ON TABLE categorizaciones IS
    'Catálogo de categorías RENIPRESS/MINSA con nivel de complejidad y capacidad resolutiva.';

-- ---------------------------------------------------------------------------
-- Catálogo de especialidades médicas
-- ---------------------------------------------------------------------------
CREATE TABLE especialidades (
    id                  SERIAL PRIMARY KEY,
    codigo              VARCHAR(10) NOT NULL UNIQUE,           -- MEDGEN, PEDIA, CARDI, ...
    nombre              VARCHAR(120) NOT NULL,
    complejidad_minima  INTEGER NOT NULL CHECK (complejidad_minima BETWEEN 1 AND 3),
    descripcion         TEXT,
    descripcion_emb     vector(384)
);

COMMENT ON TABLE especialidades IS
    'Especialidades médicas con el nivel de atención mínimo requerido (I-1..III-1).';

-- ---------------------------------------------------------------------------
-- Ubigeo INEI: departamento / provincia / distrito + centroide espacial
-- ---------------------------------------------------------------------------
CREATE TABLE ubigeo (
    id                   SERIAL PRIMARY KEY,
    codigo_ubigeo        VARCHAR(6) NOT NULL UNIQUE,
    departamento         VARCHAR(60) NOT NULL,
    provincia            VARCHAR(60) NOT NULL,
    distrito             VARCHAR(60) NOT NULL,
    latitud_centroide    DOUBLE PRECISION,
    longitud_centroide   DOUBLE PRECISION,
    geom_centroide       geometry(Point, 4326)
);

CREATE INDEX idx_ubigeo_dept ON ubigeo (departamento);
CREATE INDEX idx_ubigeo_prov ON ubigeo (departamento, provincia);

-- ---------------------------------------------------------------------------
-- IPRESS: establecimientos de salud (RENIPRESS)
-- ---------------------------------------------------------------------------
CREATE TABLE ipress (
    id                  SERIAL PRIMARY KEY,
    codigo_renipress    VARCHAR(12) NOT NULL UNIQUE,           -- Código RENIPRESS único
    nombre              VARCHAR(200) NOT NULL,
    categoria_id        INTEGER NOT NULL REFERENCES categorizaciones (id),
    ubigeo_id           INTEGER REFERENCES ubigeo (id),
    direccion           VARCHAR(255),
    departamento        VARCHAR(60),
    provincia           VARCHAR(60),
    distrito            VARCHAR(60),
    latitud             DOUBLE PRECISION,
    longitud            DOUBLE PRECISION,
    geom                geometry(Point, 4326),
    estado_operativo    VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'
                        CHECK (estado_operativo IN ('ACTIVO','INACTIVO','REFERENCIAL')),
    capacidad_camas     INTEGER NOT NULL DEFAULT 0,
    capacidad_consultorios INTEGER NOT NULL DEFAULT 0,
    horario             VARCHAR(60),
    tiene_ambulancia    BOOLEAN NOT NULL DEFAULT FALSE,
    telefono            VARCHAR(30),
    propietario         VARCHAR(60),                           -- MINSA, ESSALUD, PRIVADO, FFAA/PNP...
    descripcion_emb     vector(384)                            -- Embedding semántico del establecimiento
);

COMMENT ON COLUMN ipress.geom IS 'Geometría WGS84 (SRID 4326) para operadores espaciales PostGIS.';
COMMENT ON COLUMN ipress.estado_operativo IS 'Estado operativo del establecimiento (RENIPRESS).';
COMMENT ON COLUMN ipress.descripcion_emb IS 'Embedding de búsqueda semántica (pgvector, 384 dims).';

-- ---------------------------------------------------------------------------
-- Atenciones HIS-MINSA (volumen masivo) - TABLA PARTICIONADA POR RANGO
-- ---------------------------------------------------------------------------
-- La partición declarativa por rango mensual permite consultas tipo "point in
-- time" sobre millones de registros mediante pruning de particiones (runtime
-- partitioning elimination) sin tocar los datos completos.
-- Las particiones mensuales se crean en 06_seed.sql (demo) o dinámicamente en
-- el pipeline Gold (postgis_writer.py) para volúmenes reales.
-- ---------------------------------------------------------------------------
CREATE TABLE atenciones_his (
    id                  BIGSERIAL,
    codigo_ipress       VARCHAR(12) NOT NULL,                   -- Código RENIPRESS del establecimiento
    ipress_id           INTEGER NOT NULL REFERENCES ipress (id),
    codigo_ubigeo       VARCHAR(6)  NOT NULL REFERENCES ubigeo (codigo_ubigeo),
    fecha_atencion      DATE NOT NULL,
    especialidad_id     INTEGER NOT NULL REFERENCES especialidades (id),
    diagnostico_cie10   VARCHAR(8),                              -- Clasificación CIE-10
    tipo_atencion       VARCHAR(20) NOT NULL DEFAULT 'CONSULTA'
                        CHECK (tipo_atencion IN ('CONSULTA','EMERGENCIA','HOSPITALIZACION','PREVENTIVA')),
    edad_paciente       INTEGER CHECK (edad_paciente BETWEEN 0 AND 120),
    sexo                CHAR(1) CHECK (sexo IN ('M','F')),
    tiempo_espera_min   INTEGER,                                 -- Proxy de saturación / congestión
    estado_salida       VARCHAR(20)
                        CHECK (estado_salida IN ('ALTA','DERIVADO','HOSPITALIZADO','OBSERVACION','FALLECIDO','ABANDONO')),
    derivado_a          VARCHAR(12),                             -- Código RENIPRESS destino si DERIVADO
    PRIMARY KEY (id, fecha_atencion)                             -- La clave de partición forma parte del PK
) PARTITION BY RANGE (fecha_atencion);

COMMENT ON TABLE atenciones_his IS
    'Atenciones HIS-MINSA particionadas por mes (millones de registros en producción).';
COMMENT ON COLUMN atenciones_his.tiempo_espera_min IS 'Proxy de saturación: minutos de espera antes de la atención.';

-- ---------------------------------------------------------------------------
-- Función utilitaria: crea la partición mensual si no existe
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION crear_particion_mensual(IN p_fecha DATE)
RETURNS VOID AS $$
DECLARE
    -- Longitud suficiente: 'atenciones_his_' (16) + 'YYYY_MM' (7)
    v_nombre VARCHAR(40) := 'atenciones_his_' || to_char(p_fecha, 'YYYY_MM');
    v_desde  DATE := date_trunc('month', p_fecha);
    v_hasta  DATE := date_trunc('month', p_fecha) + INTERVAL '1 month';
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = v_nombre
    ) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF atenciones_his FOR VALUES FROM (%L) TO (%L)',
            v_nombre, v_desde, v_hasta
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION crear_particion_mensual(DATE) IS
    'Crea dinámicamente la partición mensual de atenciones_his para la fecha dada (usado por el pipeline Gold).';
