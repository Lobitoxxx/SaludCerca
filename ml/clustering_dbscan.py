# ============================================================================
# SALUD CERCA - ml/clustering_dbscan.py
# ----------------------------------------------------------------------------
# Clustering geoespacial de IPRESS activas con DBSCAN (distancia haversine).
#
# Utilidad para la planificación de red:
#   * Grupos densos  -> polos de oferta de salud (clusters)
#   * Puntos aislados -> IPRESS solitarias -> candidatas a "desiertos sanitarios"
# ============================================================================

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

# Radio medio de la Tierra (km) para convertir la métrica haversine
RADIO_TIERRA_KM = 6371.0088


class GeoClusterer:
    """DBSCAN sobre (lat, lon) con distancia haversine en kilómetros.

    Args:
        eps_km: radio de vecindad (km). Valor típico 25 km (ámbito distrital).
        min_samples: n° mínimo de IPRESS para formar un cluster (core).
    """

    def __init__(self, eps_km: float = 25.0, min_samples: int = 4) -> None:
        if eps_km <= 0:
            raise ValueError("eps_km debe ser > 0")
        self.eps_km = eps_km
        self.eps_rad = eps_km / RADIO_TIERRA_KM
        self.min_samples = min_samples

    def ajustar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ajusta DBSCAN sobre las columnas `latitud`/`longitud`.

        Agrega la columna `cluster_id` (-1 = ruido / IPRESS aislada).
        """
        coords = df[["latitud", "longitud"]].to_numpy() * (np.pi / 180.0)
        labels = DBSCAN(
            eps=self.eps_rad,
            min_samples=self.min_samples,
            metric="haversine",
        ).fit_predict(coords)

        out = df.copy()
        out["cluster_id"] = labels
        return out

    @staticmethod
    def resumen(clustered: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Resumen de clusters y listado de IPRESS aisladas (ruido).

        Returns:
            (agg, aisladas): agregado por cluster (n, capacidad, centroide,
            departamentos) y subconjunto con cluster_id == -1.
        """
        core = clustered[clustered["cluster_id"] >= 0]
        agg = (
            core.groupby("cluster_id")
            .agg(
                n_ipress=("codigo_renipress", "count"),
                camas=("capacidad_camas", "sum"),
                consultorios=("capacidad_consultorios", "sum"),
                lat_centroide=("latitud", "mean"),
                lon_centroide=("longitud", "mean"),
                departamentos=("departamento", lambda s: ",".join(sorted(set(s)))),
            )
            .sort_values("n_ipress", ascending=False)
            .reset_index()
        )
        aisladas = clustered[clustered["cluster_id"] == -1].copy()
        return agg, aisladas
