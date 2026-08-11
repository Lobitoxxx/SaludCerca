# ============================================================================
# SALUD CERCA - Orquestador del pipeline Medallón
# ----------------------------------------------------------------------------
# Ejecución por etapas (Bronze -> Silver -> Gold) de un solo comando:
#
#   python main.py                     # ejecuta las 3 etapas (all)
#   python main.py --stage bronze      # solo ingesta a capa Bronze
#   python main.py --stage silver      # solo limpieza + Parquet Silver
#   python main.py --stage gold        # solo UPSERT a PostgreSQL/PostGIS
#
# Requiere que PostgreSQL + PostGIS esté arriba para la etapa gold:
#   docker compose up -d db
# ============================================================================

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permitir importar los módulos de src/ como paquetes de primer nivel
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from bronze import run_bronze       # noqa: E402
from config import PipelineConfig   # noqa: E402
from gold import run_gold           # noqa: E402
from manifest import escribir_manifest  # noqa: E402
from silver import run_silver       # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline SALUD CERCA (Medallón: Bronze/Silver/Gold)"
    )
    parser.add_argument(
        "--stage",
        choices=["bronze", "silver", "gold", "all"],
        default="all",
        help="Etapa del pipeline a ejecutar (default: all)",
    )
    args = parser.parse_args()

    cfg = PipelineConfig()
    spark = cfg.spark()
    spark.sparkContext.setLogLevel("ERROR")  # reducir ruido de INFO

    try:
        if args.stage in ("bronze", "all"):
            print("=" * 70)
            print("[ETAPA 1/3] INGESTA -> CAPA BRONZE (Parquet crudo)")
            print("=" * 70)
            conteos = run_bronze(spark, cfg)
            escribir_manifest(spark, cfg, "bronze", conteos)

        if args.stage in ("silver", "all"):
            print("=" * 70)
            print("[ETAPA 2/3] LIMPIEZA -> CAPA SILVER (Parquet limpio)")
            print("=" * 70)
            conteos = run_silver(spark, cfg)
            escribir_manifest(spark, cfg, "silver", conteos)

        if args.stage in ("gold", "all"):
            print("=" * 70)
            print("[ETAPA 3/3] CARGA -> CAPA GOLD (PostgreSQL + PostGIS)")
            print("=" * 70)
            conteos = run_gold(spark, cfg)
            escribir_manifest(spark, cfg, "gold", conteos)

        print("=" * 70)
        print("Pipeline finalizado correctamente.")
        print("=" * 70)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
