"""Lectura y normalización del CSV oficial RENIPRESS (delimitador ';')."""
import csv

from normalizacion import (
    clasificar_tipo,
    es_activo,
    horario_24h,
    normalizar_nombre,
    parse_par_coords,
    sector_de,
)

CAMPOS_SALIDA = [
    "codigo_renipress", "nombre", "nombre_norm", "tipo", "sector",
    "clasificacion", "categoria", "departamento", "provincia", "distrito",
    "ubigeo", "direccion", "telefono", "horario", "abierto_24h",
    "latitud", "longitud", "osm_id", "fuente", "confianza",
    "verificacion", "activo",
]


def _limpiar(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def leer_renipress(ruta_csv):
    """Genera registros normalizados desde el CSV RENIPRESS."""
    registros = []
    with open(ruta_csv, encoding="utf-8-sig", errors="replace") as f:
        for fila in csv.DictReader(f, delimiter=";"):
            nombre = _limpiar(fila.get("NOMBRE"))
            if not nombre:
                continue
            lat, lon = parse_par_coords(fila.get("NORTE"), fila.get("ESTE"))
            telefono = _limpiar(fila.get("TELEFONO"))
            if normalizar_nombre(telefono) in ("NO CUENTA CON TELEFONO", ""):
                telefono = ""
            horario = _limpiar(fila.get("HORARIO"))
            clasificacion = _limpiar(fila.get("CLASIFICACION"))
            institucion = _limpiar(fila.get("INSTITUCION"))
            registros.append({
                "codigo_renipress": _limpiar(fila.get("COD_IPRESS")),
                "nombre": nombre,
                "nombre_norm": normalizar_nombre(nombre),
                "tipo": clasificar_tipo(clasificacion, institucion),
                "sector": sector_de(institucion),
                "clasificacion": clasificacion[:120],
                "categoria": _limpiar(fila.get("CATEGORIA"))[:10],
                "departamento": _limpiar(fila.get("DEPARTAMENTO"))[:60],
                "provincia": _limpiar(fila.get("PROVINCIA"))[:60],
                "distrito": _limpiar(fila.get("DISTRITO"))[:60],
                "ubigeo": _limpiar(fila.get("UBIGEO"))[:6],
                "direccion": _limpiar(fila.get("DIRECCION")),
                "telefono": telefono[:80],
                "horario": horario,
                "abierto_24h": horario_24h(horario),
                "latitud": lat,
                "longitud": lon,
                "osm_id": "",
                "fuente": "RENIPRESS",
                "confianza": 85,
                "verificacion": "OFICIAL",
                "activo": es_activo(_limpiar(fila.get("ESTADO"))),
            })
    return registros
