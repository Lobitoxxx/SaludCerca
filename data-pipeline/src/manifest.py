# ============================================================================
# SALUD CERCA - src/manifest.py
# ----------------------------------------------------------------------------
# Versionado del Data Lakehouse: escribe data/lakehouse/MANIFEST.json con el
# estado de cada etapa (Bronze/Silver/Gold), los conteos, el commit de git y
# la fecha de generación. Permite auditar qué datos hay en cada capa y
# reproducir el pipeline (traza de procedencia).
# ============================================================================

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pyspark.sql import SparkSession

from config import PROJECT_ROOT, PipelineConfig

# Versión del esquema del lakehouse (bump al cambiar el layout de capas)
ESQUEMA_VERSION = "1.0.0"


def _git_commit() -> Optional[str]:
    """SHA corto del commit actual (o None si no hay repo/commit)."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=5,
        )
        if proc.returncode == 0:
            return proc.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _conteos_parquet(spark: SparkSession, cfg: PipelineConfig, etapa: str) -> Dict[str, int]:
    """Lee los conteos reales de la capa indicada (traza verificable)."""
    if etapa == "bronze":
        return {
            "renipress": spark.read.parquet(str(cfg.bronze_dir / "renipress")).count(),
            "his": spark.read.parquet(str(cfg.bronze_dir / "his")).count(),
            "ubigeo": spark.read.parquet(str(cfg.bronze_dir / "ubigeo")).count(),
        }
    if etapa == "silver":
        return {
            "ipress": spark.read.parquet(str(cfg.silver_dir / "ipress_silver.parquet")).count(),
            "atenciones": spark.read.parquet(str(cfg.silver_dir / "atenciones_silver")).count(),
        }
    return {}


def escribir_manifest(
    spark: SparkSession,
    cfg: PipelineConfig,
    etapa: str,
    conteos: Dict[str, Any],
) -> Path:
    """Actualiza (o crea) MANIFEST.json con el estado de una etapa.

    Args:
        etapa: 'bronze' | 'silver' | 'gold'
        conteos: dict con los conteos reportados por la etapa.
    """
    ruta = cfg.lakehouse_dir / "MANIFEST.json"

    manifiesto: Dict[str, Any] = {"esquema": ESQUEMA_VERSION, "etapas": {}}
    if ruta.exists():
        manifiesto = json.loads(ruta.read_text(encoding="utf-8"))

    manifiesto["fecha_generacion"] = datetime.now(timezone.utc).isoformat()
    manifiesto["git_commit"] = _git_commit() or manifiesto.get("git_commit")

    # Normalización: la clave del conteo de atenciones es siempre "atenciones"
    if "his" in conteos and "atenciones" not in conteos:
        conteos = dict(conteos)
        conteos["atenciones"] = conteos.pop("his")

    manifiesto["etapas"][etapa] = {
        "conteos": conteos,
        "verificado": _conteos_parquet(spark, cfg, etapa),
    }

    ruta.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[manifest] MANIFEST.json actualizado (etapa={etapa})")
    return ruta
