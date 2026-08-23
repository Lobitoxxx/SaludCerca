# 🚑 SALUD CERCA

> **Lakehouse geo-analítico sanitario del Perú evolucionando a plataforma SaaS de despacho de emergencias y ambulancias por suscripción.**

![CI](https://github.com/Lobitoxxx/SaludCerca/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Java](https://img.shields.io/badge/Java-17-orange)
![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.5-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20PostGIS%20%2B%20pgvector-336791)
![PySpark](https://img.shields.io/badge/PySpark-3.5-E25A1C)

---

## 🎯 El producto

**"Uber de ambulancias + cerebro anti-saturación"**: conectamos al ciudadano en emergencia
con la ambulancia disponible más cercana y el hospital óptimo (no saturado, nivel adecuado,
cercano), alimentado por tres canales de datos — oficiales, minado web/API y una red humana
pagada de verificadores.

```mermaid
flowchart LR
    C["📱 CIUDADANO<br/>SOS app/PWA/WhatsApp"] -->|"GPS + triaje"| D["🧠 CEREBRO DE DESPACHO<br/>score 0-100"]
    A["🚑 AMBULANCIA"] <-->|"posición + estados"| D
    D -->|"hospital óptimo"| H["🏥 HOSPITAL<br/>capacidad en vivo"]
    CO["👥 RED DE CONTRIBUIDORES<br/>pagada por verificación"] -.->|"datos frescos"| H
```

**Flujos de trabajo completos** (ciudadano, operador B2B, contribuidor, economía):
▶ **[docs/PRODUCTO.md](docs/PRODUCTO.md)**

## 🏗️ Arquitectura de un vistazo

```mermaid
flowchart TB
    subgraph FUENTES["FUENTES"]
        direction LR
        SIN["Dataset sintético seed=42<br/>RENIPRESS 1.844 · HIS 350k"]
        REAL["Fase F2: fuentes REALES<br/>RENIPRESS 35k · SUSALUD · INEI<br/>OSM Overpass · Google Places"]
    end
    subgraph MEDALLON["PIPELINE PYSPARK"]
        B[Bronze Parquet crudo] --> S[Silver dedup+geocoding] --> G[Gold UPSERT]
    end
    PG[("PostgreSQL 16 + PostGIS + pgvector<br/>ODS · Modelo estrella · Vistas OLAP<br/>+ tablas operativas RT (despacho)")]
    API["API Spring Boot :8080<br/>búsqueda geo · semántica · derivación · despacho"]
    ML["ML<br/>DBSCAN desiertos sanitarios · forecast Prophet-style"]
    DASH["Dashboard Leaflet + Chart.js"]
    PWA["PWA SOS · Panel operador · App ambulancia ⏳"]

    FUENTES --> MEDALLON --> PG
    S -.-> ML
    PG --> API --> PWA
    PG --> DASH
```

| Componente | Tecnología | Estado |
|---|---|---|
| Generador de datos | Python (seed=42) + embeddings 384d | ✅ |
| Pipeline Medallón | PySpark 3.5.5, idempotente + `MANIFEST.json` | ✅ |
| Base de datos | PostgreSQL 16 + PostGIS 3.4 + pgvector (Docker) | ✅ |
| Modelo estrella | Kimball: `fact_atenciones_medicas` + dims | ✅ |
| Motor de derivación | `recomendar_derivacion()` anti-saturación 50/30/20 | ✅ |
| Módulo ML | DBSCAN IPRESS + forecast mensual | ✅ |
| QA | 10 validaciones Gold + 7 derivación + idempotencia e2e | ✅ |
| Dashboard | HTML autónomo (Leaflet + Chart.js) | ✅ |
| API backend | Spring Boot 3.5 REST + pgvector + PostGIS | ✅ |
| **Capa operativa RT** | Tablas despacho + contribuidores (`08`/`09`) | 🔨 F0 |
| Frontend ciudadano | React Native + PWA + WhatsApp | ⏳ F5 |

## 🚀 Quick start

```bash
# 1. Dataset sintético
python data/generate_seed.py --rows 350000

# 2. PostgreSQL + PostGIS + pgvector (esquema + seed automático)
docker compose up -d --build db

# 3. Pipeline Medallón
python data-pipeline/main.py            # o --stage bronze|silver|gold

# 4. Control de calidad
python qa/run_qa.py && python qa/run_qa_derivaciones.py

# 5. Dashboard
python dashboard/generar_dashboard.py && start dashboard/index.html

# 6. ML
pip install -r ml/requirements-ml.txt && python ml/main.py

# 7. Backend API
cd backend && mvnw.cmd package && java -jar target/backend-1.0.0.jar
#   GET /api/ipress/cercanas?lat=-12.05&lon=-77.04&radioKm=50
#   GET /api/buscar/ipress?texto=cardiologia      (semántica pgvector)
#   GET /api/derivacion/recomendar?origen=...&especialidad=...
#   GET /api/despacho/ambulancias/cercanas?lat=..&lon=..   (nuevo F0)
```

> ⚠️ Los scripts de `db/init/NN_*.sql` corren solo en el **primer arranque** del volumen.
> En un volumen existente aplicar manualmente:
> `docker compose exec -T db psql -U saludcerca -d saludcerca < db/init/08_despacho.sql`

## 📊 Batch demo 2024

**1.844** IPRESS · **349.887** atenciones HIS · **957** distritos · **51** clusters DBSCAN
(**90** IPRESS aisladas = candidatas a desierto sanitario) · forecast 2025 ≈ 29.300–29.900 atenciones/mes.

## 📚 Documentación

| Documento | Contenido |
|---|---|
| [docs/PRODUCTO.md](docs/PRODUCTO.md) | Producto: módulos M1–M6, flujos de trabajo, suscripciones, roadmap F0→F5 |
| [docs/SISTEMA.md](docs/SISTEMA.md) | Técnica canónica: arquitectura Medallón, ER, índices, vistas, QA, backend |
| [docs/vault/_MOC.md](docs/vault/_MOC.md) | Vault Obsidian: conocimiento vivo del proyecto (abrir carpeta con Obsidian) |
| graphify-out/GRAPH_REPORT.md | Grafo de conocimiento del código (generado con Graphify) |

## 🗂️ Estructura

```text
SaludCerca/
├── .github/workflows/ci.yml # CI end-to-end (pipeline + QA + tests + backend)
├── backend/                 # API REST Spring Boot (Gold/PostGIS/pgvector)
├── data/                    # Generador dataset sintético + embeddings
├── data-pipeline/           # PySpark bronze/silver/gold + MANIFEST + tests
├── db/init/                 # SQL: extensiones → ODS → estrella → índices → vistas → seed → derivación → despacho(08) → enriquecimiento(09)
├── dashboard/               # Dashboard HTML generado
├── qa/                      # Validaciones + idempotencia
├── ml/                      # DBSCAN geoespacial + forecast + tests
├── docs/                    # SISTEMA.md (técnica) · PRODUCTO.md (negocio) · vault/ (Obsidian)
└── graphify-out/            # Grafo de conocimiento del código
```
