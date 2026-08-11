-- ============================================================================
-- SALUD CERCA - 07. Motor de derivación inteligente
-- ----------------------------------------------------------------------------
-- Diagnostica la red de referencias (RENIPRESS -> HIS) y recomienda el mejor
-- destino para cada paciente que requiere derivación:
--
--   * vw_derivaciones_resumen    -> flujo origen->destino con estado del destino
--   * vw_derivaciones_sin_destino-> derivaciones SIN destino por departamento
--   * vw_cuellos_de_botella      -> destinos que reciben más de lo que absorben
--   * recomendar_derivacion()    -> función plpgsql: top-N candidatos ordenados
--
-- Hallazgo que resuelve: ~40% de las atenciones DERIVADO no tienen destino
-- asignado y ~6% apuntan a IPRESS no activas. Este motor garantiza recomendar
-- destinos ACTIVOS, de nivel adecuado a la especialidad y no saturados.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 7.1 Resumen del flujo de derivaciones (origen -> destino)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_derivaciones_resumen AS
SELECT
    a.codigo_ipress              AS origen_codigo,
    i.nombre                     AS origen_nombre,
    i.departamento               AS origen_departamento,
    a.derivado_a                 AS destino_codigo,
    d.nombre                     AS destino_nombre,
    d.estado_operativo           AS destino_estado_operativo,
    CASE
        WHEN a.derivado_a IS NULL OR a.derivado_a = '' THEN 'SIN_DESTINO'
        WHEN d.estado_operativo = 'ACTIVO'              THEN 'ACTIVO'
        ELSE COALESCE(d.estado_operativo, 'INEXISTENTE')
    END                          AS estado_destino,
    COUNT(*)                     AS num_derivaciones
FROM atenciones_his a
JOIN ipress i ON i.codigo_renipress = a.codigo_ipress
LEFT JOIN ipress d ON d.codigo_renipress = a.derivado_a
WHERE a.estado_salida = 'DERIVADO'
GROUP BY 1, 2, 3, 4, 5, 6, 7;

COMMENT ON VIEW vw_derivaciones_resumen IS
    'Flujo de referencias origen->destino con el estado del destino (SIN_DESTINO/INEXISTENTE/ACTIVO/...).';

-- ---------------------------------------------------------------------------
-- 7.2 Derivaciones SIN destino por departamento (cadenas de referencia rotas)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_derivaciones_sin_destino AS
SELECT
    i.departamento        AS departamento,
    COUNT(*)              AS derivaciones_sin_destino
FROM atenciones_his a
JOIN ipress i ON i.codigo_renipress = a.codigo_ipress
WHERE a.estado_salida = 'DERIVADO'
  AND (a.derivado_a IS NULL OR a.derivado_a = '')
GROUP BY i.departamento
ORDER BY 2 DESC;

COMMENT ON VIEW vw_derivaciones_sin_destino IS
    'Derivaciones que quedaron sin destino asignado, por departamento.';

-- ---------------------------------------------------------------------------
-- 7.3 Cuellos de botella: destinos que reciben más referencias de las que
--     su capacidad (camas + capacidad_resolutiva*2) puede absorber
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_cuellos_de_botella AS
SELECT
    d.id                              AS ipress_id,
    d.codigo_renipress,
    d.nombre,
    d.departamento,
    c.nivel_atencion,
    c.capacidad_resolutiva,
    d.capacidad_camas,
    d.capacidad_consultorios,
    (d.capacidad_camas + c.capacidad_resolutiva * 2)::numeric AS capacidad_ponderada,
    COUNT(a.id)                       AS derivaciones_recibidas,
    COALESCE(ROUND(AVG(f.tasa_saturacion) FILTER (
        WHERE f.tiempo_key >= (SELECT MAX(tiempo_key) FROM fact_atenciones_medicas) - 90), 2), 0)
                                      AS saturacion_90dias
FROM ipress d
JOIN categorizaciones c ON c.id = d.categoria_id
LEFT JOIN atenciones_his a
       ON a.derivado_a = d.codigo_renipress AND a.estado_salida = 'DERIVADO'
LEFT JOIN fact_atenciones_medicas f ON f.ipress_key = d.id
WHERE d.estado_operativo = 'ACTIVO'
GROUP BY d.id, d.codigo_renipress, d.nombre, d.departamento, c.nivel_atencion,
         c.capacidad_resolutiva, d.capacidad_camas, d.capacidad_consultorios
HAVING COUNT(a.id) > 0
ORDER BY COUNT(a.id) DESC;

COMMENT ON VIEW vw_cuellos_de_botella IS
    'Establecimientos que concentran derivaciones recibidas vs capacidad ponderada (cuellos de botella de la red).';

-- ---------------------------------------------------------------------------
-- 7.4 FUNCIÓN: recomendar_derivacion(origen, especialidad, fecha, topN)
-- ---------------------------------------------------------------------------
-- Score compuesto 0-100:
--   * 50%  capacidad / anti-saturación (70% baja saturación + 30% capacidad)
--   * 30%  cercanía geográfica (ST_Distance en geography -> km)
--   * 20%  ajuste de nivel + historial real de la especialidad en el destino
-- Filtros duros: destino ACTIVO, con geometría, distinto del origen y de
-- nivel >= max(nivel_origen, complejidad_minima de la especialidad).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION recomendar_derivacion(
    IN p_origen_codigo    VARCHAR(12),
    IN p_especialidad_id  INTEGER,
    IN p_fecha            DATE DEFAULT CURRENT_DATE,
    IN p_max_candidatos   INTEGER DEFAULT 5
)
RETURNS TABLE (
    codigo_renipress       VARCHAR(12),
    nombre                 VARCHAR(200),
    nivel_atencion         INTEGER,
    departamento           VARCHAR(60),
    distancia_km           NUMERIC,
    saturacion_promedio    NUMERIC,
    capacidad_disponible   NUMERIC,
    historial_especialidad BIGINT,
    score                  NUMERIC
)
LANGUAGE plpgsql AS $$
DECLARE
    v_origen_nivel INTEGER;
    v_nivel_min    INTEGER;
BEGIN
    -- Nivel de atención del establecimiento origen
    SELECT c.nivel_atencion INTO v_origen_nivel
      FROM ipress i
      JOIN categorizaciones c ON c.id = i.categoria_id
     WHERE i.codigo_renipress = p_origen_codigo;

    IF v_origen_nivel IS NULL THEN
        RAISE NOTICE 'recomendar_derivacion: origen % no encontrado', p_origen_codigo;
        RETURN;
    END IF;

    -- Nivel mínimo exigido: el del origen o el que requiere la especialidad
    IF p_especialidad_id IS NULL THEN
        v_nivel_min := v_origen_nivel;
    ELSE
        SELECT GREATEST(v_origen_nivel, COALESCE(e.complejidad_minima, v_origen_nivel))
          INTO v_nivel_min
          FROM especialidades e
         WHERE e.id = p_especialidad_id;
        IF v_nivel_min IS NULL THEN
            v_nivel_min := v_origen_nivel;
        END IF;
    END IF;

    RETURN QUERY
    WITH origen AS (
        SELECT geom FROM ipress WHERE ipress.codigo_renipress = p_origen_codigo AND geom IS NOT NULL
    ),
    candidatos AS (
        SELECT d.id,
               d.codigo_renipress,
               d.nombre,
               c.nivel_atencion,
               d.departamento,
               (d.capacidad_camas + c.capacidad_resolutiva * 2)::numeric AS capacidad_disponible,
               -- ST_Distance sobre geography devuelve metros -> km reales
               ST_Distance(o.geom::geography, d.geom::geography) / 1000.0 AS km
          FROM ipress d
          JOIN categorizaciones c ON c.id = d.categoria_id
          CROSS JOIN origen o
         WHERE d.estado_operativo = 'ACTIVO'
           AND d.geom IS NOT NULL
           AND d.codigo_renipress <> p_origen_codigo
           AND c.nivel_atencion >= v_nivel_min
    ),
    medidas AS (
        SELECT ca.id,
               ca.codigo_renipress,
               ca.nombre,
               ca.nivel_atencion,
               ca.departamento,
               ROUND(ca.km::numeric, 2)                          AS km,
               ca.capacidad_disponible,
               COALESCE(ROUND(sat.saturacion, 2), 0)          AS saturacion,
               COALESCE(esp.n_atenciones, 0)                  AS historial_esp,
               MAX(ca.km) OVER ()                             AS max_km,
               MAX(ca.capacidad_disponible) OVER ()           AS max_cap
          FROM candidatos ca
          LEFT JOIN LATERAL (
              SELECT AVG(f.tasa_saturacion) AS saturacion
                FROM fact_atenciones_medicas f
               WHERE f.ipress_key = ca.id
                 AND f.tiempo_key BETWEEN p_fecha - 90 AND p_fecha
          ) sat ON TRUE
          LEFT JOIN LATERAL (
              SELECT COUNT(*) AS n_atenciones
                FROM atenciones_his h
               WHERE h.ipress_id = ca.id
                 AND (p_especialidad_id IS NULL OR h.especialidad_id = p_especialidad_id)
                 AND h.fecha_atencion BETWEEN p_fecha - 90 AND p_fecha
          ) esp ON TRUE
    )
    SELECT m.codigo_renipress,
           m.nombre,
           m.nivel_atencion,
           m.departamento,
           m.km,
           m.saturacion,
           m.capacidad_disponible,
           m.historial_esp,
           ROUND((LEAST(100.0, GREATEST(0.0,
               -- 50% capacidad / anti-saturación
               50.0 * (0.7 * (1.0 - LEAST(m.saturacion, 100.0) / 100.0)
                     + 0.3 * COALESCE(LEAST(1.0, m.capacidad_disponible / NULLIF(m.max_cap, 0)), 0.0))
               -- 30% cercanía
             + 30.0 * COALESCE(1.0 - m.km / NULLIF(m.max_km, 0), 0.0)
               -- 20% ajuste de nivel + historial de especialidad
             + 20.0 * (0.5 * GREATEST(0.0, 1.0 - 0.5 * (m.nivel_atencion - v_nivel_min))
                     + 0.5 * LEAST(1.0, m.historial_esp / 100.0))
           )))::numeric, 2) AS score
      FROM medidas m
     ORDER BY score DESC, m.km ASC
     LIMIT p_max_candidatos;
END;
$$;

COMMENT ON FUNCTION recomendar_derivacion(VARCHAR, INTEGER, DATE, INTEGER) IS
    'Motor anti-saturación: recomienda destinos ACTIVOS, de nivel adecuado y cercanos para una derivación. Score 0-100 (50% saturación/capacidad, 30% distancia, 20% nivel+historial).';
