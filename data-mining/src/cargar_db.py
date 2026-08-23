"""Carga data/ipress_master.csv al PostgreSQL del Docker (COPY desde stdin)."""
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(RAIZ, "data", "ipress_master.csv")
SQL_ESQUEMA = os.path.normpath(os.path.join(RAIZ, "..", "db", "init",
                                            "10_ipress_master.sql"))

COLUMNAS = ("codigo_renipress, nombre, nombre_norm, tipo, sector, clasificacion,"
            " categoria, departamento, provincia, distrito, ubigeo, direccion,"
            " telefono, horario, abierto_24h, latitud, longitud, osm_id,"
            " fuente, confianza, verificacion, activo")

PSQL = ["docker", "compose", "exec", "-T", "db", "psql",
        "-U", "saludcerca", "-d", "saludcerca", "-v", "ON_ERROR_STOP=1"]
# El comando debe ejecutarse donde está docker-compose.yml (raíz del repo)
CWD = os.path.normpath(os.path.join(RAIZ, ".."))


def _ejecutar(args, **kwargs):
    resultado = subprocess.run(args, capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               cwd=CWD, **kwargs)
    if resultado.returncode != 0:
        sys.stderr.write(resultado.stdout + "\n" + resultado.stderr + "\n")
        raise SystemExit(f"Fallo: {' '.join(args)}")
    return resultado.stdout


def main():
    if not os.path.exists(CSV):
        raise SystemExit("No existe ipress_master.csv; corre build_master.py")

    if os.path.exists(SQL_ESQUEMA):
        print("Aplicando esquema 10_ipress_master.sql...")
        with open(SQL_ESQUEMA, encoding="utf-8") as f:
            _ejecutar(PSQL + ["-f", "-"], stdin=f)

    print("Truncando tabla...")
    _ejecutar(PSQL + ["-c", "TRUNCATE ipress_master RESTART IDENTITY CASCADE;"])

    print("Importando CSV desde stdin...")
    with open(CSV, encoding="utf-8") as f:
        _ejecutar(PSQL + [
            "-c",
            f"\\copy ipress_master ({COLUMNAS}) FROM STDIN "
            f"WITH (FORMAT csv, HEADER true)",
        ], stdin=f)

    out = _ejecutar(PSQL + [
        "-c",
        "SELECT count(*) AS total FROM ipress_master;"
        " SELECT count(*) FILTER (WHERE geom IS NOT NULL) AS con_geo,"
        "        count(*) FILTER (WHERE activo) AS activos,"
        "        count(*) FILTER (WHERE fuente='MIXTO') AS mixtos"
        "   FROM ipress_master;",
    ])
    print(out)


if __name__ == "__main__":
    main()
