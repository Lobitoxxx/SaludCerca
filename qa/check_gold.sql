-- ============================================================================
-- SALUD CERCA - qa/check_gold.sql
-- ----------------------------------------------------------------------------
-- Suite de control de calidad de la capa Gold (PostgreSQL/PostGIS/pgvector).
-- Cada bloque DO ... ASSERT aborta con ON_ERROR_STOP si una validación falla.
--   Ejecución:  psql -U saludcerca -d saludcerca -v ON_ERROR_STOP=1 -f check_gold.sql
-- ============================================================================

\set ON_ERROR_STOP on

-- ---------------------------------------------------------------------------
-- 1. Conteos esperados del batch 2024
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 1/10 - conteos esperados';
  ASSERT (SELECT count(*) FROM ipress) = 1844,
    'ipress debería tener 1844 filas';
  ASSERT (SELECT count(*) FROM atenciones_his) = 349887,
    'atenciones_his debería tener 349887 filas (350000 - 113 duplicadas)';
  ASSERT (SELECT count(*) FROM dim_ipress) = 1844,
    'dim_ipress debería tener 1844 filas';
  ASSERT (SELECT count(*) FROM dim_tiempo) = 366,
    'dim_tiempo debería cubrir 366 días (2024 bisiesto)';
  ASSERT (SELECT count(*) FROM especialidades) = 16,
    'especialidades debería tener 16 filas';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 2. Unicidad de claves naturales
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 2/10 - claves únicas';
  ASSERT (SELECT count(*) - count(DISTINCT codigo_renipress) FROM ipress) = 0,
    'ipress.codigo_renipress no es único';
  ASSERT (SELECT count(*) - count(DISTINCT ipress_key) FROM dim_ipress) = 0,
    'dim_ipress.ipress_key no es único';
  ASSERT (SELECT count(*) - count(DISTINCT ubigeo_key) FROM dim_ubigeo) = 0,
    'dim_ubigeo.ubigeo_key no es único';
  ASSERT (SELECT count(*) - count(DISTINCT (ipress_key, tiempo_key)) FROM fact_atenciones_medicas) = 0,
    'fact_atenciones_medicas tiene duplicados (ipress_key, tiempo_key)';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 3. Integridad referencial (fact -> dimensiones)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 3/10 - integridad referencial del fact';
  ASSERT (SELECT count(*) FROM fact_atenciones_medicas f
          WHERE NOT EXISTS (SELECT 1 FROM dim_ipress d WHERE d.ipress_key = f.ipress_key)) = 0,
    'fact con ipress_key huérfano';
  ASSERT (SELECT count(*) FROM fact_atenciones_medicas f
          WHERE NOT EXISTS (SELECT 1 FROM dim_tiempo t WHERE t.tiempo_key = f.tiempo_key)) = 0,
    'fact con tiempo_key huérfano';
  ASSERT (SELECT count(*) FROM fact_atenciones_medicas f
          WHERE NOT EXISTS (SELECT 1 FROM dim_ubigeo u WHERE u.ubigeo_key = f.ubigeo_key)) = 0,
    'fact con ubigeo_key huérfano';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 4. Integridad referencial (transaccional -> maestros)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 4/10 - integridad referencial transaccional';
  ASSERT (SELECT count(*) FROM atenciones_his a
          WHERE NOT EXISTS (SELECT 1 FROM ubigeo u WHERE u.codigo_ubigeo = a.codigo_ubigeo)) = 0,
    'atenciones_his con codigo_ubigeo inexistente';
  ASSERT (SELECT count(*) FROM atenciones_his a
          WHERE NOT EXISTS (SELECT 1 FROM ipress i WHERE i.codigo_renipress = a.codigo_ipress)) = 0,
    'atenciones_his con codigo_ipress inexistente en RENIPRESS';
  ASSERT (SELECT count(*) FROM ipress i
          WHERE NOT EXISTS (SELECT 1 FROM ubigeo u WHERE u.id = i.ubigeo_id)) = 0,
    'ipress con ubigeo_id inexistente';
  ASSERT (SELECT count(*) FROM atenciones_his a
          WHERE NOT EXISTS (SELECT 1 FROM especialidades e WHERE e.id = a.especialidad_id)) = 0,
    'atenciones_his con especialidad inexistente';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 5. Ausencia de nulos en columnas críticas
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 5/10 - nulos en columnas críticas';
  ASSERT (SELECT count(*) FROM ipress WHERE geom IS NULL) = 0,
    'ipress con geom NULL (geocoding falló)';
  ASSERT (SELECT count(*) FROM ipress WHERE descripcion_emb IS NULL) = 0,
    'ipress con descripcion_emb NULL';
  ASSERT (SELECT count(*) FROM ipress WHERE latitud IS NULL OR longitud IS NULL) = 0,
    'ipress con coordenadas NULL';
  ASSERT (SELECT count(*) FROM ubigeo WHERE geom_centroide IS NULL) = 0,
    'ubigeo con geom_centroide NULL';
  ASSERT (SELECT count(*) FROM especialidades WHERE descripcion_emb IS NULL) = 0,
    'especialidades con descripcion_emb NULL';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 6. Rangos temporales del batch 2024
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 6/10 - rango temporal 2024';
  ASSERT (SELECT count(*) FROM atenciones_his
          WHERE fecha_atencion < DATE '2024-01-01'
             OR fecha_atencion > DATE '2024-12-31') = 0,
    'atenciones fuera del año 2024';
  ASSERT (SELECT count(*) FROM fact_atenciones_medicas f
          WHERE NOT EXISTS (SELECT 1 FROM dim_tiempo t
                            WHERE t.tiempo_key = f.tiempo_key AND t.anio = 2024)) = 0,
    'fact con tiempos fuera de 2024';
  ASSERT (SELECT count(*) FROM dim_tiempo WHERE anio <> 2024) = 0,
    'dim_tiempo fuera del año 2024';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 7. Rangos de métricas (saturación y volúmenes)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 7/10 - rangos de métricas';
  ASSERT (SELECT count(*) FROM fact_atenciones_medicas
          WHERE tasa_saturacion < 0 OR tasa_saturacion > 100) = 0,
    'tasa_saturacion fuera de [0, 100]';
  ASSERT (SELECT count(*) FROM fact_atenciones_medicas WHERE num_atenciones <= 0) = 0,
    'num_atenciones debe ser positivo';
  ASSERT (SELECT count(*) FROM fact_atenciones_medicas
          WHERE num_emergencias > num_atenciones) = 0,
    'num_emergencias no puede superar num_atenciones';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 8. Particionado mensual de atenciones_his
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 8/10 - particionado mensual';
  ASSERT (SELECT count(*) FROM pg_inherits i
          WHERE i.inhparent = 'atenciones_his'::regclass) = 12,
    'atenciones_his debería tener 12 particiones mensuales';
  ASSERT (SELECT count(*) FROM (
            SELECT date_trunc('month', fecha_atencion)::date AS mes
            FROM atenciones_his GROUP BY 1) s) = 12,
    'debería haber datos en los 12 meses de 2024';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 9. Embeddings pgvector operativos (384 dimensiones)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 9/10 - embeddings pgvector';
  ASSERT (SELECT count(*) FROM ipress WHERE vector_dims(descripcion_emb) <> 384) = 0,
    'descripcion_emb debe ser vector(384)';
  ASSERT (SELECT count(*) FROM especialidades WHERE vector_dims(descripcion_emb) <> 384) = 0,
    'descripcion_emb de especialidades debe ser vector(384)';
  ASSERT (SELECT count(*) FROM pg_indexes
          WHERE indexname = 'idx_ipress_emb' AND indexdef LIKE '%hnsw%') = 1,
    'falta el índice HNSW idx_ipress_emb';
  RAISE NOTICE '  OK';
END $$;

-- ---------------------------------------------------------------------------
-- 10. Vistas OLAP responden con datos
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  RAISE NOTICE 'CHECK 10/10 - vistas OLAP';
  ASSERT (SELECT count(*) FROM vw_cobertura_regional) >= 24,
    'vw_cobertura_regional debería cubrir ~25 departamentos';
  ASSERT (SELECT count(*) FROM vw_atenciones_mensual) > 0,
    'vw_atenciones_mensual vacía';
  ASSERT (SELECT count(*) FROM vw_saturacion_ipress) > 0,
    'vw_saturacion_ipress vacía';
  ASSERT (SELECT count(*) FROM vw_brechas_cobertura) > 0,
    'vw_brechas_cobertura vacía';
  RAISE NOTICE '  OK';
END $$;

-- ============================================================================
-- Si llegaste hasta aquí: TODAS las validaciones pasaron.
-- ============================================================================
SELECT 'QA OK: todas las validaciones de la capa Gold pasaron' AS resultado;
