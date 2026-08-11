# ============================================================================
# SALUD CERCA - qa/test_idempotencia.py
# ----------------------------------------------------------------------------
# Verifica que re-ejecutar el pipeline NO corrompe la capa Gold:
#   * ejecuta el pipeline completo (bronze+silver+gold)
#   * re-ejecuta gold (MERGE/DELETE+INSERT del mismo rango)
#   * los conteos de la BD deben permanecer idénticos en cada snapshot
#
#   Uso:
#     python qa/test_idempotencia.py
#
# Requiere: contenedor db arriba, JAVA/HADOOP configurados y python con PySpark.
# ============================================================================

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = ROOT / "data-pipeline"
DB_USER = "saludcerca"
DB_NAME = "saludcerca"

JAVA_HOME = os.getenv("JAVA_HOME", r"C:\Program Files\Eclipse Adoptium\jdk-17.0.20.8-hotspot")
HADOOP_HOME = os.getenv("HADOOP_HOME", r"C:\Users\luis6\AppData\Local\hadoop-win")

SNAPSHOT_SQL = """
SELECT
    (SELECT count(*) FROM ipress),
    (SELECT count(*) FROM atenciones_his),
    (SELECT count(*) FROM fact_atenciones_medicas),
    (SELECT count(*) FROM dim_ipress),
    (SELECT count(*) FROM dim_tiempo);
"""


def snapshot_db() -> tuple[int, ...]:
    """Lee los conteos de la BD (devuelve tupla ordenada)."""
    cmd = [
        "docker", "compose", "exec", "-T", "db",
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-tA", "-F", "|", "-c", SNAPSHOT_SQL,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if proc.returncode != 0:
        raise RuntimeError(f"No se pudo consultar la BD:\n{proc.stderr}")
    return tuple(int(x) for x in proc.stdout.strip().split("|") if x.strip() != "")


def run_pipeline(stage: str) -> None:
    """Ejecuta una etapa del pipeline con el entorno Java/Hadoop."""
    env = dict(os.environ)
    env["JAVA_HOME"] = JAVA_HOME
    env["HADOOP_HOME"] = HADOOP_HOME
    env["PATH"] = os.pathsep.join(
        [str(Path(JAVA_HOME) / "bin"), str(Path(HADOOP_HOME) / "bin"), env.get("PATH", "")]
    )
    print(f"  >> python main.py --stage {stage}")
    proc = subprocess.run(
        [sys.executable, "main.py", "--stage", stage],
        cwd=PIPELINE_DIR,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Pipeline falló en la etapa {stage} (exit={proc.returncode})")


def main() -> int:
    print("=" * 70)
    print("QA SALUD CERCA - Test de idempotencia end-to-end")
    print("=" * 70)

    s0 = snapshot_db()
    print(f"  snapshot inicial   : {s0}")

    print("-" * 70)
    print("  Paso 1: ejecutar pipeline completo (bronze+silver+gold)")
    run_pipeline("all")
    s1 = snapshot_db()
    print(f"  snapshot tras 'all': {s1}")

    print("-" * 70)
    print("  Paso 2: re-ejecutar gold (MERGE idempotente)")
    run_pipeline("gold")
    s2 = snapshot_db()
    print(f"  snapshot tras gold : {s2}")

    print("-" * 70)
    if s0 == s1 == s2:
        print("RESULTADO: OK - el pipeline es idempotente (conteos idénticos)")
        print(f"           {s0}")
        print("=" * 70)
        return 0

    print("RESULTADO: FALLIDO - los conteos cambiaron entre ejecuciones:")
    print(f"           inicial={s0}  tras_all={s1}  tras_gold={s2}")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
