"""Matching espacial+nombre entre POIs OSM y registros RENIPRESS."""
import math
from difflib import SequenceMatcher

# Rejilla de ~200 m en grados cerca del ecuador
PASO = 0.002
RADIO_MAX_M = 250.0
UMBRAL_NOMBRE = 0.72


def _celda(lat, lon):
    return (int(lat // PASO), int(lon // PASO))


def distancia_m(lat1, lon1, lat2, lon2):
    """Distancia haversine aproximada en metros."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _similitud(a, b):
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def construir_indice(registros_con_geo):
    """Indexa registros con coordenadas por celdas de rejilla."""
    indice = {}
    for reg in registros_con_geo:
        if reg.get("latitud") is None or reg.get("longitud") is None:
            continue
        cx, cy = _celda(reg["latitud"], reg["longitud"])
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                indice.setdefault((cx + dx, cy + dy), []).append(reg)
    return indice


def buscar_candidato(indice, poi):
    """Mejor candidato RENIPRESS para un POI OSM, o None."""
    if poi.get("latitud") is None:
        return None
    mejor = None
    mejor_score = 0.0
    for reg in indice.get(_celda(poi["latitud"], poi["longitud"]), []):
        dist = distancia_m(poi["latitud"], poi["longitud"],
                           reg["latitud"], reg["longitud"])
        if dist > RADIO_MAX_M:
            continue
        sim = _similitud(poi["nombre_norm"], reg["nombre_norm"])
        score = sim * (1.0 - min(dist / RADIO_MAX_M, 1.0) * 0.3)
        if sim >= UMBRAL_NOMBRE and score > mejor_score:
            mejor, mejor_score = reg, score
    return mejor


def fusionar(renipress, pois_osm):
    """Fusiona POIs OSM sobre RENIPRESS.

    Devuelve (osm_sin_match, estadisticas).
    Los POI con match completan teléfono/horario/geo faltantes del registro
    oficial y suben su confianza.
    """
    indice = construir_indice(renipress)
    sin_match = []
    matches = 0
    for poi in pois_osm:
        reg = buscar_candidato(indice, poi)
        if reg is None:
            sin_match.append(poi)
            continue
        matches += 1
        reg["osm_id"] = poi["osm_id"]
        reg["fuente"] = "MIXTO"
        reg["confianza"] = 92
        if not reg["telefono"]:
            reg["telefono"] = poi["telefono"]
        if not reg["horario"]:
            reg["horario"] = poi["horario"]
            reg["abierto_24h"] = reg["abierto_24h"] or poi["abierto_24h"]
        if reg["latitud"] is None and poi["latitud"] is not None:
            reg["latitud"], reg["longitud"] = poi["latitud"], poi["longitud"]
    stats = {"osm_total": len(pois_osm), "matches": matches,
             "osm_nuevos": len(sin_match)}
    return sin_match, stats
