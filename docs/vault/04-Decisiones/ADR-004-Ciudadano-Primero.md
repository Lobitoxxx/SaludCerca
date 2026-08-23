---
tags: [adr, producto, estrategia]
estado: aceptada
fecha: 2026-08-22
supera: ADR-001
---

# ADR-004 — Cara ciudadana primero (supera ADR-001)

## Contexto
ADR-001 priorizaba B2B (operadores de ambulancias). El 2026-08-22 el owner re-priorizó: el valor inmediato y la captura de usuarios están en el **buscador ciudadano nacional** de hospitales/clínicas con rutas rápidas en emergencia.

## Decisión
- **Portal ciudadano primero** (F-C1..C5): catálogo nacional real (~35k IPRESS incl. clínicas privadas), búsqueda detallada, mapa, ruta con ETA por hora (Valhalla).
- El panel operador B2B se construye **después reutilizando** esta misma capa (catálogo + routing + capacidad RT), no se abandona.
- La red de informantes (M6) se activa desde el inicio porque alimenta el catálogo ciudadano.

## Consecuencias
- ✅ Producto público demostrable antes; SEO/crecimiento orgánico desde día 1.
- ✅ Cada búsqueda/ruta ciudadana valida datos que luego usa el despacho B2B.
- ⚠️ Monetización directa se posterga: primero tráfico/usuarios, después planes premium ([[Suscripciones-Economia]]).
