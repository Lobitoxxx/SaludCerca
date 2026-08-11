# ============================================================================
# SALUD CERCA - ml/main.py
# ----------------------------------------------------------------------------
# Orquestador del módulo ML. Ejecuta sobre la capa SILVER del lakehouse:
#
#   python ml/main.py                          # default: eps=25km, min=4, h=12
#   python ml/main.py --eps-km 20 --min-samples 3 --horizon 12
#
# Salidas (en data/lakehouse/ml/):
#   * clusters_ipress.csv                 # cluster_id por IPRESS activa
#   * resumen_clusters.csv                # agregados por cluster
#   * clusters_ipress.png                 # mapa de dispersión coloreado
#   * atenciones_mensual.csv              # serie observada
#   * forecast_atenciones_total.csv       # pronóstico 2025 (formato Prophet)
#   * forecast_atenciones_departamento.csv
#   * forecast_total.png                  # observado + pronóstico + banda
# ============================================================================

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from clustering_dbscan import GeoClusterer  # noqa: E402
from features import (  # noqa: E402
    cargar_atenciones,
    cargar_ipress,
    serie_mensual_departamento,
    serie_mensual_total,
)
from forecast import pronosticar_departamentos, pronosticar_serie  # noqa: E402

# Directorio raíz del proyecto (dos niveles arriba de este archivo)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def ejecutar_clustering(
    ipress, eps_km: float, min_samples: int, output_dir: Path
) -> None:
    print("=" * 70)
    print("[ML 1/2] CLUSTERING DBSCAN DE IPRESS ACTIVAS (haversine)")
    print("=" * 70)

    activas = ipress[
        (ipress["estado_operativo"] == "ACTIVO")
        & ipress["latitud"].notna()
        & ipress["longitud"].notna()
    ].copy()
    print(f"IPRESS ACTIVAS con coordenadas: {len(activas)}")

    clusterer = GeoClusterer(eps_km=eps_km, min_samples=min_samples)
    clustered = clusterer.ajustar(activas)
    agg, aisladas = clusterer.resumen(clustered)

    n_clusters = len(agg)
    n_aisladas = len(aisladas)
    n_core = len(clustered) - n_aisladas
    print(f"Clusters formados: {n_clusters} | IPRESS en clusters: {n_core} "
          f"({100 * n_core / len(clustered):.1f}%)")
    print(f"IPRESS aisladas (ruido -> brecha potencial): {n_aisladas} "
          f"({100 * n_aisladas / len(clustered):.1f}%)")
    if not agg.empty:
        top = agg.iloc[0]
        print(f"Cluster más grande: {top['n_ipress']} IPRESS "
              f"(deptos: {top['departamentos']})")

    clustered[["codigo_renipress", "nombre", "departamento", "provincia",
               "distrito", "latitud", "longitud", "capacidad_camas",
               "cluster_id"]].sort_values("cluster_id").to_csv(
        output_dir / "clusters_ipress.csv", index=False
    )
    agg.to_csv(output_dir / "resumen_clusters.csv", index=False)

    # Gráfico de dispersión coloreado por cluster
    fig, ax = plt.subplots(figsize=(9, 6))
    for cid in sorted(clustered["cluster_id"].unique()):
        sub = clustered[clustered["cluster_id"] == cid]
        if cid == -1:
            ax.scatter(sub["longitud"], sub["latitud"], s=12, c="black",
                       marker="x", label=f"aislada (n={len(sub)})")
        else:
            ax.scatter(sub["longitud"], sub["latitud"], s=14, alpha=0.7,
                       label=f"cluster {cid} (n={len(sub)})")
    ax.set_title(f"DBSCAN IPRESS activas (eps={eps_km} km, min_samples={min_samples})")
    ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud")
    ax.legend(fontsize=7, loc="lower left", ncol=2)
    fig.tight_layout()
    fig.savefig(output_dir / "clusters_ipress.png", dpi=130)
    plt.close(fig)
    print(f"Exportado -> {output_dir / 'clusters_ipress.csv'}")
    print(f"Exportado -> {output_dir / 'resumen_clusters.csv'}")
    print(f"Exportado -> {output_dir / 'clusters_ipress.png'}")


def ejecutar_forecast(atenciones, ipress, horizon: int, top: int, output_dir: Path) -> None:
    print("=" * 70)
    print("[ML 2/2] FORECAST MENSUAL (tendencia + estacionalidad, estilo Prophet)")
    print("=" * 70)

    total = serie_mensual_total(atenciones)
    total.to_csv(output_dir / "atenciones_mensual.csv", index=False)
    print(f"Serie observada (meses): {len(total)} -> atenciones_mensual.csv")

    pronostico, modelo = pronosticar_serie(total, horizon=horizon)
    pronostico.to_csv(output_dir / "forecast_atenciones_total.csv", index=False)
    print(f"Pronóstico total {horizon} meses: "
          f"{pronostico['yhat'].iloc[0]:,.0f} -> {pronostico['yhat'].iloc[-1]:,.0f} "
          f"atenciones/mes")
    print(f"RMSE in-sample: {modelo.ajuste.rmse:,.1f} | "
          f"MAPE: {modelo.ajuste.mape:.2f}% | "
          f"pendiente tendencia: {modelo.ajuste.slope:+.1f} atenciones/mes")
    if not modelo.ajuste.estacionalidad.empty:
        max_mes = modelo.ajuste.estacionalidad.idxmax()
        print(f"Estacionalidad pico: {max_mes}")

    deptos = serie_mensual_departamento(atenciones, ipress, top=top)
    print(f"Departamentos pronosticados: {sorted(deptos['departamento'].unique())}")
    pronostico_deptos = pronosticar_departamentos(deptos, horizon=horizon)
    pronostico_deptos.to_csv(
        output_dir / "forecast_atenciones_departamento.csv", index=False
    )

    # Gráfico observado + pronóstico
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(total["ds"], total["y"], "o-", label="observado (2024)")
    ax.plot(pronostico["ds"], pronostico["yhat"], "s--", label="pronóstico")
    ax.fill_between(
        pronostico["ds"], pronostico["yhat_lower"], pronostico["yhat_upper"],
        alpha=0.2, label="banda 80%",
    )
    ax.set_title("Atenciones HIS mensuales: observado vs pronóstico")
    ax.set_xlabel("Mes"); ax.set_ylabel("Atenciones")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "forecast_total.png", dpi=130)
    plt.close(fig)
    print(f"Exportado -> {output_dir / 'forecast_total.png'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Módulo ML de SALUD CERCA (DBSCAN + forecast sobre Silver)"
    )
    parser.add_argument("--eps-km", type=float, default=25.0,
                        help="Radio de vecindad DBSCAN en km (default 25)")
    parser.add_argument("--min-samples", type=int, default=4,
                        help="Mínimo de IPRESS por cluster (default 4)")
    parser.add_argument("--horizon", type=int, default=12,
                        help="Meses a pronosticar (default 12)")
    parser.add_argument("--top-departamentos", type=int, default=8,
                        help="N° de departamentos a pronosticar (default 8)")
    parser.add_argument("--output-dir", type=Path,
                        default=PROJECT_ROOT / "data" / "lakehouse" / "ml",
                        help="Directorio de salida de artefactos")
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    ipress = cargar_ipress()
    atenciones = cargar_atenciones()

    ejecutar_clustering(ipress, args.eps_km, args.min_samples, output_dir)
    ejecutar_forecast(
        atenciones, ipress, args.horizon, args.top_departamentos, output_dir
    )

    print("=" * 70)
    print("Módulo ML finalizado correctamente.")
    print("=" * 70)


if __name__ == "__main__":
    main()
