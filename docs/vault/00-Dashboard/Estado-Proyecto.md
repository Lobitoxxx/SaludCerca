---
tags: [dashboard, estado]
estado: vivo
actualizado: 2026-08-22
---

# Estado del Proyecto

> Última revisión: **2026-08-22** · Fase actual: **F-C2 ✅ → F-C3 (portal React/PWA)**

## ⚠️ Cambio de estrategia 2026-08-22
[[ADR-004-Ciudadano-Primero]] supera al ADR-001: el buscador ciudadano nacional va primero; el panel B2B se reutiliza después sobre la misma capa.

## Roadmap maestro

### ✅ Completado — F-C1: Datos nacionales reales
- [x] RENIPRESS oficial jul-2026 descargado y normalizado (35.813 registros)
- [x] Módulo `data-mining/` (stdlib): Overpass OSM + matching espacial/nombre · **12 tests OK**
- [x] `db/init/10_ipress_master.sql` — catálogo con geom, índices geography+trgm, vista búsqueda
- [x] Cargados **38.786 establecimientos** (29.762 activos, 25.626 con geo, 6.029 enriquecidos MIXTO)
- [x] KNN por radio: 10,5 ms · búsqueda fuzzy trgm verificada

### ✅ Completado (base analítica)
- [x] Pipeline Medallón PySpark (Bronze/Silver/Gold) idempotente + MANIFEST
- [x] PostgreSQL 16 + PostGIS 3.4 + pgvector en Docker (esquema ODS + estrella)
- [x] Motor de derivación anti-saturación `recomendar_derivacion()`
- [x] Módulo ML: DBSCAN haversine (desiertos sanitarios) + forecast estilo Prophet
- [x] QA: 10 validaciones Gold + 7 derivación + idempotencia e2e
- [x] Dashboard Leaflet+Chart.js autónomo
- [x] CI end-to-end GitHub Actions (pipeline + QA + tests + backend)
- [x] Backend Spring Boot REST sobre capa Gold (7 endpoints)
- [x] F0 despacho+contribución: SQL 08/09 verificados, backend smoke test end-to-end OK, JDK instalado

### 🚧 En curso — F-C2: Routing Valhalla
- [x] PBF Perú (Geofabrik, 244 MB) en `data/osm/` · imagen `ghcr.io/valhalla/valhalla`
- [x] Servicio `valhalla` + `api` contenedorizada en docker-compose (`backend/Dockerfile`, jar Maven local)
- [x] Endpoint `/api/ruta` (proxy Valhalla, costing auto/bici/pie/moto) + decodificador polyline6 con tests
- [x] `db/init/11_trafico_segmentos.sql` aplicado (velocidades OSM×hora×tipo-día)
- [x] Portal demo: botón "Cómo llegar" dibuja ruta + ETA
- [x] Build de tiles Perú terminado (0,8 GB, Valhalla 3.8.3) + servicio :8002 arriba
- [x] **Prueba e2e OK**: Lima centro→San Isidro 9,16 km / 10,9 min · clínica más cercana 0,58 km / 1,5 min vía `/api/ruta`

### ✅ Completado — F-C1: Datos nacionales reales
- [x] RENIPRESS oficial jul-2026 descargado y normalizado (35.813 registros)
- [x] Módulo `data-mining/` (stdlib): Overpass OSM + matching espacial/nombre · **12 tests OK**
- [x] `db/init/10_ipress_master.sql` — catálogo con geom, índices geography+trgm, vista búsqueda
- [x] Cargados **38.786 establecimientos** (29.762 activos, 25.626 con geo, 6.029 enriquecidos MIXTO)
- [x] KNN por radio: 10,5 ms · búsqueda fuzzy trgm verificada
- [x] Demo API `/api/establecimientos/*` + portal mapa :8011

### ⏳ Pendiente
| Fase | Alcance | Ver |
|---|---|---|
| **F-C3 Portal ciudadano** | PWA React `portal/`: buscador detallado + mapa + ficha + ruta | [[Vision-Producto]] |
| **F-C4 Informantes** | Auth mínima + UI tareas/reportes + tarifario validación/pago | [[Modulos-M1-M6]] |
| **F-C5 Cobertura** | Isócronas × población INEI → índice necesidad-cubierta | [[Evolucion-Tiempo-Real]] |
| F3 Monetización | Suscripciones Culqi/Izipay + facturación | [[Suscripciones-Economia]] |
| F4/F5 B2B+App | Panel operador reutilizando capa ciudadana · React Native | [[ADR-001-Estrategia-B2B-Primero]] |

## Métricas clave del negocio (a instrumentar desde F1)
- Tiempo medio de respuesta (desde SOS hasta llegada a escena) — métrica reina
- % emergencias asignadas < 60 s · ocupación de flota · NPS operadores
