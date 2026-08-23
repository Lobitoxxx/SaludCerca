import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from matching import buscar_candidato, construir_indice, distancia_m, fusionar
from normalizacion import (clasificar_tipo, es_activo, horario_24h,
                           normalizar_nombre, parse_par_coords, sector_de)


# ---------------------------------------------------------------------------
# normalizacion
# ---------------------------------------------------------------------------

def test_normalizar_nombre():
    assert normalizar_nombre("  Clínica  San Pablo S.A.C. ") == "CLINICA SAN PABLO S A C"
    assert normalizar_nombre("HOSPITAL  Edmundo Escombe") == "HOSPITAL EDMUNDO ESCOMBE"
    assert normalizar_nombre("") == ""


def test_clasificar_tipo():
    assert clasificar_tipo("HOSPITALES O CLINICAS DE ATENCION GENERAL", "MINSA") == "HOSPITAL"
    assert clasificar_tipo("HOSPITALES O CLINICAS DE ATENCION ESPECIALIZADA", "PRIVADO") == "CLINICA"
    assert clasificar_tipo("PUESTOS DE SALUD O POSTAS DE SALUD") == "POSTA"
    assert clasificar_tipo("CENTROS DE SALUD O CENTROS MEDICOS") == "CENTRO_SALUD"
    assert clasificar_tipo("POLICLINICOS") == "POLICLINICO"
    assert clasificar_tipo("CONSULTORIOS MEDICOS Y DE OTROS PROFESIONALES") == "CONSULTORIO"
    assert clasificar_tipo("ALGO DESCONOCIDO") == "OTRO"


def test_sector_de():
    assert sector_de("PRIVADO") == "PRIVADO"
    assert sector_de("GOBIERNO REGIONAL") == "PUBLICO"
    assert sector_de("MINSA") == "PUBLICO"
    assert sector_de("ESSALUD") == "PUBLICO"
    assert sector_de("OTRO") == "OTRO"


def test_es_activo_y_horario():
    assert es_activo("ACTIVO")
    assert not es_activo("BAJA DEFINITIVA")
    assert horario_24h("24 HORAS DE LUNES A DOMINGO")
    assert not horario_24h("9:00 - 21:00")


def test_parse_par_coords_convencion_lat_lon():
    # Convención NORTE=latitud (archivo RENIPRESS 2026)
    lat, lon = parse_par_coords("-12.0675439", "-77.0368198")
    assert abs(lat - (-12.0675439)) < 1e-9
    assert abs(lon - (-77.0368198)) < 1e-9


def test_parse_par_coords_convencion_invertida():
    # Convención antigua: NORTE=longitud, ESTE=latitud
    lat, lon = parse_par_coords("-78.85838013", "-6.1335228")
    assert abs(lat - (-6.1335228)) < 1e-9
    assert abs(lon - (-78.85838013)) < 1e-9


def test_parse_par_coords_invalidos():
    assert parse_par_coords("", "") == (None, None)
    assert parse_par_coords("abc", "-77.0") == (None, None)
    assert parse_par_coords("999", "999") == (None, None)  # fuera de rango Perú


# ---------------------------------------------------------------------------
# matching
# ---------------------------------------------------------------------------

REG = {"nombre_norm": "CLINICA SAN PABLO", "latitud": -12.09, "longitud": -77.02,
       "telefono": "", "horario": "", "osm_id": "", "fuente": "RENIPRESS",
       "confianza": 85, "abierto_24h": False}


def _reg(**kw):
    base = {k: v for k, v in REG.items()}
    base.update(kw)
    return base


def test_distancia_m_corta():
    # ~111 m por grado de latitud
    d = distancia_m(-12.0, -77.0, -12.001, -77.0)
    assert 100 < d < 120


def test_buscar_candidato_match():
    indice = construir_indice([REG])
    poi = {"nombre_norm": "CLINICA SAN PABLO", "latitud": -12.0901,
           "longitud": -77.0201}
    assert buscar_candidato(indice, poi) is REG


def test_buscar_candidato_nombre_distinto_no_matchea():
    indice = construir_indice([REG])
    poi = {"nombre_norm": "LABORATORIO TORRES TOTALMENTE DISTINTO",
           "latitud": -12.0901, "longitud": -77.0201}
    assert buscar_candidato(indice, poi) is None


def test_fusionar_completa_datos_y_nuevos():
    reg = _reg()
    pois = [
        {"nombre": "Clínica San Pablo", "nombre_norm": "CLINICA SAN PABLO",
         "latitud": -12.0901, "longitud": -77.0201, "osm_id": "n/123",
         "telefono": "01-5555555", "horario": "24/7", "abierto_24h": True,
         "fuente": "OSM"},
        {"nombre": "Clinica Nueva Sin Registro",
         "nombre_norm": "CLINICA NUEVA SIN REGISTRO",
         "latitud": -12.05, "longitud": -77.10, "osm_id": "n/456",
         "telefono": "", "horario": "", "abierto_24h": False,
         "fuente": "OSM"},
    ]
    sin_match, stats = fusionar([reg], pois)
    assert stats["matches"] == 1 and stats["osm_nuevos"] == 1
    assert reg["telefono"] == "01-5555555" and reg["horario"] == "24/7"
    assert reg["fuente"] == "MIXTO" and reg["confianza"] == 92
    assert sin_match[0]["fuente"] == "OSM"


def test_fusionar_poi_sin_geo_va_a_nuevos():
    reg = _reg()
    poi = {"nombre": "X", "nombre_norm": "X", "latitud": None,
           "longitud": None, "osm_id": "n/1", "telefono": "", "horario": "",
           "abierto_24h": False, "fuente": "OSM"}
    sin_match, stats = fusionar([reg], [poi])
    assert len(sin_match) == 1 and stats["matches"] == 0
