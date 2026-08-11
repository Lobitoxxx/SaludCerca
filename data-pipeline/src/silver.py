# ============================================================================
# SALUD CERCA - src/silver.py
# ----------------------------------------------------------------------------
# Capa Silver del Lakehouse: datos LIMPIOS, tipados y sin duplicados,
# persistidos en Parquet (columnar + compresión snappy) y particionados
# para consultas y re-ingestas eficientes.
# ============================================================================

from __future__ import annotations

from pyspark.sql import SparkSession

from cleaning import DataCleaner
from config import PipelineConfig


class SilverWriter:
    """Aplica el pipeline de calidad de datos y persiste la capa Silver."""

    def __init__(self, spark: SparkSession, cfg: PipelineConfig) -> None:
        self.spark = spark
        self.cfg = cfg
        self.cleaner = DataCleaner()

    def construir_ipress(self) -> "pyspark.sql.DataFrame":  # noqa: F821
        """Silver de IPRESS: dedup + geocoding imputado + tipificación."""
        ipress = self.spark.read.parquet(str(self.cfg.bronze_dir / "renipress"))
        ubigeo = self.spark.read.parquet(str(self.cfg.bronze_dir / "ubigeo"))

        return (
            ipress.transform(self.cleaner.deduplicar_ipress)
            .transform(lambda df: self.cleaner.imputar_geocoding(df, ubigeo))
            .transform(self.cleaner.tipificar_ipress)
        )

    def construir_his(self) -> "pyspark.sql.DataFrame":  # noqa: F821
        """Silver de atenciones HIS: dedup + tipificación + fecha_key."""
        his = self.spark.read.parquet(str(self.cfg.bronze_dir / "his"))
        return his.transform(self.cleaner.deduplicar_his).transform(self.cleaner.tipificar_his)

    def escribir(self) -> dict[str, int]:
        ipress_silver = self.construir_ipress()
        his_silver = self.construir_his()

        # Silver IPRESS (dimensión, sin particionar)
        ipress_silver.write.mode("overwrite").parquet(
            str(self.cfg.silver_dir / "ipress_silver.parquet")
        )

        # Silver HIS particionado por año/mes -> pruning eficiente
        cols_his = [c for c in his_silver.columns if c not in ("anio", "mes", "fecha_key")]
        his_silver.select(*cols_his, "anio", "mes").write.mode("overwrite") \
            .partitionBy("anio", "mes") \
            .parquet(str(self.cfg.silver_dir / "atenciones_silver"))

        n_ipress = ipress_silver.count()
        n_his = his_silver.count()
        print(f"[silver] ipress_silver: {n_ipress:,} registros")
        print(f"[silver] atenciones_silver: {n_his:,} registros (particionado por anio/mes)")
        return {"ipress": n_ipress, "his": n_his}


def run_silver(spark: SparkSession, cfg: PipelineConfig) -> dict[str, int]:
    """Orquesta la construcción de la capa Silver (limpia)."""
    return SilverWriter(spark, cfg).escribir()
