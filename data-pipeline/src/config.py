# ============================================================================
# SALUD CERCA - src/config.py
# ----------------------------------------------------------------------------
# Configuración centralizada del pipeline y construcción de la SparkSession
# con parámetros de sintonización para procesamiento masivo (millones de
# registros HIS-MINSA).
# ============================================================================

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from pyspark.sql import SparkSession

# Directorio raíz del proyecto (dos niveles arriba de este archivo)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class PipelineConfig:
    """Configuración del pipeline Medallón.

    Atributos:
        raw_dir:       Fuentes originales (CSV/JSON del MINSA o datasets sintéticos)
        lakehouse_dir: Data Lakehouse local (bronze/ + silver/)
        postgres_url:  Cadena JDBC hacia PostgreSQL + PostGIS + pgvector
        shuffle_partitions: Nº de particiones de shuffle (rule of thumb:
                       núcleos * 2~4, ajustado por volumen de datos)
    """

    # Rutas del Data Lake
    raw_dir: Path = PROJECT_ROOT / "data" / "output"
    lakehouse_dir: Path = PROJECT_ROOT / "data" / "lakehouse"
    bronze_dir: Path = field(init=False)
    silver_dir: Path = field(init=False)

    # Conexión PostgreSQL / PostGIS / pgvector (ver docker-compose.yml)
    postgres_url: str = os.getenv(
        "POSTGRES_URL",
        "jdbc:postgresql://localhost:5432/saludcerca",
    )
    postgres_user: str = os.getenv("POSTGRES_USER", "saludcerca")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "saludcerca123")
    postgres_driver: str = "org.postgresql.Driver"
    postgres_jdbc_jar: Path = PROJECT_ROOT / "data-pipeline" / "lib" / "postgresql-42.7.4.jar"

    # Sintonización Spark (escala: millones de registros)
    master: str = os.getenv("SPARK_MASTER", "local[*]")
    app_name: str = "saludcerca-etl-medallion"
    shuffle_partitions: int = int(os.getenv("SPARK_SHUFFLE_PARTITIONS", "8"))
    driver_memory: str = os.getenv("SPARK_DRIVER_MEMORY", "3g")
    executor_memory: str = os.getenv("SPARK_EXECUTOR_MEMORY", "3g")
    spark_local_dir: str = str(PROJECT_ROOT / "data" / "lakehouse" / "_spark_tmp")

    def __post_init__(self) -> None:
        self.bronze_dir = self.lakehouse_dir / "bronze"
        self.silver_dir = self.lakehouse_dir / "silver"
        for d in (self.raw_dir, self.lakehouse_dir, self.bronze_dir, self.silver_dir):
            d.mkdir(parents=True, exist_ok=True)

    def spark(self) -> SparkSession:
        """Construye una SparkSession sintonizada para el pipeline.

        Buenas prácticas de escala aplicadas:
          * spark.sql.shuffle.partitions  -> controla el n° de tareas de shuffle
          * spark.sql.adaptive.enabled    -> AQE: coalesce dinámico de particiones
          * spark.sql.autoBroadcastJoinThreshold -> broadcast de tablas pequeñas
            (dimensión ubigeo ~KB) evitando shuffles costosos.
          * spark.jars                     -> driver JDBC para la capa Gold.
        """
        builder = (
            SparkSession.builder.master(self.master)
            .appName(self.app_name)
            .config("spark.sql.shuffle.partitions", str(self.shuffle_partitions))
            .config("spark.sql.adaptive.enabled", "true")
            .config(
                "spark.sql.adaptive.coalescePartitions.enabled", "true"
            )
            .config(
                "spark.sql.autoBroadcastJoinThreshold",
                str(10 * 1024 * 1024),  # 10 MB
            )
            .config("spark.sql.parquet.compression.codec", "snappy")
            # Driver JDBC en el classpath del driver: en modo local[*] los
            # executors comparten JVM, así que NO se usa spark.jars (evita el
            # fetchFile de Hadoop/winutils en Windows).
            .config("spark.driver.extraClassPath", str(self.postgres_jdbc_jar))
            .config("spark.driver.memory", self.driver_memory)
            .config("spark.executor.memory", self.executor_memory)
            .config("spark.local.dir", self.spark_local_dir)
        )
        return builder.getOrCreate()
