---
tags: [minado, datos, fc1]
estado: vivo
actualizado: 2026-08-22
---

# Módulo data-mining (F-C1)

> Construye `ipress_master`: catálogo nacional real de establecimientos de salud (hospitales + clínicas + centros + postas) fusionando RENIPRESS oficial con OSM.

## Fuentes
| Fuente | Archivo | Aporta |
|---|---|---|
| RENIPRESS SUSALUD (mensual) | `data/renipress_YYYY-MM.csv` | ~35.8k IPRESS, código único, ubigeo, teléfono, horario, coordenadas |
| OSM Overpass Perú | `data/osm_peru_health.json` (cache) | clínicas privadas no registradas, horarios, teléfono |

## Uso
```powershell
cd data-mining
python -m pytest tests -q          # tests unitarios
python src\build_master.py         # genera data/ipress_master.csv
python src\cargar_db.py            # COPY al Docker (requiere db arriba)
```

## Decisiones técnicas
- **Solo stdlib** (csv/math/difflib/urllib) — sin dependencias pesadas.
- Coordenadas RENIPRESS vienen en columnas `NORTE`/`ESTE` con convención inconsistente entre archivos → se valida por rango geográfico del Perú (lat [-19,-0], lon [-82,-68]) y se corrige automáticamente.
- Matching OSM↔RENIPRESS: rejilla espacial ~200 m + similitud de nombre normalizado ≥ 0.72 y distancia ≤ 250 m.
- Registros sin coordenada (≈13k) quedan `geom IS NULL` → futuras tareas para contribuidores ([[Modulos-M1-M6]] M6).
