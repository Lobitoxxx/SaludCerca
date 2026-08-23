-- ============================================================================
-- SALUD CERCA - 09. Motor de enriquecimiento de datos + red de contribuidores
-- ----------------------------------------------------------------------------
-- Soporte del módulo M6 (docs/PRODUCTO.md):
--
--   * fuentes_datos           -> catálogo de fuentes oficiales/minadas con última sync
--   * contribuidores          -> red humana pagada, reputación y saldo
--   * tareas_verificacion     -> cola de verificaciones geo-asignadas por IPRESS
--   * reportes_contribucion   -> submissions con validación y procedencia
--   * pagos_contribuidor      -> liquidaciones Yape/Plin/Culqi/transferencia
--   * validar_reporte()       -> aprueba/rechaza un reporte actualizando reputación,
--                                tarea y hospital_capacidad_rt si aplica
--
-- Regla económica: el pago solo se genera al VALIDAR; datos críticos exigen
-- doble validación o cross-check contra canal OFICIAL (ver docs/PRODUCTO.md §4.3).
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 9.1 Catálogo de fuentes de datos
-- ---------------------------------------------------------------------------
CREATE TABLE fuentes_datos (
    id            SERIAL PRIMARY KEY,
    nombre        VARCHAR(120) UNIQUE NOT NULL,
    url           VARCHAR(400),
    canal         VARCHAR(15) NOT NULL
                  CHECK (canal IN ('OFICIAL', 'MINADO', 'CONTRIBUIDORES')),
    frecuencia    VARCHAR(20) NOT NULL DEFAULT 'MENSUAL'
                  CHECK (frecuencia IN ('TIEMPO_REAL', 'DIARIA', 'SEMANAL', 'MENSUAL', 'ANUAL', 'PUNTUAL')),
    formato       VARCHAR(20) DEFAULT 'CSV',
    ultima_sync   TIMESTAMPTZ,
    activa        BOOLEAN NOT NULL DEFAULT TRUE,
    notas         TEXT
);

COMMENT ON TABLE fuentes_datos IS 'Catálogo del motor M6: qué fuente alimenta el sistema y cuándo se sincronizó por última vez.';

INSERT INTO fuentes_datos (nombre, url, canal, frecuencia, formato, notas) VALUES
('RENIPRESS_SUSALUD', 'https://www.datosabiertos.gob.pe/dataset/minsa-ipress', 'OFICIAL', 'MENSUAL', 'CSV',
 '~35.000 IPRESS reales; base maestra de establecimientos.'),
('SUSALUD_RECURSOS_IPRESS', 'http://datos.susalud.gob.pe/', 'OFICIAL', 'MENSUAL', 'CSV',
 'Consultorios físicos/funcionales y N° de ambulancias por IPRESS.'),
('SUSALUD_F500_2', 'http://datos.susalud.gob.pe/', 'OFICIAL', 'MENSUAL', 'CSV',
 'Histórico disponibilidad camas UCI/hospitalización.'),
('INEI_POBLACION_DISTRITO', 'https://www.inei.gob.pe/', 'OFICIAL', 'ANUAL', 'CSV',
 'Proyecciones poblacionales 1.874 distritos; índice cobertura/10k hab.'),
('HIS_MINSA_ATENCIONES', 'https://www.datosabiertos.gob.pe/group/ministerio-de-salud-minsa', 'OFICIAL', 'MENSUAL', 'CSV',
 'Atenciones reales por establecimiento (reemplaza dataset sintético).'),
('OSM_OVERPASS_PERU', 'https://overpass-api.de/api/interpreter', 'MINADO', 'SEMANAL', 'JSON',
 'POIs salud amenity=hospital|clinic|doctors|pharmacy con coords/tel/horarios.'),
('GOOGLE_PLACES_TOP500', 'https://developers.google.com/maps/documentation/places', 'MINADO', 'MENSUAL', 'JSON',
 'Metadata premium solo para top-500 hospitales (control de costo).')
ON CONFLICT (nombre) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 9.2 Contribuidores (perfil sobre usuarios_app rol=CONTRIBUIDOR)
-- ---------------------------------------------------------------------------
CREATE TABLE contribuidores (
    id                    SERIAL PRIMARY KEY,
    usuario_id            INTEGER UNIQUE REFERENCES usuarios_app(id),
    alias                 VARCHAR(60) UNIQUE NOT NULL,
    nivel                 VARCHAR(10) NOT NULL DEFAULT 'BRONCE'
                          CHECK (nivel IN ('BRONCE', 'PLATA', 'ORO', 'DIAMANTE')),
    reputacion            NUMERIC(5,2) NOT NULL DEFAULT 50.0
                          CHECK (reputacion BETWEEN 0 AND 100),
    zona_base_lat         DOUBLE PRECISION,
    zona_base_lon         DOUBLE PRECISION,
    total_reportes        INTEGER NOT NULL DEFAULT 0,
    reportes_validados    INTEGER NOT NULL DEFAULT 0,
    reportes_rechazados   INTEGER NOT NULL DEFAULT 0,
    saldo_pendiente       NUMERIC(8,2) NOT NULL DEFAULT 0 CHECK (saldo_pendiente >= 0),
    ganancias_total       NUMERIC(10,2) NOT NULL DEFAULT 0,
    telefono_pago         VARCHAR(30),              -- Yape/Plin destino
    metodo_pago_preferido VARCHAR(15) DEFAULT 'YAPE'
                          CHECK (metodo_pago_preferido IN ('YAPE', 'PLIN', 'CULQI', 'TRANSFERENCIA')),
    activo                BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE contribuidores IS 'Red humana verificadora. Reputación 50=base; <20 expulsión; peso del voto escala con nivel.';
CREATE INDEX idx_contribuidores_zona ON contribuidores(zona_base_lat, zona_base_lon);

-- ---------------------------------------------------------------------------
-- 9.3 Cola de tareas de verificación (geo-asignadas)
-- ---------------------------------------------------------------------------
CREATE TABLE tareas_verificacion (
    id             BIGSERIAL PRIMARY KEY,
    ipress_id      INTEGER NOT NULL REFERENCES ipress(id),
    tipo           VARCHAR(25) NOT NULL
                   CHECK (tipo IN ('VERIFICAR_ESTADO', 'CAPACIDAD_CAMAS', 'URGENCIA_ESTADO',
                                   'HORARIO', 'TELEFONO', 'AUDITORIA_COMPLETA',
                                   'CONFIRMAR_CIERRE')),
    prioridad      SMALLINT NOT NULL DEFAULT 5 CHECK (prioridad BETWEEN 1 AND 10),
    estado         VARCHAR(12) NOT NULL DEFAULT 'PENDIENTE'
                   CHECK (estado IN ('PENDIENTE', 'ASIGNADA', 'REPORTADA',
                                     'VALIDADA', 'EXPIRADA')),
    latitud        DOUBLE PRECISION NOT NULL,
    longitud       DOUBLE PRECISION NOT NULL,
    geom           GEOMETRY(Point, 4326) GENERATED ALWAYS AS
                   (ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)) STORED,
    recompensa     NUMERIC(6,2) NOT NULL DEFAULT 3.00 CHECK (recompensa >= 0),
    asignada_a     INTEGER REFERENCES contribuidores(id),
    asignada_en    TIMESTAMPTZ,
    expira_en      TIMESTAMPTZ,
    creada_en      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE tareas_verificacion IS 'Cola Waze-salud: verificaciones pendientes ordenables por cercanía (KNN geom) y prioridad.';
CREATE INDEX idx_tareas_geom ON tareas_verificacion USING GIST (geom);
CREATE INDEX idx_tareas_estado_prioridad ON tareas_verificacion(estado, prioridad DESC);

-- ---------------------------------------------------------------------------
-- 9.4 Reportes de contribución
-- ---------------------------------------------------------------------------
CREATE TABLE reportes_contribucion (
    id               BIGSERIAL PRIMARY KEY,
    tarea_id         BIGINT REFERENCES tareas_verificacion(id),
    contribuidor_id  INTEGER NOT NULL REFERENCES contribuidores(id),
    ipress_id        INTEGER NOT NULL REFERENCES ipress(id),
    campo_reportado  VARCHAR(30) NOT NULL
                     CHECK (campo_reportado IN ('ESTADO_OPERATIVO', 'CAMAS_UCI',
                                                'CAMAS_HOSPITALIZACION', 'URGENCIA_ESTADO',
                                                'HORARIO', 'TELEFONO', 'OTRO')),
    valor_anterior   TEXT,
    valor_nuevo      TEXT NOT NULL,
    evidencia_url    TEXT,                            -- foto/nota opcional
    latitud_reporte  DOUBLE PRECISION,                -- geofence: debe caer cerca de la IPRESS
    longitud_reporte DOUBLE PRECISION,
    enviado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    validacion       VARCHAR(10) NOT NULL DEFAULT 'PENDIENTE'
                     CHECK (validacion IN ('PENDIENTE', 'APROBADO', 'RECHAZADO')),
    validado_por     INTEGER REFERENCES contribuidores(id),
    validado_en      TIMESTAMPTZ,
    puntos_ganados   SMALLINT NOT NULL DEFAULT 0,
    comentario_validador TEXT
);

COMMENT ON TABLE reportes_contribucion IS 'Submissions crudos. Aprobado => dato a Gold/hospital_capacidad_rt con procedencia CONTRIBUIDOR.';
CREATE INDEX idx_reportes_validacion ON reportes_contribucion(validacion);
CREATE INDEX idx_reportes_ipress ON reportes_contribucion(ipress_id, enviado_en DESC);

-- ---------------------------------------------------------------------------
-- 9.5 Pagos a contribuidores
-- ---------------------------------------------------------------------------
CREATE TABLE pagos_contribuidor (
    id              BIGSERIAL PRIMARY KEY,
    contribuidor_id INTEGER NOT NULL REFERENCES contribuidores(id),
    monto           NUMERIC(8,2) NOT NULL CHECK (monto > 0),
    metodo          VARCHAR(15) NOT NULL
                    CHECK (metodo IN ('YAPE', 'PLIN', 'CULQI', 'TRANSFERENCIA')),
    estado          VARCHAR(10) NOT NULL DEFAULT 'PENDIENTE'
                    CHECK (estado IN ('PENDIENTE', 'PAGADO', 'FALLIDO')),
    referencia_externa VARCHAR(80),
    solicitado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pagado_en       TIMESTAMPTZ
);

COMMENT ON TABLE pagos_contribuidor IS 'Liquidaciones semanales del fondo de datos (15% del MRR).';
CREATE INDEX idx_pagos_estado ON pagos_contribuidor(contribuidor_id, estado);

-- ---------------------------------------------------------------------------
-- 9.6 FUNCIÓN: validar_reporte(p_reporte, p_validador, p_aprobado)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION validar_reporte(
    IN p_reporte_id    BIGINT,
    IN p_validador_id  INTEGER,
    IN p_aprobado      BOOLEAN,
    IN p_comentario    TEXT DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    v_rep        RECORD;
    v_recompensa NUMERIC := 0;
BEGIN
    SELECT * INTO v_rep FROM reportes_contribucion WHERE id = p_reporte_id FOR UPDATE;

    IF v_rep.id IS NULL THEN
        RAISE EXCEPTION 'Reporte % no existe', p_reporte_id;
    END IF;
    IF v_rep.validacion <> 'PENDIENTE' THEN
        RAISE EXCEPTION 'Reporte % ya fue %', p_reporte_id, v_rep.validacion;
    END IF;

    UPDATE reportes_contribucion
       SET validacion = CASE WHEN p_aprobado THEN 'APROBADO' ELSE 'RECHAZADO' END,
           validado_por = p_validador_id,
           validado_en = NOW(),
           puntos_ganados = CASE WHEN p_aprobado THEN 5 ELSE -10 END,
           comentario_validador = p_comentario
     WHERE id = p_reporte_id;

    UPDATE contribuidores
       SET reputacion = LEAST(100, GREATEST(0,
               reputacion + CASE WHEN p_aprobado THEN 5 ELSE -10 END)),
           nivel = CASE
                     WHEN reputacion + (CASE WHEN p_aprobado THEN 5 ELSE -10 END) >= 90 THEN 'DIAMANTE'
                     WHEN reputacion + (CASE WHEN p_aprobado THEN 5 ELSE -10 END) >= 70 THEN 'ORO'
                     WHEN reputacion + (CASE WHEN p_aprobado THEN 5 ELSE -10 END) >= 40 THEN 'PLATA'
                     ELSE 'BRONCE' END,
           total_reportes = total_reportes + 1,
           reportes_validados  = reportes_validados + CASE WHEN p_aprobado THEN 1 ELSE 0 END,
           reportes_rechazados = reportes_rechazados + CASE WHEN p_aprobado THEN 0 ELSE 1 END,
           activo = GREATEST(reputacion + (CASE WHEN p_aprobado THEN 5 ELSE -10 END), 0) > 20
     WHERE id = v_rep.contribuidor_id;

    IF p_aprobado THEN
        -- Recompensa según tarea (si el reporte responde a una tarea)
        SELECT t.recompensa INTO v_recompensa
          FROM tareas_verificacion t WHERE t.id = v_rep.tarea_id;

        UPDATE contribuidores
           SET saldo_pendiente = saldo_pendiente + COALESCE(v_recompensa, 2.00),
               ganancias_total = ganancias_total + COALESCE(v_recompensa, 2.00)
         WHERE id = v_rep.contribuidor_id;

        IF v_rep.tarea_id IS NOT NULL THEN
            UPDATE tareas_verificacion SET estado = 'VALIDADA' WHERE id = v_rep.tarea_id;
        END IF;

        -- Si el reporte toca capacidad crítica, refresca la capa RT (procedencia CONTRIBUIDOR)
        IF v_rep.campo_reportado IN ('CAMAS_UCI', 'CAMAS_HOSPITALIZACION', 'URGENCIA_ESTADO') THEN
            INSERT INTO hospital_capacidad_rt
                (ipress_id, camas_uci_disponibles, camas_hosp_disponibles,
                 urgencia_estado, actualizado_por, vigente_hasta)
            VALUES (v_rep.ipress_id,
                    CASE WHEN v_rep.campo_reportado = 'CAMAS_UCI'
                         THEN v_rep.valor_nuevo::SMALLINT END,
                    CASE WHEN v_rep.campo_reportado = 'CAMAS_HOSPITALIZACION'
                         THEN v_rep.valor_nuevo::SMALLINT END,
                    CASE WHEN v_rep.campo_reportado = 'URGENCIA_ESTADO'
                         THEN v_rep.valor_nuevo::VARCHAR ELSE 'NORMAL' END,
                    'CONTRIBUIDOR', NOW() + INTERVAL '4 hours');
        END IF;
    END IF;
END;
$$;

COMMENT ON FUNCTION validar_reporte(BIGINT, INTEGER, BOOLEAN, TEXT) IS
    'Aprueba/rechaza un reporte: ajusta reputación/nivel/expulsión, acredita saldo si aprobado, cierra tarea y empuja datos críticos a hospital_capacidad_rt.';

-- ---------------------------------------------------------------------------
-- 9.7 Seed demo: 2 tareas de ejemplo sobre Lima
-- ---------------------------------------------------------------------------
INSERT INTO tareas_verificacion (ipress_id, tipo, prioridad, latitud, longitud, recompensa, expira_en)
SELECT i.id, 'CAPACIDAD_CAMAS', 8, i.latitud, i.longitud, 5.00, NOW() + INTERVAL '7 days'
  FROM ipress i
 WHERE i.departamento = 'LIMA' AND i.estado_operativo = 'ACTIVO' AND i.geom IS NOT NULL
 ORDER BY ST_Distance(i.geom::geography,
                      ST_SetSRID(ST_MakePoint(-77.0428, -12.0461), 4326)::geography)
 LIMIT 3;
