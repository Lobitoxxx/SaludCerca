# ============================================================================
# SALUD CERCA - src/gold.py
# ----------------------------------------------------------------------------
# Capa Gold: carga del Data Lake (Silver) hacia PostgreSQL + PostGIS + pgvector
# con semántica UPSERT (MERGE) y mantenimiento del modelo dimensional.
#
# Estrategias aplicadas:
#   * Staging tables (stg_*) escritas por Spark JDBC (batch) para minimizar
#     round-trips; luego MERGE transaccional en la JVM de Spark.
#   * Dimensión ipress   -> MERGE por clave natural codigo_renipress (UPSERT).
#   * Hechos atenciones  -> reload idempotente del rango del batch
#                           (DELETE + INSERT = reemplazo de "partición lógica").
#   * Geometrías PostGIS -> UPDATE con ST_SetSRID/ST_MakePoint.
#   * Modelo estrella    -> refresh de dims y fact (ON CONFLICT DO UPDATE).
# ============================================================================

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from config import PipelineConfig

# Columnas objetivo (orden estable entre staging y tablas Gold)
IPRESS_COLS = [
    "codigo_renipress", "nombre", "categoria_id", "ubigeo_id", "direccion",
    "departamento", "provincia", "distrito", "latitud", "longitud",
    "estado_operativo", "capacidad_camas", "capacidad_consultorios",
    "horario", "tiene_ambulancia", "telefono", "propietario", "descripcion_emb",
]

HIS_COLS = [
    "codigo_ipress", "ipress_id", "codigo_ubigeo", "fecha_atencion",
    "especialidad_id", "diagnostico_cie10", "tipo_atencion", "edad_paciente",
    "sexo", "tiempo_espera_min", "estado_salida", "derivado_a",
]


class PostgisGoldWriter:
    """Carga incremental (UPSERT) de la capa Silver hacia PostgreSQL/PostGIS."""

    def __init__(self, spark: SparkSession, cfg: PipelineConfig) -> None:
        self.spark = spark
        self.cfg = cfg

    # -- Conexión JDBC (a través de la JVM de Spark, sin dependencias extra) --
    def _jdbc(self):
        jvm = self.spark.sparkContext._jvm
        return jvm.java.sql.DriverManager.getConnection(
            self.cfg.postgres_url, self.cfg.postgres_user, self.cfg.postgres_password
        )

    def _ejecutar(self, sql: str) -> None:
        conn = self._jdbc()
        try:
            stmt = conn.createStatement()
            try:
                stmt.execute(sql)
            finally:
                stmt.close()
        finally:
            conn.close()

    # -- Staging ---------------------------------------------------------
    def _escribir_staging(self, tabla: str, df: DataFrame) -> None:
        (df.write.format("jdbc")
         .options(
             url=self.cfg.postgres_url,
             driver=self.cfg.postgres_driver,
             dbtable=tabla,
             user=self.cfg.postgres_user,
             password=self.cfg.postgres_password,
             batchsize="10000",                 # lotes grandes de inserción
             rewriteBatchedInserts="true",       # insert multi-row (hasta 10x)
             truncate="true",
         )
         .mode("overwrite")
         .save())

    # -- Dimensión IPRESS: MERGE (UPSERT) por clave natural ---------------
    _MERGE_IPRESS = f"""
    MERGE INTO ipress AS t
    USING stg_ipress AS s
      ON t.codigo_renipress = s.codigo_renipress
    WHEN MATCHED THEN UPDATE SET
        nombre                = s.nombre,
        categoria_id          = s.categoria_id,
        ubigeo_id             = s.ubigeo_id,
        direccion             = s.direccion,
        departamento          = s.departamento,
        provincia             = s.provincia,
        distrito              = s.distrito,
        latitud               = s.latitud,
        longitud              = s.longitud,
        estado_operativo      = s.estado_operativo,
        capacidad_camas       = s.capacidad_camas,
        capacidad_consultorios= s.capacidad_consultorios,
        horario               = s.horario,
        tiene_ambulancia      = s.tiene_ambulancia,
        telefono              = s.telefono,
        propietario           = s.propietario,
        descripcion_emb       = s.descripcion_emb::vector
    WHEN NOT MATCHED THEN INSERT
        (codigo_renipress, nombre, categoria_id, ubigeo_id, direccion,
         departamento, provincia, distrito, latitud, longitud,
         estado_operativo, capacidad_camas, capacidad_consultorios,
         horario, tiene_ambulancia, telefono, propietario, descripcion_emb)
    VALUES
        (s.codigo_renipress, s.nombre, s.categoria_id, s.ubigeo_id, s.direccion,
         s.departamento, s.provincia, s.distrito, s.latitud, s.longitud,
         s.estado_operativo, s.capacidad_camas, s.capacidad_consultorios,
         s.horario, s.tiene_ambulancia, s.telefono, s.propietario,
         s.descripcion_emb::vector);
    """

    # -- Hechos HIS: reload idempotente del rango del batch --------------
    def _reload_atenciones(self, min_fecha: str, max_fecha: str) -> None:
        self._ejecutar(
            f"DELETE FROM atenciones_his "
            f"WHERE fecha_atencion BETWEEN DATE '{min_fecha}' AND DATE '{max_fecha}'"
        )
        self._ejecutar(
            f"INSERT INTO atenciones_his ({', '.join(HIS_COLS)}) "
            f"SELECT {', '.join(HIS_COLS)} FROM stg_atenciones"
        )

    def _actualizar_geometrias(self) -> None:
        self._ejecutar(
            "UPDATE ipress SET geom = ST_SetSRID(ST_MakePoint(longitud, latitud), 4326) "
            "WHERE latitud IS NOT NULL AND longitud IS NOT NULL"
        )

    # -- Mantenimiento del modelo dimensional (estrella) ------------------
    def _refrescar_dim_ipress(self) -> None:
        self._ejecutar("""
        INSERT INTO dim_ipress (ipress_key, codigo_renipress, nombre, categoria,
                                nivel_atencion, capacidad_resolutiva, departamento,
                                provincia, distrito, latitud, longitud, geom,
                                estado_operativo, capacidad_camas, propietario)
        SELECT i.id, i.codigo_renipress, i.nombre, c.codigo, c.nivel_atencion,
               c.capacidad_resolutiva, i.departamento, i.provincia, i.distrito,
               i.latitud, i.longitud, i.geom, i.estado_operativo, i.capacidad_camas,
               i.propietario
          FROM ipress i
          JOIN categorizaciones c ON c.id = i.categoria_id
        ON CONFLICT (ipress_key) DO UPDATE SET
               codigo_renipress     = EXCLUDED.codigo_renipress,
               nombre               = EXCLUDED.nombre,
               categoria            = EXCLUDED.categoria,
               nivel_atencion       = EXCLUDED.nivel_atencion,
               capacidad_resolutiva = EXCLUDED.capacidad_resolutiva,
               departamento         = EXCLUDED.departamento,
               provincia            = EXCLUDED.provincia,
               distrito             = EXCLUDED.distrito,
               latitud              = EXCLUDED.latitud,
               longitud             = EXCLUDED.longitud,
               geom                 = EXCLUDED.geom,
               estado_operativo     = EXCLUDED.estado_operativo,
               capacidad_camas      = EXCLUDED.capacidad_camas,
               propietario          = EXCLUDED.propietario
        """)

    def _refrescar_dim_tiempo(self, min_fecha: str, max_fecha: str) -> None:
        self._ejecutar(f"""
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
          FROM generate_series(DATE '{min_fecha}', DATE '{max_fecha}', '1 day') AS d
        ON CONFLICT (tiempo_key) DO NOTHING
        """)

    def _recomputar_fact(self, min_fecha: str, max_fecha: str) -> None:
        """Recalcula los hechos OLAP del rango del batch (grain ipress x día x ubigeo)."""
        self._ejecutar(f"""
        INSERT INTO fact_atenciones_medicas (ipress_key, tiempo_key, ubigeo_key,
                                             num_atenciones, num_emergencias,
                                             num_hospitalizaciones, num_derivaciones,
                                             ocupacion_promedio, tiempo_espera_promedio,
                                             tasa_saturacion)
        WITH agg AS (
            SELECT a.ipress_id AS ipress_key,
                   a.fecha_atencion,
                   u.id        AS ubigeo_key,
                   COUNT(*)    AS num_atenciones,
                   COUNT(*) FILTER (WHERE a.tipo_atencion = 'EMERGENCIA')      AS num_emergencias,
                   COUNT(*) FILTER (WHERE a.tipo_atencion = 'HOSPITALIZACION') AS num_hospitalizaciones,
                   COUNT(*) FILTER (WHERE a.estado_salida = 'DERIVADO')        AS num_derivaciones,
                   AVG(a.tiempo_espera_min)::numeric(7,2) AS espera_prom
              FROM atenciones_his a
              JOIN ubigeo u ON u.codigo_ubigeo = a.codigo_ubigeo
             WHERE a.fecha_atencion BETWEEN DATE '{min_fecha}' AND DATE '{max_fecha}'
             GROUP BY 1, 2, 3
        )
        SELECT agg.ipress_key, agg.fecha_atencion, agg.ubigeo_key,
               agg.num_atenciones, agg.num_emergencias, agg.num_hospitalizaciones,
               agg.num_derivaciones,
               ROUND(LEAST(100.0, agg.num_atenciones * 0.8 /
                    NULLIF(d.capacidad_camas + d.capacidad_resolutiva * 2, 0) * 100), 2),
               agg.espera_prom,
               ROUND(LEAST(100.0,
                   (CASE WHEN d.capacidad_camas + d.capacidad_resolutiva * 2 > 0
                         THEN agg.num_atenciones * 0.8 /
                              (d.capacidad_camas + d.capacidad_resolutiva * 2) * 100
                         ELSE 0 END) * 0.6
                   + LEAST(100.0, agg.espera_prom) * 0.4), 2)
          FROM agg
          JOIN dim_ipress d ON d.ipress_key = agg.ipress_key
        ON CONFLICT (ipress_key, tiempo_key, ubigeo_key) DO UPDATE SET
               num_atenciones            = EXCLUDED.num_atenciones,
               num_emergencias           = EXCLUDED.num_emergencias,
               num_hospitalizaciones     = EXCLUDED.num_hospitalizaciones,
               num_derivaciones          = EXCLUDED.num_derivaciones,
               ocupacion_promedio        = EXCLUDED.ocupacion_promedio,
               tiempo_espera_promedio    = EXCLUDED.tiempo_espera_promedio,
               tasa_saturacion           = EXCLUDED.tasa_saturacion
        """)

    # -- Orquestación ----------------------------------------------------
    def escribir(self) -> dict[str, int]:
        ipress = self.spark.read.parquet(str(self.cfg.silver_dir / "ipress_silver.parquet"))
        his = self.spark.read.parquet(str(self.cfg.silver_dir / "atenciones_silver"))

        # Asegurar particiones mensuales para el rango del batch
        meses = his.select("anio", "mes").distinct().collect()
        for m in meses:
            fecha = f"{m['anio']:04d}-{m['mes']:02d}-01"
            self._ejecutar(f"SELECT crear_particion_mensual(DATE '{fecha}')")

        # Rango temporal del batch
        rango = his.agg(
            F.min("fecha_atencion").alias("min"),
            F.max("fecha_atencion").alias("max"),
        ).collect()[0]
        min_fecha = rango["min"].isoformat()
        max_fecha = rango["max"].isoformat()
        print(f"[gold] rango del batch: {min_fecha} .. {max_fecha}")

        # 1) Staging (write masivo por JDBC)
        print("[gold] escribiendo staging stg_ipress / stg_atenciones ...")
        self._escribir_staging("stg_ipress", ipress.select(*IPRESS_COLS))
        his_cols = [c for c in HIS_COLS]
        self._escribir_staging("stg_atenciones", his.select(*his_cols))

        # 2) UPSERT dimensión ipress
        print("[gold] MERGE ipress (UPSERT por codigo_renipress) ...")
        self._ejecutar(self._MERGE_IPRESS)

        # 3) Reload idempotente de hechos HIS
        print("[gold] reload atenciones_his (DELETE + INSERT del rango) ...")
        self._reload_atenciones(min_fecha, max_fecha)

        # 4) Geometrías PostGIS
        print("[gold] actualizando geometrías (ST_MakePoint) ...")
        self._actualizar_geometrias()

        # 5) Mantenimiento del modelo dimensional
        print("[gold] refrescando dim_ipress / dim_tiempo ...")
        self._refrescar_dim_ipress()
        self._refrescar_dim_tiempo(min_fecha, max_fecha)

        # 6) Recomputo de hechos OLAP (estrella)
        print("[gold] recomputando fact_atenciones_medicas ...")
        self._recomputar_fact(min_fecha, max_fecha)

        # 7) Limpieza de staging
        self._ejecutar("DROP TABLE IF EXISTS stg_ipress")
        self._ejecutar("DROP TABLE IF EXISTS stg_atenciones")

        n_ipress = ipress.count()
        n_his = his.count()
        print(f"[gold] IPRESS upserted: {n_ipress:,} | atenciones cargadas: {n_his:,}")
        return {"ipress": n_ipress, "his": n_his}


def run_gold(spark: SparkSession, cfg: PipelineConfig) -> dict[str, int]:
    """Orquesta la carga de la capa Silver hacia PostgreSQL/PostGIS (Gold)."""
    return PostgisGoldWriter(spark, cfg).escribir()
