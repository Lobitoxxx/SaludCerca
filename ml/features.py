# ============================================================================
# SALUD CERCA - ml/features.py
# ----------------------------------------------------------------------------
# Carga de características desde la capa SILVER del lakehouse (Parquet):
#   * IPRESS limpias (con coordenadas y estado operativo)
#   * Serie mensual de atenciones (total y por departamento)
# ============================================================================

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Directorio raíz del proyecto (dos niveles arriba de este archivo)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

SILVER_DIR = PROJECT_ROOT / "data" / "lakehouse" / "silver"


def cargar_ipress(silver_dir: Path = SILVER_DIR) -> pd.DataFrame:
    """Devuelve la capa Silver de IPRESS como DataFrame."""
    df = pd.read_parquet(silver_dir / "ipress_silver.parquet")
    return df


def cargar_atenciones(silver_dir: Path = SILVER_DIR) -> pd.DataFrame:
    """Devuelve la capa Silver de atenciones HIS como DataFrame."""
    return pd.read_parquet(silver_dir / "atenciones_silver")


def serie_mensual_total(atenciones: pd.DataFrame) -> pd.DataFrame:
    """Agrega atenciones por mes (fecha a primer día del mes).

    Devuelve un DataFrame con columnas `ds` (datetime) y `y` (conteo).
    """
    serie = (
        atenciones.groupby(["anio", "mes"], sort=True)
        .size()
        .reset_index(name="y")
    )
    serie["ds"] = pd.to_datetime(
        serie["anio"].astype(str) + "-" + serie["mes"].astype(str).str.zfill(2) + "-01"
    )
    serie = serie[["ds", "y"]].sort_values("ds").reset_index(drop=True)
    return serie


def serie_mensual_departamento(
    atenciones: pd.DataFrame, ipress: pd.DataFrame, top: int = 8
) -> pd.DataFrame:
    """Serie mensual por departamento, limitada a los `top` con más atenciones.

    Une atenciones -> ipress por `ipress_id` para conocer el departamento.
    Devuelve columnas `departamento`, `ds`, `y`.
    """
    if "departamento" not in atenciones.columns:
        merge = atenciones.merge(
            ipress[["id", "departamento"]],
            left_on="ipress_id",
            right_on="id",
            how="left",
        )
    else:
        merge = atenciones

    merge["ds"] = pd.to_datetime(
        merge["anio"].astype(str) + "-" + merge["mes"].astype(str).str.zfill(2) + "-01"
    )
    agg = merge.groupby(["departamento", "ds"]).size().reset_index(name="y")

    top_deptos = (
        agg.groupby("departamento")["y"].sum().sort_values(ascending=False).head(top).index
    )
    return agg[agg["departamento"].isin(top_deptos)].sort_values(
        ["departamento", "ds"]
    ).reset_index(drop=True)
