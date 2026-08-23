---
tags: [arquitectura]
estado: estable
actualizado: 2026-08-22
---

# Arquitectura Actual (base construida)

> Fuente canónica técnica: `docs/SISTEMA.md` · Evolución nueva: [[Evolucion-Tiempo-Real]]

```mermaid
flowchart LR
    subgraph F["FUENTES sintéticas (seed=42)"]
        R[renipress.csv 1.844] ; H[his_atenciones.csv 350k] ; U[ubigeo.csv 957]
    end
    subgraph P["PYSPARK Medallón"]
        B[Bronze Parquet crudo] --> S[Silver dedup+geocoding] --> G[Gold UPSERT Postgres]
    end
    DB[(PG16+PostGIS+pgvector<br/>ODS + estrella + vistas OLAP)]
    API[Spring Boot :8080<br/>7 endpoints REST]
    ML[ML: DBSCAN haversine<br/>forecast Prophet-style]
    DASH[Dashboard Leaflet+Chart.js]

    F --> B --> G --> DB
    DB --> API & DASH
    S -.-> ML
```

## Piezas clave que el producto REUTILIZA
| Pieza | Ubicación | Uso futuro |
|---|---|---|
| `recomendar_derivacion()` score 50/30/20 | `db/init/07_derivacion.sql` | núcleo del destino hospitalario v2 |
| Búsqueda geo `ST_DWithin` geography | `IpressService` backend | patrón para ambulancias cercanas |
| Embeddings pgvector HNSW deterministas | `data/embedding_encoder.py` + espejo Java | búsqueda semántica ciudadana |
| KPI saturación 0-100 | `fact_atenciones_medicas` | insumo del score anti-saturación |
| QA idempotente + CI e2e | `qa/`, `.github/workflows/ci.yml` | extender a tablas operativas |
