# ============================================================================
# SALUD CERCA - ml/forecast.py
# ----------------------------------------------------------------------------
# Modelo aditivo de tendencia lineal + estacionalidad mensual (estilo Prophet)
# ajustado por mínimos cuadrados:
#
#     y = a + b*t + Σ_m d_m * I(mes=m) + ε
#
# Determinista y liviano (OLS cerrado con numpy). La API replica a Prophet
# (ds / yhat / yhat_lower / yhat_upper) para que sea intercambiable por una
# implementación real de Prophet en producción.
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class AjusteModelo:
    """Resultado del ajuste de una serie."""

    yhat: pd.Series
    residuos: np.ndarray
    rmse: float
    mape: float
    slope: float
    intercepto: float
    estacionalidad: pd.Series
    n_obs: int


class SeasonalTrendModel:
    """Tendencia lineal + estacionalidad mensual por OLS.

    Args:
        nivel_conf: nivel de confianza de la banda de predicción (default 0.8).
    """

    def __init__(self, nivel_conf: float = 0.8) -> None:
        self.nivel_conf = nivel_conf
        self._ds: Optional[pd.Series] = None
        self._coefs: Optional[np.ndarray] = None
        self._sigma: float = 0.0
        self._n_obs: int = 0
        self.ajuste: Optional[AjusteModelo] = None

    # ------------------------------------------------------------------
    # Construcción de la matriz de diseño (intercepto, tendencia, meses 2..12)
    @staticmethod
    def _disenio(fechas: np.ndarray) -> np.ndarray:
        n = len(fechas)
        meses = pd.DatetimeIndex(fechas).month.to_numpy(dtype=int)
        dummies = np.zeros((n, 11), dtype=float)
        for j, mes in enumerate(range(2, 13)):
            dummies[:, j] = (meses == mes).astype(float)
        t = np.arange(n)
        return np.column_stack([np.ones(n), t, dummies])

    # ------------------------------------------------------------------
    def fit(self, df: pd.DataFrame) -> "SeasonalTrendModel":
        """Ajusta el modelo sobre un DataFrame con `ds` (datetime) e `y`."""
        df = df.copy().sort_values("ds").reset_index(drop=True)
        y = df["y"].to_numpy(dtype=float)
        fechas = pd.to_datetime(df["ds"]).to_numpy()
        self._n_obs = len(y)

        if self._n_obs < 3:
            raise ValueError("Se necesitan al menos 3 observaciones para ajustar")

        X = self._disenio(fechas)
        coefs, *_ = np.linalg.lstsq(X, y, rcond=None)
        yhat = X @ coefs
        residuos = y - yhat

        # varianza residual con corrección de grados de libertad. Con pocas
        # observaciones (p.ej. 1 año) el modelo queda saturado (RMSE ~0); se
        # impone un piso de 2% del nivel medio para que la banda sea informativa.
        dof = max(1, self._n_obs - X.shape[1])
        sigma = float(np.sqrt(np.sum(residuos ** 2) / dof))
        self._sigma = max(sigma, 0.02 * float(np.mean(y)))
        self._coefs = coefs
        self._ds = pd.Series(fechas)

        mape = float(np.mean(np.abs(residuos) / np.where(y == 0, 1, np.abs(y))) * 100)
        self.ajuste = AjusteModelo(
            yhat=pd.Series(yhat, index=df.index),
            residuos=residuos,
            rmse=float(np.sqrt(np.mean(residuos ** 2))),
            mape=mape,
            slope=float(coefs[1]),
            intercepto=float(coefs[0]),
            estacionalidad=pd.Series(
                coefs[2:], index=[f"mes_{m}" for m in range(2, 13)]
            ),
            n_obs=self._n_obs,
        )
        return self

    # ------------------------------------------------------------------
    def predict(self, horizon: int = 12) -> pd.DataFrame:
        """Pronostica `horizon` meses siguientes (formato Prophet).

        Returns:
            DataFrame con ds, yhat, yhat_lower, yhat_upper.
        """
        if self._coefs is None or self._ds is None:
            raise RuntimeError("Debe llamar a fit() antes de predict()")

        ultima = self._ds.iloc[-1]
        futuras = pd.date_range(
            start=ultima + pd.offsets.MonthBegin(1),
            periods=horizon,
            freq="MS",
        )
        X_fut = self._disenio(futuras.to_numpy())
        yhat = X_fut @ self._coefs

        z = float(stats.norm.ppf(0.5 + self.nivel_conf / 2.0))
        return pd.DataFrame(
            {
                "ds": futuras,
                "yhat": yhat,
                "yhat_lower": yhat - z * self._sigma,
                "yhat_upper": yhat + z * self._sigma,
            }
        )

    # ------------------------------------------------------------------
    @property
    def n_obs(self) -> int:
        return self._n_obs


def pronosticar_serie(
    serie: pd.DataFrame,
    horizon: int = 12,
    nivel_conf: float = 0.8,
) -> Tuple[pd.DataFrame, SeasonalTrendModel]:
    """Ajusta el modelo a `serie` (ds/y) y devuelve (pronóstico, modelo)."""
    modelo = SeasonalTrendModel(nivel_conf=nivel_conf).fit(serie)
    return modelo.predict(horizon), modelo


def pronosticar_departamentos(
    serie_deptos: pd.DataFrame,
    departamentos: Optional[List[str]] = None,
    horizon: int = 12,
) -> pd.DataFrame:
    """Pronostica por departamento y devuelve un DataFrame apilado."""
    if departamentos is None:
        departamentos = sorted(serie_deptos["departamento"].unique())

    piezas: List[pd.DataFrame] = []
    for depto in departamentos:
        sub = serie_deptos[serie_deptos["departamento"] == depto]
        if len(sub) < 3:
            continue
        pronostico, _ = pronosticar_serie(sub[["ds", "y"]], horizon=horizon)
        pronostico.insert(0, "departamento", depto)
        piezas.append(pronostico)

    if not piezas:
        raise ValueError("No hay departamentos suficientes para pronosticar")
    return pd.concat(piezas, ignore_index=True)
