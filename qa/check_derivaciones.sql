-- ============================================================================
-- SALUD CERCA - qa/check_derivaciones.sql
-- ----------------------------------------------------------------------------
-- Control de calidad del MOTOR DE DERIVACIÓN INTELIGENTE.
-- Requiere haber aplicado db/init/07_derivacion.sql y un dataset regenerado
-- (data/generate_seed.py con destinos garantizados).
-- Cada bloque DO ... ASSERT aborta (ON_ERROR_STOP) si una validación falla.
-- ============================================================================

\set ON_ERROR_STOP on

-- ---------------------------------------------------------------------------
-- 1. Ninguna derivación SIN destino
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 1/7 - derivaciones sin destino';
  ASSERT (SELECT count(*) FROM atenciones_his
          WHERE estado_salida = 'DERIVADO'
            AND (derivado_a IS NULL OR derivado_a = '')) = 0,
    'existen DERIVADO sin destino asignado (cadena de referencia rota)';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 2. Ninguna derivación a un código inexistente
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 2/7 - destino inexistente';
  ASSERT (SELECT count(*) FROM atenciones_his a
          WHERE a.estado_salida = 'DERIVADO'
            AND a.derivado_a <> ''
            AND NOT EXISTS (SELECT 1 FROM ipress i WHERE i.codigo_renipress = a.derivado_a)) = 0,
    'existen derivaciones a códigos RENIPRESS inexistentes';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 3. Ninguna derivación a una IPRESS NO ACTIVA
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 3/7 - destino no activo';
  ASSERT (SELECT count(*) FROM atenciones_his a
          JOIN ipress d ON d.codigo_renipress = a.derivado_a
          WHERE a.estado_salida = 'DERIVADO' AND d.estado_operativo <> 'ACTIVO') = 0,
    'existen derivaciones a IPRESS INACTIVO/REFERENCIAL';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 4. Ninguna derivación hacia un nivel menor que el del origen
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 4/7 - nivel regresivo';
  ASSERT (SELECT count(*) FROM atenciones_his a
          JOIN ipress io ON io.codigo_renipress = a.codigo_ipress
          JOIN ipress id ON id.codigo_renipress = a.derivado_a
          JOIN categorizaciones co ON co.id = io.categoria_id
          JOIN categorizaciones cd ON cd.id = id.categoria_id
          WHERE a.estado_salida = 'DERIVADO'
            AND cd.nivel_atencion < co.nivel_atencion) = 0,
    'existen derivaciones a establecimientos de MENOR nivel que el origen';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 5. El motor retorna candidatos válidos y ordenados (caso real)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  v_origen VARCHAR(12);
  v_esp    INTEGER;
  v_n_min  INTEGER;
  v_n_orig INTEGER;
  v_prev   NUMERIC;
  v_ok     BOOLEAN := TRUE;
  v_row    RECORD;
BEGIN
  RAISE NOTICE 'CHECK 5/7 - recomendar_derivacion (candidatos validos y ordenados)';

  DROP TABLE IF EXISTS _qa_recomendacion;
  CREATE TEMP TABLE _qa_recomendacion AS
  SELECT r.codigo_renipress, r.nivel_atencion, r.score
    FROM recomendar_derivacion(
        (SELECT codigo_renipress FROM ipress
          WHERE estado_operativo = 'ACTIVO' ORDER BY id LIMIT 1),
        (SELECT id FROM especialidades ORDER BY id LIMIT 1),
        DATE '2024-12-31', 10) r;

  SELECT codigo_renipress INTO v_origen FROM ipress
   WHERE estado_operativo = 'ACTIVO' ORDER BY id LIMIT 1;
  SELECT id INTO v_esp FROM especialidades ORDER BY id LIMIT 1;

  ASSERT (SELECT count(*) FROM _qa_recomendacion) > 0,
    'el motor no retornó candidatos para un caso válido';

  ASSERT (SELECT count(*) FROM _qa_recomendacion r
          JOIN ipress i ON i.codigo_renipress = r.codigo_renipress
          WHERE i.estado_operativo <> 'ACTIVO') = 0,
    'el motor retornó un destino NO ACTIVO';

  ASSERT (SELECT count(*) FROM _qa_recomendacion
          WHERE codigo_renipress = v_origen) = 0,
    'el motor retornó el propio origen como destino';

  SELECT nivel_atencion INTO v_n_orig FROM ipress i
    JOIN categorizaciones c ON c.id = i.categoria_id
   WHERE i.codigo_renipress = v_origen;
  SELECT GREATEST(v_n_orig, COALESCE(e.complejidad_minima, 1)) INTO v_n_min
    FROM especialidades e WHERE e.id = v_esp;

  ASSERT (SELECT count(*) FROM _qa_recomendacion
          WHERE nivel_atencion < v_n_min) = 0,
    'el motor retornó candidatos por debajo del nivel requerido';

  v_prev := NULL;
  FOR v_row IN SELECT score FROM _qa_recomendacion ORDER BY score DESC LOOP
    IF v_prev IS NOT NULL AND v_row.score > v_prev THEN
      v_ok := FALSE;
    END IF;
    v_prev := v_row.score;
  END LOOP;
  ASSERT v_ok, 'los candidatos no están ordenados por score descendente';

  DROP TABLE IF EXISTS _qa_recomendacion;
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 6. El motor funciona sin especialidad (fallback al nivel del origen)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  v_origen VARCHAR(12);
BEGIN
  RAISE NOTICE 'CHECK 6/7 - recomendar_derivacion sin especialidad';

  SELECT codigo_renipress INTO v_origen FROM ipress
   WHERE estado_operativo = 'ACTIVO' ORDER BY id LIMIT 1;

  ASSERT (SELECT count(*) FROM recomendar_derivacion(v_origen, NULL, DATE '2024-12-31', 5)) > 0,
    'el motor no retornó candidatos con especialidad NULL';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 7. Vistas de diagnóstico responden con datos
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 7/7 - vistas de diagnóstico';
  ASSERT (SELECT count(*) FROM vw_derivaciones_resumen) > 0,
    'vw_derivaciones_resumen vacía';
  ASSERT (SELECT count(*) FROM vw_derivaciones_sin_destino) = 0,
    'vw_derivaciones_sin_destino no está vacía';
  ASSERT (SELECT count(*) FROM vw_cuellos_de_botella) > 0,
    'vw_cuellos_de_botella vacía';
  RAISE NOTICE '  OK';
END $$;

-- ============================================================================
SELECT 'QA DERIVACIONES OK: la red de referencias está sana y el motor responde'
       AS resultado;
