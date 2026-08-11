# ============================================================================
# SALUD CERCA - qa/run_qa_derivaciones.py
# ----------------------------------------------------------------------------
# Ejecuta la suite de control de calidad del MOTOR DE DERIVACIÓN INTELIGENTE
# (qa/check_derivaciones.sql) contra PostgreSQL + PostGIS + pgvector en Docker.
#
#   Uso:
#     python qa/run_qa_derivaciones.py   # valida y sale con exit code 0/1
#
# Requiere el contenedor arriba y db/init/07_derivacion.sql aplicado:
#   docker compose up -d --build db
# ============================================================================

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = Path(__file__).resolve().parent / "check_derivaciones.sql"

DB_USER = "saludcerca"
DB_NAME = "saludcerca"


def run() -> int:
    print("=" * 70)
    print("QA SALUD CERCA - Motor de derivación inteligente")
    print("=" * 70)
    print(f"  contenedor : saludcerca-db")
    print(f"  script     : {SQL_FILE.name}")
    print("-" * 70)

    cmd = [
        "docker", "compose", "exec", "-T", "db",
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-v", "ON_ERROR_STOP=1",
        "-f", "/dev/stdin",
    ]
    proc = subprocess.run(
        cmd,
        input=SQL_FILE.read_bytes(),
        capture_output=True,
        text=False,
        cwd=ROOT,
    )

    salida = (proc.stdout or b"").decode("utf-8", errors="replace")
    errores = (proc.stderr or b"").decode("utf-8", errors="replace")
    for line in (salida + errores).splitlines():
        line = line.strip()
        if line:
            print(f"  {line}")

    if proc.returncode == 0:
        print("-" * 70)
        print("RESULTADO: OK - la red de derivaciones está sana y el motor responde")
        print("=" * 70)
    else:
        print("-" * 70)
        print("RESULTADO: FALLIDO - revisar las validaciones anteriores")
        print("=" * 70)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(run())
