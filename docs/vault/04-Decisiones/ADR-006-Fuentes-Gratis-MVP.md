---
tags: [adr, producto, datos]
estado: aceptada
fecha: 2026-08-22
---

# ADR-006 — MVP con fuentes de datos 100% gratuitas

## Contexto
F-C1 requiere enriquecer el catálogo nacional. Google Places API eliminó su crédito mensual de $200 (mar-2025): hoy free tier por SKU (Essentials 10k/mes, Pro 5k/mes, Enterprise 1k/mes) y exige cuenta GCP con tarjeta.

## Decisión
El MVP mina **solo fuentes gratuitas y abiertas**:
1. **RENIPRESS (SUSALUD)** — catálogo oficial ~35k IPRESS nacionales (incluye clínicas privadas), actualización mensual.
2. **OSM Overpass / Geofabrik Perú** — POIs salud con horarios/teléfono; captura privados no registrados.
3. **Datos abiertos MINSA/SUSALUD/INEI** — recursos, camas, población.

Google Places se difiere a fase premium (enriquecer top-N con popularidad/horarios ocupados), nunca será dependencia del core.

## Consecuencias
- ✅ Cero costo de datos + licencias limpias (datos abiertos reuso permitido; OSM ODbL con atribución).
- ⚠️ Menos metadata "rica" que Google → lo compensa la red de contribuidores ([[Modulos-M1-M6]] M6) pagada por dato validado.
