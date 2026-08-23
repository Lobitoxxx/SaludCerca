---
tags: [adr, arquitectura, routing]
estado: aceptada
fecha: 2026-08-22
---

# ADR-005 — Routing: Valhalla self-hosted + tráfico propio

## Contexto
El portal necesita rutas al establecimiento más cercano con evaluación de tráfico. Ningún motor gratuito ofrece tráfico en vivo real (Google/Waze son propietarios y pagos). Investigación 2026-08-22 ([[Fuentes-Datos-Investigacion]]).

## Decisión
- **Valhalla self-hosted** (Docker) sobre extract OSM Perú de Geofabrik:
  - Único motor OSS con *time-dependent costing* (velocidades distintas por hora del día ≈ tráfico histórico sin pagar feeds).
  - Isócronas nativas → análisis de cobertura F-C5.
  - Tiles parciales → actualización sin rebuild total.
- **Tráfico propio a mediano plazo**: agregar `posiciones_ambulancia` (+ futuros reportes GPS de conductores/contribuidores) → velocidades observadas por segmento/hora en `trafico_segmentos` → inyectar como custom speeds. Es un moat de datos que nadie más tiene.
- Google Directions queda como opción premium B2B futura, nunca dependencia del MVP.

## Consecuencias
- ✅ Costo marginal cero por consulta; latencia ~200 ms suficiente para emergencias.
- ⚠️ Build inicial del grafo Perú: ~30–60 min y 4–8 GB RAM una sola vez.
- ⚠️ ETA inicial = histórico por hora, no tráfico en vivo → documentarlo en UI ("ETA estimada según hora").
