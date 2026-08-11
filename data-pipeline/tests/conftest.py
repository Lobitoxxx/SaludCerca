# ============================================================================
# SALUD CERCA - tests/conftest.py
# ----------------------------------------------------------------------------
# Fixtures compartidas: SparkSession local y configuración del pipeline.
# ============================================================================

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# src/ es hermano de tests/ -> permitir importar bronze, cleaning, config, ...
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from config import PipelineConfig  # noqa: E402


@pytest.fixture(scope="session")
def cfg() -> PipelineConfig:
    """Configuración real del pipeline (rutas del lakehouse + BD)."""
    return PipelineConfig()


@pytest.fixture(scope="session")
def spark():
    """SparkSession ligera para tests (sin el driver JDBC ni memoria pesada)."""
    from pyspark.sql import SparkSession

    session = (
        SparkSession.builder.master("local[2]")
        .appName("saludcerca-tests")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.driver.memory", "1g")
        .config("spark.executor.memory", "1g")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()
