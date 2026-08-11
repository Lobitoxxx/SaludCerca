# ============================================================================
# SALUD CERCA - src/bronze.py
# ----------------------------------------------------------------------------
# Capa Bronze del Lakehouse: persistencia del dato CRUDO (sin transformar)
# en Parquet, particionado por año/mes en el caso del volumen masivo.
# ============================================================================

from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from config import PipelineConfig
from ingestion import HisReader, RenipressReader, UbigeoReader


class BronzeWriter:
    """Persiste las fuentes crudas en el Data Lake (Parquet)."""

    def __init__(self, spark: SparkSession, cfg: PipelineConfig) -> None:
        self.spark = spark
        self.cfg = cfg

    def escribir(self, renipress: DataFrame, his: DataFrame, ubigeo: DataFrame) -> None:
        # --- RENIPRESS (bruto, sin particionar: ~2k filas) -----------------
        (renipress
         .coalesce(1)
         .write.mode("overwrite")
         .parquet(str(self.cfg.bronze_dir / "renipress")))

        # --- HIS-MINSA (masivo, particionado por año/mes) -----------------
        # Particionamiento físico = pruning en consultas temporales y
        # escrituras incrementales (una partición = un mes de atención).
        his_cols = [c for c in his.columns if c not in ("anio", "mes")]
        (his.select(*his_cols)
         .withColumn("anio", F.year("fecha_atencion"))
         .withColumn("mes", F.month("fecha_atencion"))
         .write.mode("overwrite")
         .partitionBy("anio", "mes")
         .parquet(str(self.cfg.bronze_dir / "his")))

        # --- Ubigeo (tabla maestra pequeña) -------------------------------
        (ubigeo
         .coalesce(1)
         .write.mode("overwrite")
         .parquet(str(self.cfg.bronze_dir / "ubigeo")))

        self._auditar("renipress", renipress)
        self._auditar("his", his)
        self._auditar("ubigeo", ubigeo)

    @staticmethod
    def _auditar(nombre: str, df: DataFrame) -> None:
        print(f"[bronze] {nombre}: {df.count():,} registros persistidos")


def run_bronze(spark: SparkSession, cfg: PipelineConfig) -> dict[str, int]:
    """Orquesta la carga de fuentes crudas hacia la capa Bronze."""
    renipress = RenipressReader.read(spark, cfg.raw_dir / "renipress.csv")
    his = HisReader.read(spark, cfg.raw_dir / "his_atenciones.csv")
    ubigeo = UbigeoReader.read(spark, cfg.raw_dir / "ubigeo.csv")

    BronzeWriter(spark, cfg).escribir(renipress, his, ubigeo)
    return {"renipress": renipress.count(), "his": his.count(), "ubigeo": ubigeo.count()}
