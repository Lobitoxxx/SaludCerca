# ============================================================================
# SALUD CERCA - src/ingestion.py
# ----------------------------------------------------------------------------
# Lectura masiva de las fuentes del MINSA (RENIPRESS e HIS-MINSA).
#
# Estrategia para millones de registros:
#   * Esquemas tipados (StructType) en lugar de inferencia -> evita un pase
#     completo de lectura para inferir tipos (2x más rápido en la práctica).
#   * Modo PERMISSIVE + columna _corrupt_record: los registros malformados
#     se aíslan y auditan, sin abortar el batch.
#   * Lectores separados por formato: CSV (RENIPRESS) y CSV/JSON (HIS).
# ============================================================================

from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

# ---------------------------------------------------------------------------
# Esquemas tipados (reflejan los datasets reales de RENIPRESS y HIS-MINSA)
# ---------------------------------------------------------------------------

RENIPRESS_SCHEMA = StructType(
    [
        StructField("id", IntegerType(), True),
        StructField("codigo_renipress", StringType(), False),
        StructField("nombre", StringType(), False),
        StructField("categoria_id", IntegerType(), True),
        StructField("ubigeo_id", IntegerType(), True),
        StructField("direccion", StringType(), True),
        StructField("departamento", StringType(), True),
        StructField("provincia", StringType(), True),
        StructField("distrito", StringType(), True),
        StructField("latitud", DoubleType(), True),          # puede venir vacía -> geocoding
        StructField("longitud", DoubleType(), True),         # puede venir vacía -> geocoding
        StructField("estado_operativo", StringType(), True),
        StructField("capacidad_camas", IntegerType(), True),
        StructField("capacidad_consultorios", IntegerType(), True),
        StructField("horario", StringType(), True),
        # Se lee como STRING porque Spark CSV no soporta trueValue/falseValue
        # singular (removido en 3.x); la conversión a booleano ocurre en la
        # capa de limpieza (cleaning.tipificar_ipress).
        StructField("tiene_ambulancia", StringType(), True),
        StructField("telefono", StringType(), True),
        StructField("propietario", StringType(), True),
        StructField("descripcion_emb", StringType(), True),  # literal pgvector "[0.1,...]"
    ]
)

HIS_SCHEMA = StructType(
    [
        StructField("codigo_ipress", StringType(), False),
        StructField("ipress_id", IntegerType(), True),
        StructField("codigo_ubigeo", StringType(), True),
        StructField("fecha_atencion", DateType(), False),
        StructField("especialidad_id", IntegerType(), True),
        StructField("diagnostico_cie10", StringType(), True),
        StructField("tipo_atencion", StringType(), True),
        StructField("edad_paciente", IntegerType(), True),
        StructField("sexo", StringType(), True),
        StructField("tiempo_espera_min", IntegerType(), True),
        StructField("estado_salida", StringType(), True),
        StructField("derivado_a", StringType(), True),
    ]
)

UBIGEO_SCHEMA = StructType(
    [
        StructField("id", IntegerType(), True),
        StructField("codigo_ubigeo", StringType(), False),
        StructField("departamento", StringType(), False),
        StructField("provincia", StringType(), False),
        StructField("distrito", StringType(), False),
        StructField("latitud_centroide", DoubleType(), True),
        StructField("longitud_centroide", DoubleType(), True),
    ]
)


class RenipressReader:
    """Lector del registro nacional de establecimientos de salud (RENIPRESS)."""

    @staticmethod
    def read(spark: SparkSession, path: Path | str) -> DataFrame:
        """Lee el CSV masivo de IPRESS con esquema tipado y manejo de corruptos."""
        return (
            spark.read.schema(RENIPRESS_SCHEMA)
            .option("header", True)
            .option("encoding", "UTF-8")
            .option("mode", "PERMISSIVE")                    # aísla filas corruptas
            .option("columnNameOfCorruptRecord", "_corrupt_record")
            .option("nullValue", "")
            .option("inferSchema", False)
            .csv(str(path))
        )


class HisReader:
    """Lector de atenciones HIS-MINSA (millones de registros).

    Soporta dos formatos de fuente (el MINSA publica ambos):
      * CSV  -> spark.read.csv
      * JSON -> spark.read.json (multilinea si es pretty-printed)
    """

    @staticmethod
    def read(spark: SparkSession, path: Path | str) -> DataFrame:
        path = Path(path)
        if path.is_dir():
            files = list(path.glob("*.csv")) + list(path.glob("*.json"))
            if not files:
                raise FileNotFoundError(f"No hay CSV/JSON en: {path}")
            frame = HisReader._read_csv(spark, path) if files[0].suffix == ".csv" \
                else HisReader._read_json(spark, path)
        elif path.suffix == ".json":
            frame = HisReader._read_json(spark, path)
        else:
            frame = HisReader._read_csv(spark, path)
        return frame

    @staticmethod
    def _read_csv(spark: SparkSession, path: Path | str) -> DataFrame:
        return (
            spark.read.schema(HIS_SCHEMA)
            .option("header", True)
            .option("encoding", "UTF-8")
            .option("mode", "PERMISSIVE")
            .option("columnNameOfCorruptRecord", "_corrupt_record")
            .option("nullValue", "")
            .csv(str(path))
        )

    @staticmethod
    def _read_json(spark: SparkSession, path: Path | str) -> DataFrame:
        return (
            spark.read.schema(HIS_SCHEMA)
            .option("mode", "PERMISSIVE")
            .option("multiline", True)
            .json(str(path))
        )


class UbigeoReader:
    """Lector de la tabla maestra de división política (INEI)."""

    @staticmethod
    def read(spark: SparkSession, path: Path | str) -> DataFrame:
        return (
            spark.read.schema(UBIGEO_SCHEMA)
            .option("header", True)
            .option("encoding", "UTF-8")
            .option("nullValue", "")
            .csv(str(path))
        )
