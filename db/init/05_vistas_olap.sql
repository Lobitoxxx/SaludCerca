-- ============================================================================
-- SALUD CERCA - 05. Vistas OLAP / Geo-analítica
-- ----------------------------------------------------------------------------
-- Vistas de agregación que alimentan el Dashboard y los endpoints REST:
--   * vw_cobertura_regional : métricas de cobertura por departamento (GeoJSON)
--   * vw_saturacion_ipress  : saturación vigente por establecimiento
--   * vw_brechas_cobertura  : zonas con déficit (desiertos sanitarios)
--   * vw_atenciones_mensual : tendencia temporal para series de tiempo
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Cobertura por departamento (para /api/v1/analitica/cobertura)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_cobertura_regional AS
SELECT
    u.departamento,
    COUNT(DISTINCT i.id)                                          AS total_ipress,
    COUNT(DISTINCT i.id) FILTER (WHERE i.estado_operativo = 'ACTIVO') AS ipress_activas,
    COUNT(DISTINCT i.id) FILTER (WHERE c.nivel_atencion = 1)     AS nivel_primario,
    COUNT(DISTINCT i.id) FILTER (WHERE c.nivel_atencion = 2)     AS nivel_secundario,
    COUNT(DISTINCT i.id) FILTER (WHERE c.nivel_atencion = 3)     AS nivel_terciario,
    COALESCE(ROUND(AVG(f.tasa_saturacion) FILTER (WHERE f.tasa_saturacion IS NOT NULL), 2), 0) AS saturacion_promedio,
    -- Índice de cobertura: establecimientos cada 10 000 habitantes (proxy por ubigeo)
    -- NOTA: MAX() porque la población es constante por departamento (el SUM lo
    -- habría multiplicado por el número de filas del grupo).
    ROUND(
        (COUNT(DISTINCT i.id)::NUMERIC / NULLIF(MAX(dim_u.poblacion_proxy) FILTER (WHERE dim_u.poblacion_proxy > 0), 0)) * 10000.0, 2
    )                                                             AS indice_cobertura,
    -- Punto representativo del departamento (agregado espacial para heatmaps)
    ST_Centroid(ST_Collect(i.geom))                              AS geom_centroide
FROM ubigeo u
LEFT JOIN ipress i ON i.ubigeo_id = u.id
LEFT JOIN categorizaciones c ON c.id = i.categoria_id
LEFT JOIN dim_ipress d_ip ON d_ip.codigo_renipress = i.codigo_renipress
LEFT JOIN fact_atenciones_medicas f ON f.ipress_key = d_ip.ipress_key
LEFT JOIN LATERAL (
    SELECT MAX(r.poblacion_proxy) AS poblacion_proxy
    FROM (VALUES
        ('AMAZONAS', 426), ('ANCASH', 1185), ('APURIMAC', 418), ('AREQUIPA', 1516),
        ('AYACUCHO', 668), ('CAJAMARCA', 1390), ('CALLAO', 1170), ('CUSCO', 1390),
        ('HUANCAVELICA', 348), ('HUANUCO', 771), ('ICA', 977), ('JUNIN', 1389),
        ('LA LIBERTAD', 2074), ('LAMBAYEQUE', 1316), ('LIMA', 10501), ('LORETO', 1027),
        ('MADRE DE DIOS', 177), ('MOQUEGUA', 201), ('PASCO', 272), ('PIURA', 2113),
        ('PUNO', 1153), ('SAN MARTIN', 940), ('TACNA', 386), ('TUMBES', 262), ('UCAYALI', 617)
    ) AS r(dep, poblacion_proxy)  -- Unidades: miles de habitantes
    WHERE r.dep = u.departamento
) AS dim_u ON TRUE
GROUP BY u.departamento;

-- ---------------------------------------------------------------------------
-- Saturación vigente por IPRESS (para recomendación anti-saturación)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_saturacion_ipress AS
SELECT
    d.ipress_key,
    d.codigo_renipress,
    d.nombre,
    d.categoria,
    d.nivel_atencion,
    d.capacidad_resolutiva,
    d.estado_operativo,
    d.latitud,
    d.longitud,
    d.geom,
    COALESCE(ROUND(AVG(f.tasa_saturacion), 2), 0)  AS saturacion_promedio,
    COALESCE(SUM(f.num_atenciones), 0)             AS atenciones_periodo
FROM dim_ipress d
LEFT JOIN fact_atenciones_medicas f ON f.ipress_key = d.ipress_key
    AND f.tiempo_key >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY d.ipress_key;

-- ---------------------------------------------------------------------------
-- Brechas de cobertura: distritos sin establecimiento ACTIVO en X km
-- (desiertos sanitarios, complementa el clustering DBSCAN del motor ML)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_brechas_cobertura AS
WITH activos AS (
    SELECT geom FROM ipress WHERE estado_operativo = 'ACTIVO' AND geom IS NOT NULL
)
SELECT
    u.id              AS ubigeo_id,
    u.codigo_ubigeo,
    u.departamento,
    u.provincia,
    u.distrito,
    u.geom_centroide,
    -- Distancia al establecimiento activo más cercano (en km)
    -- NOTA: ST_Distance retorna double precision; se castea a numeric
    -- porque ROUND(double, int) no existe en PostgreSQL.
    ROUND((
        ST_Distance(
            u.geom_centroide::geography,
            (SELECT a.geom FROM activos a ORDER BY u.geom_centroide <-> a.geom LIMIT 1)::geography
        ) / 1000.0
    )::numeric, 2)   AS km_ipress_mas_cercana,
    -- Clasificación de brecha según cobertura estandarizada
    CASE
        WHEN (SELECT COUNT(*) FROM activos WHERE ST_DWithin(u.geom_centroide::geography, activos.geom::geography, 10000)) = 0
            THEN 'DESIERTO_SANITARIO'
        WHEN (SELECT COUNT(*) FROM activos WHERE ST_DWithin(u.geom_centroide::geography, activos.geom::geography, 10000)) <= 2
            THEN 'DEFICIT_MODERADO'
        ELSE 'COBERTURA_ACEPTABLE'
    END               AS brecha
FROM ubigeo u
WHERE u.geom_centroide IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Tendencia mensual de atenciones (alimenta series de tiempo / Prophet)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_atenciones_mensual AS
SELECT
    date_trunc('month', f.tiempo_key)::date AS mes,
    d.departamento,
    COUNT(*)                                 AS num_dias,
    SUM(f.num_atenciones)                    AS total_atenciones,
    SUM(f.num_emergencias)                   AS total_emergencias,
    ROUND(AVG(f.tasa_saturacion), 2)         AS saturacion_promedio
FROM fact_atenciones_medicas f
JOIN dim_ipress d ON d.ipress_key = f.ipress_key
GROUP BY 1, 2
ORDER BY 1, 2;
