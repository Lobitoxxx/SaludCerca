# ============================================================================
# SALUD CERCA - tests/test_derivacion.py
# ----------------------------------------------------------------------------
# Verifica el MOTOR DE DERIVACIÓN INTELIGENTE:
#   * integridad del dataset generado (0 derivaciones vacías/inválidas/no activas)
#   * función recomendar_derivacion contra la BD (integración, se salta si el
#     contenedor db no está disponible).
# ============================================================================

from __future__ import annotations

import csv as _csv
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]  # raíz del repositorio
CSV_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "output"

DB_USER = "saludcerca"
DB_NAME = "saludcerca"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _read_csv(name: str) -> list[dict]:
    with open(CSV_DIR / name, encoding="utf-8") as fh:
        return list(_csv.DictReader(fh))


def _db_ok() -> bool:
    if shutil.which("docker") is None:
        return False
    proc = subprocess.run(
        ["docker", "compose", "ps", "-q", "db"],
        cwd=ROOT, capture_output=True,
    )
    return proc.returncode == 0 and bool(proc.stdout.strip())


def _psql(query: str) -> list[list[str]]:
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "db",
         "psql", "-U", DB_USER, "-d", DB_NAME,
         "-tA", "-F", "|", "-c", query],
        cwd=ROOT, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"psql falló: {proc.stderr}")
    return [row.split("|") for row in proc.stdout.strip().splitlines() if row.strip()]


# ---------------------------------------------------------------------------
# 1) Integridad del dataset generado (sin BD, sin Spark)
# ---------------------------------------------------------------------------

def test_generador_derivaciones_validas() -> None:
    renipress = _read_csv("renipress.csv")
    his = _read_csv("his_atenciones.csv")
    categorias = {r["id"]: r for r in _read_csv("categorizaciones.csv")}

    estado = {r["codigo_renipress"]: r["estado_operativo"] for r in renipress}
    nivel = {r["codigo_renipress"]: int(categorias[r["categoria_id"]]["nivel_atencion"])
             for r in renipress}

    deriv = [r for r in his if r["estado_salida"] == "DERIVADO"]
    assert deriv, "no hay derivaciones en el dataset"

    assert sum(1 for r in deriv if not r["derivado_a"]) == 0, \
        "existen DERIVADO sin destino asignado"
    assert sum(1 for r in deriv if r["derivado_a"] not in estado) == 0, \
        "existen derivaciones a códigos inexistentes"
    assert sum(1 for r in deriv if estado.get(r["derivado_a"]) != "ACTIVO") == 0, \
        "existen derivaciones a IPRESS no ACTIVA"
    assert sum(1 for r in deriv
               if r["derivado_a"] and nivel.get(r["derivado_a"], 99) < nivel.get(r["codigo_ipress"], 0)) == 0, \
        "existen derivaciones a nivel menor que el origen"


# ---------------------------------------------------------------------------
# 2) Función recomendar_derivacion (integración con BD)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _db_ok(), reason="contenedor db no disponible")
def test_recomendar_retorna_candidatos_activos_ordenados() -> None:
    rows = _psql(
        "SELECT r.codigo_renipress, r.score FROM recomendar_derivacion("
        " (SELECT codigo_renipress FROM ipress WHERE estado_operativo='ACTIVO' ORDER BY id LIMIT 1),"
        " (SELECT id FROM especialidades ORDER BY id LIMIT 1), DATE '2024-12-31', 5) r"
    )
    assert rows, "el motor no retornó candidatos"

    codes = "','".join(r[0] for r in rows)
    inactivas = _psql(
        f"SELECT count(*) FROM ipress WHERE codigo_renipress IN ('{codes}')"
        f" AND estado_operativo <> 'ACTIVO'"
    )
    assert inactivas[0][0] == "0", "el motor retornó un destino NO ACTIVO"

    scores = [float(r[1]) for r in rows]
    assert scores == sorted(scores, reverse=True), "los candidatos no están ordenados por score"


@pytest.mark.skipif(not _db_ok(), reason="contenedor db no disponible")
def test_recomendar_no_incluye_origen() -> None:
    origen = _psql(
        "SELECT codigo_renipress FROM ipress WHERE estado_operativo='ACTIVO' ORDER BY id LIMIT 1"
    )[0][0]
    rows = _psql(
        f"SELECT codigo_renipress FROM recomendar_derivacion('{origen}', NULL, DATE '2024-12-31', 5)"
    )
    codes = [r[0] for r in rows]
    assert origen not in codes, "el motor retornó el propio origen"


@pytest.mark.skipif(not _db_ok(), reason="contenedor db no disponible")
def test_recomendar_respeta_nivel_de_especialidad() -> None:
    rows = _psql(
        "SELECT r.nivel_atencion FROM recomendar_derivacion("
        " (SELECT i.codigo_renipress FROM ipress i"
        "   JOIN categorizaciones c ON c.id = i.categoria_id"
        "  WHERE i.estado_operativo='ACTIVO' AND c.nivel_atencion=1 ORDER BY i.id LIMIT 1),"
        " (SELECT id FROM especialidades WHERE complejidad_minima=3 ORDER BY id LIMIT 1),"
        " DATE '2024-12-31', 5) r"
    )
    assert rows, "sin candidatos para origen de nivel 1 y especialidad de nivel 3"
    assert all(int(r[0]) >= 3 for r in rows), \
        "se retornaron destinos por debajo del nivel de la especialidad"
