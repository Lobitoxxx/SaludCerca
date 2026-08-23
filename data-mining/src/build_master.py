"""CLI: construye data/ipress_master.csv (RENIPRESS + OSM fusionados)."""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from matching import fusionar  # noqa: E402
from overpass import descargar_overpass, extraer_pois  # noqa: E402
from renipress import CAMPOS_SALIDA, leer_renipress  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RAIZ, "data")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--renipress",
                        default=os.path.join(DATA, "renipress_2026-07.csv"))
    parser.add_argument("--osm-cache",
                        default=os.path.join(DATA, "osm_peru_health.json"))
    parser.add_argument("--out",
                        default=os.path.join(DATA, "ipress_master.csv"))
    parser.add_argument("--sin-osm", action="store_true",
                        help="omitir la descarga OSM (solo RENIPRESS)")
    args = parser.parse_args()

    registros = leer_renipress(args.renipress)
    con_geo = sum(1 for r in registros if r["latitud"] is not None)
    activos = sum(1 for r in registros if r["activo"])
    print(f"RENIPRESS: {len(registros)} registros "
          f"({activos} activos, {con_geo} con geo)")

    if not args.sin_osm:
        datos = descargar_overpass(args.osm_cache)
        pois = extraer_pois(datos)
        print(f"OSM: {len(pois)} POIs de salud")
        sin_match, stats = fusionar(registros, pois)
        print(f"Match: {stats['matches']} fusionados, "
              f"{stats['osm_nuevos']} nuevos desde OSM")
        registros.extend(sin_match)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_SALIDA)
        writer.writeheader()
        for reg in registros:
            fila = {k: reg.get(k, "") for k in CAMPOS_SALIDA}
            if fila["latitud"] is None:
                fila["latitud"], fila["longitud"] = "", ""
            writer.writerow(fila)

    total_geo = sum(1 for r in registros if r["latitud"] is not None)
    print(f"MASTER: {len(registros)} establecimientos -> {args.out} "
          f"({total_geo} con geo)")


if __name__ == "__main__":
    main()
