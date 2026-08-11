-- ============================================================================
-- SALUD CERCA - 06. Carga de datos sintéticos (seed) + materialización OLAP
-- ----------------------------------------------------------------------------
-- Requiere haber ejecutado antes:  python data/generate_seed.py
-- (los CSV se montan automáticamente en /seed-data dentro del contenedor).
--
-- Flujo:
--   1. Crea las particiones mensuales de atenciones_his (año 2024)
--   2. COPY masivo de los CSV sintéticos (Catálogos -> Ubigeo -> IPRESS -> HIS)
--   3. Reconstrucción de geometrías espaciales (ST_SetSRID / ST_MakePoint)
--   4. Ajuste de secuencias (SERIAL)
--   5. Materialización del modelo dimensional en estrella (Capa Gold)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Particiones mensuales de atenciones_his (2024)
-- ---------------------------------------------------------------------------
DO $$
DECLARE v_mes DATE;
BEGIN
    FOR v_mes IN
        SELECT generate_series('2024-01-01'::date, '2024-12-01'::date, '1 month')
    LOOP
        PERFORM crear_particion_mensual(v_mes);
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- 2. Carga masiva (COPY) - formato CSV con cabecera
-- ---------------------------------------------------------------------------
\echo '>> Cargando categorizaciones...'
COPY categorizaciones (id, codigo, nombre, nivel_atencion, capacidad_resolutiva,
                       descripcion, descripcion_emb)
FROM '/seed-data/categorizaciones.csv' CSV HEADER;

\echo '>> Cargando especialidades...'
COPY especialidades (id, codigo, nombre, complejidad_minima, descripcion, descripcion_emb)
FROM '/seed-data/especialidades.csv' CSV HEADER;

\echo '>> Cargando ubigeo...'
COPY ubigeo (id, codigo_ubigeo, departamento, provincia, distrito,
             latitud_centroide, longitud_centroide)
FROM '/seed-data/ubigeo.csv' CSV HEADER;

\echo '>> Cargando IPRESS (RENIPRESS)...'
COPY ipress (id, codigo_renipress, nombre, categoria_id, ubigeo_id, direccion,
             departamento, provincia, distrito, latitud, longitud,
             estado_operativo, capacidad_camas, capacidad_consultorios, horario,
             tiene_ambulancia, telefono, propietario, descripcion_emb)
FROM '/seed-data/renipress.csv' CSV HEADER;

\echo '>> Cargando atenciones HIS-MINSA (masivo)...'
COPY atenciones_his (codigo_ipress, ipress_id, codigo_ubigeo, fecha_atencion,
                     especialidad_id, diagnostico_cie10, tipo_atencion,
                     edad_paciente, sexo, tiempo_espera_min, estado_salida, derivado_a)
FROM '/seed-data/his_atenciones.csv' CSV HEADER;

-- ---------------------------------------------------------------------------
-- 3. Reconstrucción de geometrías (PostGIS)
-- ---------------------------------------------------------------------------
\echo '>> Construyendo geometrías espaciales...'
UPDATE ubigeo
   SET geom_centroide = ST_SetSRID(ST_MakePoint(longitud_centroide, latitud_centroide), 4326)
 WHERE geom_centroide IS NULL;

UPDATE ipress
   SET geom = ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)
 WHERE geom IS NULL;

-- ---------------------------------------------------------------------------
-- 4. Ajuste de secuencias después de COPY explícito de ids
-- ---------------------------------------------------------------------------
SELECT setval('categorizaciones_id_seq',  (SELECT COALESCE(max(id), 1) FROM categorizaciones));
SELECT setval('especialidades_id_seq',    (SELECT COALESCE(max(id), 1) FROM especialidades));
SELECT setval('ubigeo_id_seq',            (SELECT COALESCE(max(id), 1) FROM ubigeo));
SELECT setval('ipress_id_seq',            (SELECT COALESCE(max(id), 1) FROM ipress));

-- ---------------------------------------------------------------------------
-- 5. Materialización del MODELO DIMENSIONAL EN ESTRELLA (Capa Gold)
-- ---------------------------------------------------------------------------
\echo '>> Materializando dimensiones (Gold)...'

INSERT INTO dim_ipress (ipress_key, codigo_renipress, nombre, categoria,
                        nivel_atencion, capacidad_resolutiva, departamento,
                        provincia, distrito, latitud, longitud, geom,
                        estado_operativo, capacidad_camas, propietario)
SELECT i.id, i.codigo_renipress, i.nombre, c.codigo, c.nivel_atencion,
       c.capacidad_resolutiva, i.departamento, i.provincia, i.distrito,
       i.latitud, i.longitud, i.geom, i.estado_operativo, i.capacidad_camas,
       i.propietario
  FROM ipress i
  JOIN categorizaciones c ON c.id = i.categoria_id;

INSERT INTO dim_ubigeo (ubigeo_key, codigo_ubigeo, departamento, provincia,
                        distrito, latitud_centroide, longitud_centroide, geom_centroide)
SELECT id, codigo_ubigeo, departamento, provincia, distrito,
       latitud_centroide, longitud_centroide, geom_centroide
  FROM ubigeo;

INSERT INTO dim_tiempo (tiempo_key, anio, mes, dia, trimestre, semana_iso,
                        nombre_mes, nombre_dia, es_fin_de_semana)
SELECT d::date,
       EXTRACT(year FROM d)::smallint,
       EXTRACT(month FROM d)::smallint,
       EXTRACT(day FROM d)::smallint,
       EXTRACT(quarter FROM d)::smallint,
       EXTRACT(week FROM d)::smallint,
       to_char(d, 'TMMonth'),
       to_char(d, 'TMDay'),
       (EXTRACT(isodow FROM d) IN (6, 7))
  FROM generate_series('2024-01-01'::date, '2024-12-31'::date, '1 day') AS d;

\echo '>> Materializando tabla de hechos fact_atenciones_medicas...'

-- Grain: IPRESS x día x ubigeo. La tasa de saturación es un KPI compuesto
-- (60% ocupación estimada + 40% tiempo de espera normalizado) que usa el
-- motor de recomendación anti-saturación.
INSERT INTO fact_atenciones_medicas (ipress_key, tiempo_key, ubigeo_key,
                                     num_atenciones, num_emergencias,
                                     num_hospitalizaciones, num_derivaciones,
                                     ocupacion_promedio, tiempo_espera_promedio,
                                     tasa_saturacion)
WITH agg AS (
    SELECT a.ipress_id AS ipress_key,
           a.fecha_atencion,
           u.id                    AS ubigeo_key,
           COUNT(*)                AS num_atenciones,
           COUNT(*) FILTER (WHERE a.tipo_atencion = 'EMERGENCIA')      AS num_emergencias,
           COUNT(*) FILTER (WHERE a.tipo_atencion = 'HOSPITALIZACION') AS num_hospitalizaciones,
           COUNT(*) FILTER (WHERE a.estado_salida = 'DERIVADO')        AS num_derivaciones,
           AVG(a.tiempo_espera_min)::numeric(7,2)                      AS espera_prom
      FROM atenciones_his a
      JOIN ubigeo u ON u.codigo_ubigeo = a.codigo_ubigeo
     GROUP BY 1, 2, 3
)
SELECT agg.ipress_key,
       agg.fecha_atencion,
       agg.ubigeo_key,
       agg.num_atenciones,
       agg.num_emergencias,
       agg.num_hospitalizaciones,
       agg.num_derivaciones,
       -- Ocupación estimada (%): atenciones vs capacidad instalada
       ROUND(LEAST(100.0,
            agg.num_atenciones * 0.8 /
            NULLIF(d.capacidad_camas + d.capacidad_resolutiva * 2, 0) * 100), 2),
       agg.espera_prom,
       -- Tasa de saturación compuesta (0-100)
       ROUND(LEAST(100.0,
           (CASE WHEN d.capacidad_camas + d.capacidad_resolutiva * 2 > 0
                 THEN agg.num_atenciones * 0.8 /
                      (d.capacidad_camas + d.capacidad_resolutiva * 2) * 100
                 ELSE 0 END) * 0.6
           + LEAST(100.0, agg.espera_prom) * 0.4), 2)
  FROM agg
  JOIN dim_ipress d ON d.ipress_key = agg.ipress_key;

-- ---------------------------------------------------------------------------
-- Resumen de carga (verificación)
-- ---------------------------------------------------------------------------
\echo '>> RESUMEN DE CARGA:'
SELECT 'categorizaciones' AS tabla, COUNT(*) AS filas FROM categorizaciones
UNION ALL SELECT 'especialidades', COUNT(*) FROM especialidades
UNION ALL SELECT 'ubigeo', COUNT(*) FROM ubigeo
UNION ALL SELECT 'ipress', COUNT(*) FROM ipress
UNION ALL SELECT 'atenciones_his', COUNT(*) FROM atenciones_his
UNION ALL SELECT 'fact_atenciones_medicas', COUNT(*) FROM fact_atenciones_medicas
UNION ALL SELECT 'dim_ipress', COUNT(*) FROM dim_ipress
UNION ALL SELECT 'dim_ubigeo', COUNT(*) FROM dim_ubigeo
UNION ALL SELECT 'dim_tiempo', COUNT(*) FROM dim_tiempo;
