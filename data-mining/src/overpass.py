"""Descarga (con cache) y parseo de POIs de salud de OSM Perú vía Overpass."""
import json
import os
import urllib.parse
import urllib.request

# Instancias públicas de Overpass; se prueban en orden.
SERVIDORES = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

QUERY = """
[out:json][timeout:300];
area["ISO3166-1"="PE"][admin_level=2]->.peru;
(
  nwr["amenity"="hospital"](area.peru);
  nwr["amenity"="clinic"](area.peru);
  nwr["amenity"="doctors"](area.peru);
);
out center tags;
"""

AMENITY_TIPO = {
    "hospital": "HOSPITAL",
    "clinic": "CLINICA",
    "doctors": "CONSULTORIO",
}


def descargar_overpass(cache_path, timeout=600):
    """Descaja POIs salud OSM; usa cache local si existe."""
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    ultimo_error = None
    for servidor in SERVIDORES:
        try:
            req = urllib.request.Request(
                servidor, data=body,
                headers={"User-Agent": "SaludCerca/0.1 (datos abiertos)"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                datos = json.loads(resp.read().decode("utf-8"))
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(datos, f)
            return datos
        except Exception as exc:  # noqa: BLE001 - probamos el siguiente espejo
            ultimo_error = exc
    raise RuntimeError(f"Overpass no disponible: {ultimo_error}")


def _centro(elemento):
    if "lat" in elemento and "lon" in elemento:
        return float(elemento["lat"]), float(elemento["lon"])
    centro = elemento.get("center") or {}
    if "lat" in centro and "lon" in centro:
        return float(centro["lat"]), float(centro["lon"])
    return None, None


def extraer_pois(datos):
    """Convierte la respuesta Overpass en POIs normalizados."""
    pois = []
    for elemento in datos.get("elements", []):
        tags = elemento.get("tags") or {}
        nombre = (tags.get("name") or "").strip()
        if not nombre:
            continue
        lat, lon = _centro(elemento)
        amenity = tags.get("amenity", "")
        telefono = (tags.get("phone") or tags.get("contact:phone")
                    or tags.get("contact:mobile") or "")
        pois.append({
            "osm_id": f"{elemento['type']}/{elemento['id']}",
            "nombre": nombre,
            "nombre_norm": __import__("normalizacion").normalizar_nombre(nombre),
            "tipo": AMENITY_TIPO.get(amenity, "OTRO"),
            "sector": "PRIVADO" if tags.get("operator") else "OTRO",
            "direccion": tags.get("addr:street", "") + " "
                         + tags.get("addr:housenumber", ""),
            "telefono": telefono.strip()[:80],
            "horario": tags.get("opening_hours", ""),
            "abierto_24h": tags.get("opening_hours", "").startswith("24/7"),
            "latitud": lat,
            "longitud": lon,
            "departamento": "", "provincia": "", "distrito": "",
            "ubigeo": "", "codigo_renipress": "",
            "clasificacion": f"OSM amenity={amenity}",
            "categoria": "",
            "fuente": "OSM",
            "confianza": 45,
            "verificacion": "SIN_VERIFICAR",
            "activo": True,
        })
    return pois
