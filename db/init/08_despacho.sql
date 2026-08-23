-- ============================================================================
-- SALUD CERCA - 08. Capa operativa de despacho en tiempo real (F0)
-- ----------------------------------------------------------------------------
-- Tablas transaccionales del negocio de emergencias:
--
--   * organizaciones            -> tenants B2B (operadores de ambulancias)
--   * usuarios_app              -> usuarios del sistema (admin/operador/conductor)
--   * ambulancias               -> flota con estado y última posición conocida
--   * posiciones_ambulancia     -> historial GPS por unidad
--   * emergencias               -> solicitudes de auxilio con triaje y SLA
--   * asignaciones              -> emergencia <-> ambulancia con tiempos por etapa
--   * hospital_capacidad_rt     -> capacidad declarada en vivo por IPRESS
--   * ambulancia_disponible_cercana() -> KNN de unidades DISPONIBLES
--
-- Convenciones: dominios CHECK, geometría Point 4326 + índice GIST,
-- timestamps America/Lima gestionados a nivel sesión (TZ contenedor).
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 8.1 Organizaciones (tenants B2B)
-- ---------------------------------------------------------------------------
CREATE TABLE organizaciones (
    id            SERIAL PRIMARY KEY,
    nombre        VARCHAR(160) NOT NULL,
    ruc           VARCHAR(11) UNIQUE,
    tipo          VARCHAR(20) NOT NULL DEFAULT 'PRIVADA'
                  CHECK (tipo IN ('PRIVADA', 'MUNICIPAL', 'MIXTA', 'HOSPITAL')),
    telefono      VARCHAR(30),
    email         VARCHAR(120),
    activa        BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE organizaciones IS 'Operadores B2B suscritos a la plataforma (flotas de ambulancias).';

-- ---------------------------------------------------------------------------
-- 8.2 Usuarios de la aplicación
-- ---------------------------------------------------------------------------
CREATE TABLE usuarios_app (
    id               SERIAL PRIMARY KEY,
    organizacion_id  INTEGER REFERENCES organizaciones(id),
    dni              VARCHAR(12) UNIQUE,
    nombres          VARCHAR(120) NOT NULL,
    apellidos        VARCHAR(120),
    telefono         VARCHAR(30) NOT NULL,
    email            VARCHAR(120) UNIQUE,
    rol              VARCHAR(20) NOT NULL
                     CHECK (rol IN ('ADMIN', 'OPERADOR', 'CONDUCTOR', 'CONTRIBUIDOR')),
    activo           BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE usuarios_app IS 'Usuarios multi-tenant; CONTRIBUIDOR pertenece a la red humana de datos.';
CREATE INDEX idx_usuarios_rol ON usuarios_app(rol) WHERE activo;
CREATE INDEX idx_usuarios_org ON usuarios_app(organizacion_id);

-- ---------------------------------------------------------------------------
-- 8.3 Ambulancias (flota)
-- ---------------------------------------------------------------------------
CREATE TABLE ambulancias (
    id                SERIAL PRIMARY KEY,
    organizacion_id   INTEGER NOT NULL REFERENCES organizaciones(id),
    placa             VARCHAR(10) UNIQUE NOT NULL,
    tipo              VARCHAR(15) NOT NULL
                      CHECK (tipo IN ('BASICA', 'INTERMEDIA', 'UCI')),
    estado            VARCHAR(20) NOT NULL DEFAULT 'FUERA_SERVICIO'
                      CHECK (estado IN ('DISPONIBLE', 'EN_CAMINO', 'EN_SITIO',
                                        'TRANSPORTE', 'FUERA_SERVICIO',
                                        'MANTENIMIENTO')),
    conductor_id      INTEGER REFERENCES usuarios_app(id),
    latitud           DOUBLE PRECISION,
    longitud          DOUBLE PRECISION,
    geom              GEOMETRY(Point, 4326),
    ultima_posicion   TIMESTAMPTZ,
    ipress_base_id    INTEGER REFERENCES ipress(id),  -- base/hogar de la unidad
    codigo_susalud    VARCHAR(20),                    -- referencia oficial SUSALUD si existe
    creado_en         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_coords_ambulancia CHECK (
        (latitud IS NULL AND longitud IS NULL) OR
        (latitud BETWEEN -90 AND 90 AND longitud BETWEEN -180 AND 180))
);

COMMENT ON TABLE ambulancias IS 'Unidades móviles: estado operativo en vivo y última posición GPS.';
CREATE INDEX idx_ambulancias_estado ON ambulancias(estado);
CREATE INDEX idx_ambulancias_geom ON ambulancias USING GIST (geom);
CREATE INDEX idx_ambulancias_org ON ambulancias(organizacion_id);

-- ---------------------------------------------------------------------------
-- 8.4 Historial de posiciones GPS
-- ---------------------------------------------------------------------------
CREATE TABLE posiciones_ambulancia (
    id             BIGSERIAL PRIMARY KEY,
    ambulancia_id  INTEGER NOT NULL REFERENCES ambulancias(id) ON DELETE CASCADE,
    latitud        DOUBLE PRECISION NOT NULL,
    longitud       DOUBLE PRECISION NOT NULL,
    geom           GEOMETRY(Point, 4326) GENERATED ALWAYS AS
                   (ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)) STORED,
    velocidad_kmh  SMALLINT CHECK (velocidad_kmh >= 0),
    reportado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE posiciones_ambulancia IS 'Trail GPS; la fila más reciente alimenta ambulancias.ultima_posicion.';
CREATE INDEX idx_posiciones_amb ON posiciones_ambulancia(ambulancia_id, reportado_en DESC);
CREATE INDEX idx_posiciones_brin ON posiciones_ambulancia USING BRIN (reportado_en);

-- ---------------------------------------------------------------------------
-- 8.5 Emergencias
-- ---------------------------------------------------------------------------
CREATE TABLE emergencias (
    id                    BIGSERIAL PRIMARY KEY,
    codigo                VARCHAR(20) UNIQUE NOT NULL,      -- p.ej. EMG-20260822-0001
    canal                 VARCHAR(15) NOT NULL
                          CHECK (canal IN ('APP', 'PWA', 'WHATSAPP', 'LLAMADA', 'PANEL')),
    organizacion_id       INTEGER REFERENCES organizaciones(id), -- operador que atiende
    ciudadano_telefono    VARCHAR(30),
    direccion_referencia  VARCHAR(255),
    latitud               DOUBLE PRECISION NOT NULL,
    longitud              DOUBLE PRECISION NOT NULL,
    geom                  GEOMETRY(Point, 4326) GENERATED ALWAYS AS
                          (ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)) STORED,
    triaje                CHAR(2) NOT NULL DEFAULT 'C4'
                          CHECK (triaje IN ('C1', 'C2', 'C3', 'C4')), -- Manchester
    descripcion           TEXT,
    especialidad_requerida INTEGER REFERENCES especialidades(id),
    estado                VARCHAR(15) NOT NULL DEFAULT 'RECIBIDA'
                          CHECK (estado IN ('RECIBIDA', 'ASIGNADA', 'EN_ATENCION',
                                            'EN_TRASLADO', 'COMPLETADA', 'CANCELADA')),
    hospital_destino_id   INTEGER REFERENCES ipress(id),
    -- Timestamps SLA (métrica reina: tiempo de respuesta = llegada_escena - creada)
    creada_en             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    asignada_en           TIMESTAMPTZ,
    llegada_escena_en     TIMESTAMPTZ,
    inicio_traslado_en    TIMESTAMPTZ,
    entregada_en          TIMESTAMPTZ,
    cerrada_en            TIMESTAMPTZ
);

COMMENT ON TABLE emergencias IS 'Solicitudes de auxilio con triaje C1-C4 y timestamps SLA por etapa.';
CREATE INDEX idx_emergencias_estado ON emergencias(estado);
CREATE INDEX idx_emergencias_geom ON emergencias USING GIST (geom);
CREATE INDEX idx_emergencias_triaje ON emergencias(triaje, creada_en DESC);

-- ---------------------------------------------------------------------------
-- 8.6 Asignaciones (emergencia <-> ambulancia)
-- ---------------------------------------------------------------------------
CREATE TABLE asignaciones (
    id                 BIGSERIAL PRIMARY KEY,
    emergencia_id      BIGINT NOT NULL REFERENCES emergencias(id),
    ambulancia_id      INTEGER NOT NULL REFERENCES ambulancias(id),
    estado             VARCHAR(12) NOT NULL DEFAULT 'PROPUESTA'
                       CHECK (estado IN ('PROPUESTA', 'ACEPTADA', 'RECHAZADA',
                                         'COMPLETADA', 'ANULADA')),
    distancia_km       NUMERIC(8,2),
    eta_min            SMALLINT CHECK (eta_min > 0),
    asignada_en        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    aceptada_en        TIMESTAMPTZ,
    completada_en      TIMESTAMPTZ,
    UNIQUE (emergencia_id, ambulancia_id)
);

COMMENT ON TABLE asignaciones IS 'Vínculo unidad-emergencia; una emergencia puede tener propuestas sucesivas.';
CREATE INDEX idx_asignaciones_ambulancia ON asignaciones(ambulancia_id, estado);

-- ---------------------------------------------------------------------------
-- 8.7 Capacidad hospitalaria en tiempo real
-- ---------------------------------------------------------------------------
CREATE TABLE hospital_capacidad_rt (
    id                        BIGSERIAL PRIMARY KEY,
    ipress_id                 INTEGER NOT NULL REFERENCES ipress(id),
    camas_uci_disponibles     SMALLINT CHECK (camas_uci_disponibles >= 0),
    camas_hosp_disponibles    SMALLINT CHECK (camas_hosp_disponibles >= 0),
    urgencia_estado           VARCHAR(12) NOT NULL DEFAULT 'NORMAL'
                              CHECK (urgencia_estado IN ('NORMAL', 'SATURADA',
                                                         'CRITICA', 'DESACTIVADA')),
    actualizado_por           VARCHAR(15) NOT NULL
                              CHECK (actualizado_por IN ('OFICIAL', 'OPERADOR',
                                                         'CONTRIBUIDOR', 'SISTEMA')),
    vigente_hasta             TIMESTAMPTZ NOT NULL,      -- dato vencido se ignora en scores
    actualizado_en            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE hospital_capacidad_rt IS 'Capacidad declarada en vivo; procedencia obligatoria para auditoría.';
CREATE INDEX idx_capacidad_ipress ON hospital_capacidad_rt(ipress_id, vigente_hasta DESC);

-- ---------------------------------------------------------------------------
-- 8.8 FUNCIÓN: ambulancias DISPONIBLES más cercanas a un punto
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ambulancia_disponible_cercana(
    IN p_lat         DOUBLE PRECISION,
    IN p_lon         DOUBLE PRECISION,
    IN p_radio_km    DOUBLE PRECISION DEFAULT 25.0,
    IN p_tipo_min    VARCHAR(15) DEFAULT 'BASICA',
    IN p_limite      INTEGER DEFAULT 5
)
RETURNS TABLE (
    id               INTEGER,
    placa            VARCHAR(10),
    tipo             VARCHAR(15),
    organizacion_id  INTEGER,
    distancia_km     NUMERIC,
    ultima_posicion  TIMESTAMPTZ
)
LANGUAGE sql STABLE AS $$
    SELECT a.id,
           a.placa,
           a.tipo,
           a.organizacion_id,
           ROUND((ST_Distance(a.geom::geography,
                             ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)::geography)
                  / 1000.0)::numeric, 2) AS distancia_km,
           a.ultima_posicion
      FROM ambulancias a
     WHERE a.estado = 'DISPONIBLE'
       AND a.geom IS NOT NULL
       AND a.tipo >= p_tipo_min                       -- BASICA < INTERMEDIA < UCI
       AND ST_DWithin(a.geom::geography,
                      ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)::geography,
                      p_radio_km * 1000)
     ORDER BY distancia_km ASC
     LIMIT p_limite;
$$;

COMMENT ON FUNCTION ambulancia_disponible_cercana(DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, VARCHAR, INTEGER) IS
    'KNN de unidades DISPONIBLES dentro de un radio, filtradas por tipo mínimo requerido (BASICA<=INTERMEDIA<=UCI).';

-- ---------------------------------------------------------------------------
-- 8.9 Seed demo (Lima centro) — idempotente por placa
-- ---------------------------------------------------------------------------
INSERT INTO organizaciones (nombre, ruc, tipo, telefono)
VALUES ('SaludCerca Demo SAC', '20512345678', 'PRIVADA', '+51 1 555 0001')
ON CONFLICT (ruc) DO NOTHING;

INSERT INTO ambulancias (organizacion_id, placa, tipo, estado, latitud, longitud, geom, ultima_posicion)
SELECT o.id, v.placa, v.tipo, 'DISPONIBLE', v.lat, v.lon,
       ST_SetSRID(ST_MakePoint(v.lon, v.lat), 4326), NOW()
  FROM organizaciones o
  CROSS JOIN (VALUES
      ('ABC-123', 'BASICA',     -12.0461, -77.0428),
      ('DEF-456', 'INTERMEDIA', -12.0530, -77.0090),
      ('GHI-789', 'UCI',        -12.0875, -77.0345),
      ('JKL-012', 'BASICA',     -12.1210, -77.0297),
      ('MNO-345', 'INTERMEDIA', -12.0210, -76.9930)
  ) AS v(placa, tipo, lat, lon)
  WHERE o.ruc = '20512345678'
ON CONFLICT (placa) DO NOTHING;
