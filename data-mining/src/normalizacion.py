"""Normalización y clasificación de establecimientos de salud (solo stdlib)."""
import re
import unicodedata

# Rangos geográficos aproximados del Perú continental
LAT_MIN, LAT_MAX = -19.0, 0.5
LON_MIN, LON_MAX = -82.0, -68.0

_RE_NO_ALNUM = re.compile(r"[^A-Z0-9 ]+")
_RE_ESPACIOS = re.compile(r"\s+")

# Clasificación RENIPRESS -> tipo canónico
_MAPA_CLASIFICACION = [
    ("HOSPITALES O CLINICAS DE ATENCION ESPECIALIZADA", "HOSPITAL_CLINICA"),
    ("HOSPITALES O CLINICAS DE ATENCION GENERAL", "HOSPITAL_CLINICA"),
    ("CENTROS DE SALUD CON CAMAS", "CENTRO_SALUD"),
    ("CENTROS DE SALUD O CENTROS MEDICOS", "CENTRO_SALUD"),
    ("PUESTOS DE SALUD O POSTAS", "POSTA"),
    ("POLICLINICOS", "POLICLINICO"),
    ("CONSULTORIOS MEDICOS", "CONSULTORIO"),
    ("CENTRO ODONTOLOGICO", "ODONTOLOGICO"),
    ("PATOLOGIA CLINICA", "LABORATORIO"),
    ("LABORATORIO", "LABORATORIO"),
    ("DIAGNOSTICO POR IMAGENES", "IMAGENES"),
    ("HEMODIALISIS", "HEMODIALISIS"),
    ("REHABILITACION", "REHABILITACION"),
    ("CENTROS MEDICOS ESPECIALIZADOS", "CENTRO_ESPECIALIZADO"),
    ("CENTROS OPTICOS", "OPTICA"),
    ("SERVICIO DE TRASLADO", "TRASLADO"),
]

_SECTOR_PUBLICO = (
    "MINSA", "GOBIERNO REGIONAL", "MUNICIPALIDAD", "ESSALUD",
    "SANIDAD", "INPE", "FFAA", "Fuerzas Armadas".upper(),
)


def normalizar_nombre(texto):
    """Mayúsculas, sin acentos ni signos, espacios colapsados."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c)).upper()
    t = _RE_NO_ALNUM.sub(" ", t)
    return _RE_ESPACIOS.sub(" ", t).strip()


def clasificar_tipo(clasificacion, institucion=""):
    """Tipo canónico a partir de la clasificación RENIPRESS."""
    c = normalizar_nombre(clasificacion)
    for clave, tipo in _MAPA_CLASIFICACION:
        if normalizar_nombre(clave) in c:
            if tipo == "HOSPITAL_CLINICA" and normalizar_nombre(institucion).startswith("PRIVADO"):
                return "CLINICA"
            if tipo == "HOSPITAL_CLINICA":
                return "HOSPITAL"
            return tipo
    return "OTRO"


def sector_de(institucion):
    """PUBLICO / PRIVADO / OTRO a partir de la columna INSTITUCION."""
    i = normalizar_nombre(institucion)
    if i.startswith("PRIVADO"):
        return "PRIVADO"
    if any(i.startswith(p) or p in i for p in _SECTOR_PUBLICO):
        return "PUBLICO"
    return "OTRO"


def es_activo(estado):
    return normalizar_nombre(estado) == "ACTIVO"


def horario_24h(horario):
    h = normalizar_nombre(horario)
    return "24 H" in h or "24H" in h


def parse_par_coords(norte, este):
    """Convierte NORTE/ESTE a (lat, lon) validando rangos.

    Los archivos oficiales alternan la convención (a veces NORTE=lat,
    a veces NORTE=lon), así que se decide por rango geográfico.
    Devuelve (lat, lon) o (None, None) si no se puede validar.
    """
    try:
        a = float(str(norte).strip())
        b = float(str(este).strip())
    except (TypeError, ValueError):
        return None, None

    def es_lat(v):
        return LAT_MIN <= v <= LAT_MAX

    def es_lon(v):
        return LON_MIN <= v <= LON_MAX

    if es_lat(a) and es_lon(b):
        return a, b
    if es_lat(b) and es_lon(a):
        return b, a
    return None, None
