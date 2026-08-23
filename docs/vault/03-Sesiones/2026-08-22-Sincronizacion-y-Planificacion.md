---
tags: [sesion, bitacora]
estado: cerrada
fecha: 2026-08-22
---

# Sesión 2026-08-22 — Sincronización, investigación y plan integral

## Objetivo
Convertir la carpeta vacía en repo activo y definir el plan de producto hacia emergencias/ambulancias por suscripción.

## Hecho
1. ✅ Repo conectado a `origin` (master, 3 commits descargados, tree limpio).
2. ✅ Exploración completa: lakehouse medallón + PostGIS/pgvector + motor derivación + ML + Spring Boot + dashboard ([[Arquitectura-Actual]]).
3. ✅ Investigación web de fuentes reales: RENIPRESS ~35k, SUSALUD recursos (**ambulancias por IPRESS**), INEI 1874 distritos, OSM Overpass, Google Places → [[Fuentes-Datos-Investigacion]].
4. ✅ Decisiones tomadas con el usuario:
   - Cliente inicial: B2B primero, ciudadano después → [[ADR-001-Estrategia-B2B-Primero]]
   - Móvil: React Native + PWA → [[ADR-002-Stack-Movil-ReactNative-PWA]]
   - Conocimiento: Obsidian vault versionado + Graphify → [[ADR-003-Conocimiento-Obsidian-Graphify]]
5. ✅ Infraestructura de conocimiento creada (`docs/vault/`, AGENTS.md).
6. ✅ F0 ejecutado:
   - `db/init/08_despacho.sql` + `09_enriquecimiento.sql` **verificados en Docker real**: volumen recreado limpio, init corrió los 9 scripts sin errores, `ambulancia_disponible_cercana()` probada (5 unidades KNN desde Lima centro OK), seed demo cargado.
   - Backend: DTOs records + `DespachoService`/`DespachoController` + `ContribucionService`/`ContribucionController` escritos siguiendo estilo JdbcTemplate del repo. **Pendiente: compilar** (no hay JDK en la máquina).
7. ✅ README renovado con badges y 4 diagramas Mermaid; `docs/PRODUCTO.md` completo con flujos de trabajo (ciudadano, operador B2B, contribuidor, economía).
8. ✅ Graphify integrado (`pip install graphifyy`; grafo 360 nodos/677 aristas; plugin opencode instalado en `.opencode/`).

## Hallazgos / bloqueos
- ~~JDK ausente~~ → **resuelto**: Temurin 17.0.20 instalado vía winget; `mvnw package` BUILD SUCCESS (4 tests OK).
- Bug corregido durante verificación: CHECK de `fuentes_datos.frecuencia` no incluía 'ANUAL' (INEI) → init fallaba → corregido y volumen recreado.
- Bug JDBC corregido en `DespachoService`: `EXTRACT(EPOCH ...)` devuelve `numeric` (BigDecimal), no timestamp → mappers ahora leen epoch-ms con `getBigDecimal` + helper `epochMs()`.
- Endurecido `ContribucionService`: rechaza reportes sin contribuidor/campos obligatorios (400 con handler local, antes 500); geocerca inválida también responde 400.
- Los scripts init solo corren en primer arranque; para aplicarlos sobre volumen existente: `docker compose down -v && up -d db` (re-seed completo) o psql manual.

## Smoke test end-to-end (aprobado)
| Endpoint | Resultado |
|---|---|
| `GET /api/despacho/ambulancias/cercanas?lat&lon` | 5 unidades ordenadas por km reales ✓ |
| `POST /api/despacho/emergencias` | EMG-20260822-62497, C2, RECIBIDA ✓ |
| `POST /emergencias/{id}/asignar/2` | ACEPTADA, 2.38 km, SLA marcado ✓ |
| `POST /ambulancias/{id}/posicion` | 204 + fila GPS insertada ✓ |
| `GET /api/contribucion/tareas?lat&lon` | 3 tareas por prioridad/distancia ✓ |
| `POST /api/contribucion/reportes` válido | 201, fila PENDIENTE en BD ✓ |
| Reporte sin contribuidor | 400 ✓ |
| Reporte fuera de geocerca | 400 ✓ |

## Siguiente sesión
Tests del módulo despacho en CI → auth mínima de contribuidores → arrancar F1 (OSRM vs Valhalla para ETA real).
