# ============================================================================
# SALUD CERCA - src/cleaning.py
# ----------------------------------------------------------------------------
# Capa de calidad de datos (Calidad en la fuente -> Silver):
#   1. deduplicar        -> eliminación de duplicados por claves de negocio
#   2. imputar_geocoding -> geocoding de coordenadas faltantes usando el
#                           centroide del ubigeo (tabla maestra INEI)
#   3. tipificar         -> casting estricto de tipos y normalización textual
# ============================================================================

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Mapeo columna geográfica -> columna centroide de la tabla maestra ubigeo
CENTROIDE = {"latitud": "latitud_centroide", "longitud": "longitud_centroide"}


class DataCleaner:
    """Pipeline de limpieza para las capas Silver."""

    # -- 1) Deduplicación ------------------------------------------------
    @staticmethod
    def deduplicar(df: DataFrame, subset: list[str], orden: str = "fecha_atencion") -> DataFrame:
        """Elimina duplicados exactos por `subset`, conservando la fila más reciente.

        La ventana ordena por `orden` (descendente) para que un "batch tardío"
        no cree filas repetidas al reprocesar datos ya entregados.
        """
        if not any(c in df.columns for c in subset):
            return df
        w = Window.partitionBy(subset).orderBy(F.col(orden).desc())
        dedup = (
            df.withColumn("_rn", F.row_number().over(w))
            .filter(F.col("_rn") == 1)
            .drop("_rn")
        )
        # Auditoría: cuántos duplicados fueron eliminados
        eliminados = df.count() - dedup.count()
        print(f"[cleaning.deduplicar] subset={subset} duplicados eliminados={eliminados}")
        return dedup

    @staticmethod
    def deduplicar_ipress(df: DataFrame) -> DataFrame:
        """Deduplicación de establecimientos por su clave natural RENIPRESS."""
        return DataCleaner.deduplicar(
            df, subset=["codigo_renipress"], orden="id"
        )

    @staticmethod
    def deduplicar_his(df: DataFrame) -> DataFrame:
        """Deduplicación de atenciones por clave compuesta del evento.

        En HIS real no existe clave única; se usan los atributos del evento
        para eliminar duplicados exactos de carga.
        """
        return DataCleaner.deduplicar(
            df,
            subset=["codigo_ipress", "codigo_ubigeo", "fecha_atencion",
                    "especialidad_id", "diagnostico_cie10", "tipo_atencion",
                    "edad_paciente", "sexo"],
            orden="fecha_atencion",
        )

    # -- 2) Imputación de coordenadas (Geocoding) ------------------------
    @staticmethod
    def imputar_geocoding(
        ipress: DataFrame, ubigeo: DataFrame, umbral_km: float = 50.0
    ) -> DataFrame:
        """Imputa latitud/longitud faltantes con el centroide del ubigeo.

        Cuando el RENIPRESS no registra coordenadas (común en zonas rurales),
        se asigna el centroide del distrito de la tabla maestra INEI.
        El broadcast join es correcto aquí porque `ubigeo` es una dimensión
        pequeña (decenas de KB) -> evita shuffle masivo.
        """
        # Solo las filas con coordenadas faltantes requieren imputación.
        # Se usan alias calificados ("s."/"u.") porque ambas tablas comparten
        # columnas como `id` (ambigüedad en el join y en el select posterior).
        sin_coords = ipress.filter(
            F.col("latitud").isNull() | F.col("longitud").isNull()
        ).alias("s")
        con_coords = ipress.filter(
            F.col("latitud").isNotNull() & F.col("longitud").isNotNull()
        )

        if sin_coords.count() == 0:
            print("[cleaning.imputar_geocoding] sin coordenadas faltantes")
            return ipress

        imputadas = (
            sin_coords.join(
                F.broadcast(ubigeo).alias("u"),
                F.col("s.ubigeo_id") == F.col("u.id"),
                "left",
            )
            .select(*[
                F.coalesce(
                    F.col(f"s.{c}"), F.col(f"u.{CENTROIDE[c]}")
                ).alias(c)
                if c in CENTROIDE
                else F.col(f"s.{c}")
                for c in ipress.columns
            ])
        )

        n_imputadas = imputadas.filter(
            F.col("latitud").isNotNull() & F.col("longitud").isNotNull()
        ).count()
        print(
            f"[cleaning.imputar_geocoding] filas imputadas con centroide ubigeo = {n_imputadas}"
        )
        return con_coords.unionByName(imputadas)

    # -- 3) Tipificación de columnas -------------------------------------
    @staticmethod
    def tipificar_ipress(df: DataFrame) -> DataFrame:
        """Casting estricto y normalización de los establecimientos."""
        return (
            df.withColumn("codigo_renipress", F.trim(F.upper(F.col("codigo_renipress"))))
            .withColumn("nombre", F.trim(F.upper(F.col("nombre"))))
            .withColumn("departamento", F.trim(F.upper(F.col("departamento"))))
            .withColumn("provincia", F.trim(F.upper(F.col("provincia"))))
            .withColumn("distrito", F.trim(F.upper(F.col("distrito"))))
            .withColumn("estado_operativo", F.upper(F.col("estado_operativo")))
            .withColumn("capacidad_camas", F.coalesce(F.col("capacidad_camas"), F.lit(0)))
            .withColumn(
                "capacidad_consultorios",
                F.coalesce(F.col("capacidad_consultorios"), F.lit(0)),
            )
            # Conversión explícita del booleano ("t"/"f"/"true"/"false"/"1"/"0")
            .withColumn(
                "tiene_ambulancia",
                F.when(F.col("tiene_ambulancia").isin("t", "true", "1"), F.lit(True))
                .when(F.col("tiene_ambulancia").isin("f", "false", "0"), F.lit(False))
                .otherwise(F.lit(False)),
            )
            .filter(F.col("codigo_renipress") != "")
        )

    @staticmethod
    def tipificar_his(df: DataFrame) -> DataFrame:
        """Casting estricto y validación de dominios de las atenciones."""
        tipos_validos = ["CONSULTA", "EMERGENCIA", "HOSPITALIZACION", "PREVENTIVA"]
        return (
            df.withColumn("fecha_atencion", F.to_date(F.col("fecha_atencion"), "yyyy-MM-dd"))
            .withColumn("sexo", F.upper(F.col("sexo")))
            .withColumn("tipo_atencion", F.upper(F.col("tipo_atencion")))
            .withColumn("diagnostico_cie10", F.upper(F.col("diagnostico_cie10")))
            # Calidad de dominio: solo fechas válidas y tipos de atención conocidos
            .filter(F.col("fecha_atencion").isNotNull())
            .filter(F.col("tipo_atencion").isin(*tipos_validos))
            .withColumn("anio", F.year("fecha_atencion"))
            .withColumn("mes", F.month("fecha_atencion"))
            .withColumn("fecha_key", F.date_format("fecha_atencion", "yyyy-MM"))
        )
