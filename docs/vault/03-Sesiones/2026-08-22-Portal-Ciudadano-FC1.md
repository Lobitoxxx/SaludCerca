---
tags: [sesion, bitacora, fc1]
fecha: 2026-08-22
---

# 2026-08-22 — Pivot ciudadano + F-C1 datos nacionales

## Contexto
El owner re-priorizó el producto: **cara ciudadana primero** (buscador nacional de hospitales/clínicas con rutas) y red de informantes activa desde el inicio. Decisiones: [[ADR-004-Ciudadano-Primero]], [[ADR-005-Routing-Valhalla-Trafico-Propio]], [[ADR-006-Fuentes-Gratis-MVP]].

## Investigación web
- **RENIPRESS oficial mensual** (dataset SUSALUD, ODC-BY): descargado `RENIPRESS_31-07-2026.csv` → 35.833 registros. ⚠️ El dataset viejo "minsa-ipress" (20.8k) quedó obsoleto.
- Coordenadas vienen en columnas `NORTE/ESTE` con convención inconsistente entre archivos → se valida por rango geográfico (`normalizacion.parse_par_coords`).
- Google Places: crédito $200 eliminado mar-2025, free tier por SKU → diferido ([[ADR-006-Fuentes-Gratis-MVP]]).
- Routing: Valhalla elegido por time-dependent costing + isócronas ([[ADR-005-Routing-Valhalla-Trafico-Propio]]).

## Construido (F-C1)
1. Módulo **`data-mining/`** (solo stdlib): normalización, lectura RENIPRESS, Overpass OSM Perú con cache+espejos, matching rejilla 200 m + difflib ≥0.72 ≤250 m, builder CLI y cargador COPY al Docker.
2. Tests: 12/12 pytest.
3. `db/init/10_ipress_master.sql`: tabla con geom generada, índices GIST geometry+geography, pg_trgm fuzzy, vista búsqueda.
4. Resultados en BD: **38.786 establecimientos** (29.762 activos · 25.626 con geo · 1.800 clínicas · 618 hospitales · 7.111 postas). 6.029 fusionados RENIPRESS+OSM (confianza 92), 2.973 nuevos de OSM.

## Hallazgos / lecciones
- Índice GIST sobre `geometry` NO sirve para `ST_DWithin(geography)` → índice funcional `(geom::geography)` bajó la consulta de 739 ms a **10,5 ms**.
- ~13k establecimientos sin coordenada = cola natural para contribuidores (sinergia M6).
- `CREATE OR REPLACE VIEW` no permite añadir columnas → usar `DROP VIEW IF EXISTS` previo en scripts idempotentes.

## Demo end-to-end (mismo día)
- Backend: `CatalogoService` + `CatalogoController` con 3 endpoints sobre `ipress_master`: `/cercanos` (KNN geography), `/buscar` (trgm fuzzy), `/{id}` — verificados en Lima **y** Arequipa.
- `portal/index.html` (semilla F-C3): buscador fuzzy + "cerca de mí" + filtros por tipo/radio + mapa Leaflet.
- Servicios vivos: API :8080 · portal demo :8011 · dashboard viejo :8010.

### Lecciones de depuración (para futuras sesiones)
- `mvnw.cmd` SOLO existe en `backend/`; correrlo desde raíz falla silencioso y deja jar viejo desplegado → siempre verificar línea BUILD SUCCESS + timestamp del jar.
- El `write` tool puede dejar BOM UTF-8 que javac rechaza (`illegal character: '\ufeff'`) → limpiar con `WriteAllText(UTF8Encoding($false))`.
- Editar archivos Java vía regex PowerShell corrompe acentos (cp1252) → reescribir completo con write tool.
- En text blocks Java, `%` trigram va simple; `%%` rompe el PreparedStatement.
- Al añadir columnas a un SELECT base compartido, no concatenar después del FROM.

## Siguiente sesión
F-C2: servicio Valhalla en docker-compose (PBF Perú Geofabrik) + endpoints `/api/ruta` y `/api/isocrona`; luego F-C3 portal PWA.
