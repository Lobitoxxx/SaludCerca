---
tags: [sesion, routing, valhalla, infraestructura]
fecha: 2026-08-22
fase: F-C2
---

# 2026-08-22 — F-C2: Routing Valhalla + backend contenedorizado

## Objetivo
Motor de rutas self-hosted sobre OSM Perú ([[ADR-005-Routing-Valhalla-Trafico-Propio]]): ETA real por red vial para el buscador ciudadano.

## Hecho
- **PBF Perú** descargado de Geofabrik (`data/osm/peru-latest.osm.pbf`, 244 MB, licencia ODbL).
- **docker-compose**: servicio `valhalla` (imagen oficial `ghcr.io/valhalla/valhalla`, puerto 8002) + `api` contenedorizada (`backend/Dockerfile` sobre `eclipse-temurin:17-jre`; jar compilado con Maven local).
- **Backend**: `RutaService` (proxy HTTP a Valhalla `/route`, costing auto/bicycle/pedestrian/motorcycle), decodificador polyline6 propio → geometría `[lat,lon]` lista para Leaflet. DTO `RutaDto(distanciaKm, minutosEta, costing, geometria)` + `GET /api/ruta`. **2 tests unitarios** del decoder (referencia generada en Python) — suite completa 6/6.
- **BD**: `db/init/11_trafico_segmentos.sql` aplicado manualmente al volumen existente (velocidad media por way OSM × hora × tipo-día; confianza por muestras).
- **Portal demo**: botón "🧭 Cómo llegar" en cada resultado → dibuja ruta + banner ETA.
- **scripts/valhalla-build.ps1**: build idempotente config → tiles → traffic extract, concurrencia limitada a 4 hilos / 4 GB.

## Problemas encontrados y lecciones
| Problema | Causa raíz | Solución |
|---|---|---|
| Build fallaba al instante | PowerShell 5.1 `>` escribe **UTF-16**: Valhalla no lee el config.json | Capturar salida y escribir con `WriteAllLines` ASCII |
| API moría entre comandos | Sandbox mata procesos desatachados (javaw) de forma intermitente | **Contenedorizar la API** en compose — solución permanente |
| `mvnw.cmd` desde raíz = jar viejo | El wrapper vive solo en `backend/` | Verificar línea BUILD SUCCESS + timestamp del jar |
| `< archivo.sql` no funciona | PS5.1 no soporta redirección de entrada | `Get-Content x.sql -Raw | docker compose exec -T db psql ...` |

## Estado al cierre
- Tiles Perú: build corriendo (~20 min, shortcuts nivel 1). Pendiente: `docker compose up -d valhalla` + prueba e2e Lima→San Isidro vía `/api/ruta`.
- Servicios vivos: db ✓ · api (contenedor) ✓ :8080 · portal :8011.

## Siguiente sesión
1. Verificar tiles + levantar `valhalla` + smoke test ruta real.
2. Isócronas `/api/isocrona` (Valhalla `/isochrone`) para F-C5.
3. Poblar `trafico_segmentos` sintético y ajustar ETA por hora (estrategia ADR-005 §ajuste).
