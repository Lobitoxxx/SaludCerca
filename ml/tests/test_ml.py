# ============================================================================
# SALUD CERCA - ml/tests/test_ml.py
# ----------------------------------------------------------------------------
# Tests del módulo ML (sin BD): DBSCAN (sintético + Silver) y forecast.
#
#   pytest ml/tests
# ============================================================================

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from ml.clustering_dbscan import GeoClusterer  # noqa: E402
from ml.features import (  # noqa: E402
    cargar_ipress,
    serie_mensual_departamento,
    serie_mensual_total,
)
from ml.forecast import pronosticar_serie  # noqa: E402


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _ipress_sintetica() -> pd.DataFrame:
    """Dos clusters densos (Lima y Arequipa) + dos IPRESS aisladas."""
    rng = np.random.default_rng(7)
    limas = pd.DataFrame(
        {
            "codigo_renipress": [f"L{i:06d}" for i in range(6)],
            "nombre": "P.S. LIMA",
            "departamento": "LIMA",
            "latitud": -12.04 + rng.normal(0, 0.02, 6),
            "longitud": -77.02 + rng.normal(0, 0.02, 6),
            "capacidad_camas": [10] * 6,
            "capacidad_consultorios": [3] * 6,
        }
    )
    arequipa = pd.DataFrame(
        {
            "codigo_renipress": [f"A{i:06d}" for i in range(5)],
            "nombre": "P.S. AREQUIPA",
            "departamento": "AREQUIPA",
            "latitud": -16.40 + rng.normal(0, 0.02, 5),
            "longitud": -71.54 + rng.normal(0, 0.02, 5),
            "capacidad_camas": [8] * 5,
            "capacidad_consultorios": [2] * 5,
        }
    )
    aisladas = pd.DataFrame(
        {
            "codigo_renipress": ["X000001", "X000002"],
            "nombre": "P.S. AISLADO",
            "departamento": ["AMAZONAS", "MADRE DE DIOS"],
            "latitud": [-5.90, -12.59],
            "longitud": [-77.90, -69.18],
            "capacidad_camas": [2, 2],
            "capacidad_consultorios": [1, 1],
        }
    )
    return pd.concat([limas, arequipa, aisladas], ignore_index=True)


# ----------------------------------------------------------------------------
# DBSCAN
# ----------------------------------------------------------------------------

def test_dbscan_forma_dos_clusters_y_ruido():
    clusterer = GeoClusterer(eps_km=50.0, min_samples=2)
    resultado = clusterer.ajustar(_ipress_sintetica())
    agg, aisladas = clusterer.resumen(resultado)

    assert sorted(resultado["cluster_id"].unique()) == [-1, 0, 1]
    assert len(agg) == 2
    assert len(aisladas) == 2
    assert set(aisladas["codigo_renipress"]) == {"X000001", "X000002"}


def test_dbscan_cada_punto_tiene_vecino_dentro_de_eps():
    """Propiedad DBSCAN: todo punto no-ruido tiene un vecino a < eps (haversine)."""
    df = _ipress_sintetica()
    eps_km = 50.0
    clusterer = GeoClusterer(eps_km=eps_km, min_samples=2)
    resultado = clusterer.ajustar(df)

    coords = resultado[["latitud", "longitud"]].to_numpy() * (np.pi / 180.0)
    for i, cid in enumerate(resultado["cluster_id"]):
        if cid == -1:
            continue
        vecinos = 0
        for j in range(len(coords)):
            if i == j:
                continue
            dist_rad = np.arccos(
                np.clip(
                    np.sin(coords[i][0]) * np.sin(coords[j][0])
                    + np.cos(coords[i][0]) * np.cos(coords[j][0])
                    * np.cos(coords[i][1] - coords[j][1]),
                    -1.0, 1.0,
                )
            )
            if dist_rad * 6371.0088 < eps_km:
                vecinos += 1
        assert vecinos >= 1, "punto no-ruido sin vecino dentro de eps"


def test_dbscan_silver_ipress_activas():
    ipress = cargar_ipress()
    activas = ipress[
        (ipress["estado_operativo"] == "ACTIVO")
        & ipress["latitud"].notna()
        & ipress["longitud"].notna()
    ].copy()
    assert len(activas) == 1649

    clusterer = GeoClusterer(eps_km=25.0, min_samples=4)
    resultado = clusterer.ajustar(activas)
    agg, aisladas = clusterer.resumen(resultado)

    assert resultado["cluster_id"].notna().all()
    assert len(agg) >= 1
    assert "n_ipress" in agg.columns and "camas" in agg.columns
    assert (aisladas["cluster_id"] == -1).all()
    assert (agg["n_ipress"] >= 1).all()


# ----------------------------------------------------------------------------
# Features
# ----------------------------------------------------------------------------

def test_serie_mensual_total_12_meses():
    at = pd.read_parquet(PROJECT_ROOT / "data/lakehouse/silver/atenciones_silver")
    serie = serie_mensual_total(at)
    assert len(serie) == 12
    assert serie["ds"].is_monotonic_increasing
    assert (serie["y"] > 0).all()
    assert serie["y"].sum() == 349_887


def test_serie_mensual_departamento_top():
    at = pd.read_parquet(PROJECT_ROOT / "data/lakehouse/silver/atenciones_silver")
    ipress = cargar_ipress()
    serie = serie_mensual_departamento(at, ipress, top=5)
    assert list(serie.columns) == ["departamento", "ds", "y"]
    assert serie["departamento"].nunique() == 5
    assert serie["y"].notna().all()


# ----------------------------------------------------------------------------
# Forecast
# ----------------------------------------------------------------------------

def _serie_sintetica(meses: int = 36) -> pd.DataFrame:
    """Serie con tendencia lineal + estacionalidad anual."""
    ds = pd.date_range("2022-01-01", periods=meses, freq="MS")
    t = np.arange(meses)
    estacional = 400 * np.sin(2 * np.pi * (t / 12))
    y = 1000 + 50 * t + estacional + np.random.default_rng(3).normal(0, 30, meses)
    return pd.DataFrame({"ds": ds, "y": y})


def test_forecast_estructura_prophet():
    serie = _serie_sintetica()
    pronostico, modelo = pronosticar_serie(serie, horizon=12)
    assert list(pronostico.columns) == ["ds", "yhat", "yhat_lower", "yhat_upper"]
    assert len(pronostico) == 12
    assert (pronostico["yhat"] > 0).all()
    assert (pronostico["yhat_lower"] <= pronostico["yhat"]).all()
    assert (pronostico["yhat"] <= pronostico["yhat_upper"]).all()
    assert pronostico["ds"].iloc[0] == pd.Timestamp("2025-01-01")


def test_forecast_captura_tendencia():
    serie = _serie_sintetica()
    _, modelo = pronosticar_serie(serie, horizon=12)
    assert 20 < modelo.ajuste.slope < 80
    assert modelo.n_obs == 36


def test_forecast_determinista():
    serie = _serie_sintetica()
    p1, _ = pronosticar_serie(serie, horizon=12)
    p2, _ = pronosticar_serie(serie, horizon=12)
    pd.testing.assert_frame_equal(p1, p2)


def test_forecast_silver_total():
    at = pd.read_parquet(PROJECT_ROOT / "data/lakehouse/silver/atenciones_silver")
    serie = serie_mensual_total(at)
    pronostico, modelo = pronosticar_serie(serie, horizon=12)
    assert len(pronostico) == 12
    assert (pronostico["yhat"] > 0).all()
    assert (pronostico["yhat_lower"] <= pronostico["yhat"]).all()
    assert (pronostico["yhat"] <= pronostico["yhat_upper"]).all()
    assert modelo.n_obs == 12
    # El nivel pronosticado debe rondar el promedio observado (~29k/mes)
    assert 20_000 < pronostico["yhat"].mean() < 40_000
