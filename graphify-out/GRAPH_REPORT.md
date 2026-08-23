# Graph Report - SaludCerca  (2026-08-22)

## Corpus Check
- 100 files · ~44,199 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 690 nodes · 1222 edges · 55 communities (49 shown, 6 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 73 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9d5eebd0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_ml.py
- IpressService
- PipelineConfig
- GeneradorSaludCerca
- DataCleaner
- run_bronze
- ipress
- SemanticEncoder
- SALUD CERCA — Documentación del Sistema
- mvnw
- test_derivacion.py
- CorsConfig.java
- generar_dashboard.py
- test_idempotencia.py
- SaludCercaBackendApplication
- pe.saludcerca:backend
- DespachoService
- SALUD CERCA — Plan de Producto
- _MOC.md
- AGENTS.md — Reglas permanentes para sesiones de IA (opencode)
- 🗺️ SALUD CERCA — Mapa de Contenido
- Estado del Proyecto
- Fuentes de Datos Investigadas (reales)
- Suscripciones y Economía
- Visión de Producto
- Sesión 2026-08-22 — Sincronización, investigación y plan integral
- ADR-003 — Conocimiento: Obsidian vault versionado + Graphify
- Backlog priorizado
- Evolución Tiempo Real (F0)
- test_minado.py
- graphify.js
- ADR-001 — Estrategia B2B primero (operadores de ambulancias)
- ContribucionController.java
- org.springframework.web.bind.annotation.GetMapping
- BusquedaService
- 2026-08-22 — Pivot ciudadano + F-C1 datos nacionales
- Módulo data-mining (F-C1)
- cargar_db.py
- ADR-004 — Cara ciudadana primero (supera ADR-001)
- ADR-005 — Routing: Valhalla self-hosted + tráfico propio
- ADR-006 — MVP con fuentes de datos 100% gratuitas
- 10_ipress_master.sql
- Arquitectura Actual (base construida)
- CatalogoService
- org.springframework.jdbc.core.JdbcTemplate
- java.sql.ResultSet

## God Nodes (most connected - your core abstractions)
1. `SALUD CERCA — Documentación del Sistema` - 20 edges
2. `DataCleaner` - 19 edges
3. `PipelineConfig` - 17 edges
4. `DespachoService` - 16 edges
5. `GeneradorSaludCerca` - 16 edges
6. `ipress` - 15 edges
7. `CatalogoService` - 14 edges
8. `PostgisGoldWriter` - 14 edges
9. `IpressService` - 12 edges
10. `run_bronze()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `test_normalizar_nombre()` --calls--> `normalizar_nombre()`  [INFERRED]
  data-mining/tests/test_minado.py → data-mining/src/normalizacion.py
- `test_clasificar_tipo()` --calls--> `clasificar_tipo()`  [INFERRED]
  data-mining/tests/test_minado.py → data-mining/src/normalizacion.py
- `test_sector_de()` --calls--> `sector_de()`  [INFERRED]
  data-mining/tests/test_minado.py → data-mining/src/normalizacion.py
- `test_parse_par_coords_convencion_invertida()` --calls--> `parse_par_coords()`  [INFERRED]
  data-mining/tests/test_minado.py → data-mining/src/normalizacion.py
- `test_parse_par_coords_convencion_lat_lon()` --calls--> `parse_par_coords()`  [INFERRED]
  data-mining/tests/test_minado.py → data-mining/src/normalizacion.py

## Import Cycles
- None detected.

## Communities (55 total, 6 thin omitted)

### Community 0 - "test_ml.py"
Cohesion: 0.06
Nodes (46): GeoClusterer, DataFrame, DBSCAN sobre (lat, lon) con distancia haversine en kilómetros. Args: eps_km:…, Ajusta DBSCAN sobre las columnas `latitud`/`longitud`. Agrega la columna…, Resumen de clusters y listado de IPRESS aisladas (ruido). Returns: (agg,…, cargar_atenciones(), cargar_ipress(), DataFrame (+38 more)

### Community 1 - "IpressService"
Cohesion: 0.17
Nodes (8): CercanaRowMapper, IpressRowMapper, IpressService, Override, EspecialidadDto, IpressCercanaDto, IpressDto, IpressController

### Community 2 - "PipelineConfig"
Cohesion: 0.06
Nodes (35): Any, main(), PipelineConfig, SparkSession, Configuración del pipeline Medallón. Atributos: raw_dir: Fuentes originales…, Construye una SparkSession sintonizada para el pipeline. Buenas prácticas de…, PostgisGoldWriter, DataFrame (+27 more)

### Community 3 - "GeneradorSaludCerca"
Cohesion: 0.11
Nodes (15): embed(), embed_postgres(), _ngramas(), _normalizar(), Normaliza el texto: minúsculas, sin acentos y sin puntuación., Genera los n-gramas de caracteres (n=1..4) del token con delimitadores., Convierte texto en un vector L2-normalizado de `DIMENSION` dimensiones.…, Devuelve el embedding en formato literal de pgvector ('[0.1,0.2,...]'). (+7 more)

### Community 4 - "DataCleaner"
Cohesion: 0.17
Nodes (19): DataCleaner, DataFrame, Casting estricto y normalización de los establecimientos., Casting estricto y validación de dominios de las atenciones., Pipeline de limpieza para las capas Silver., Elimina duplicados exactos por `subset`, conservando la fila más reciente. La…, Deduplicación de establecimientos por su clave natural RENIPRESS., Deduplicación de atenciones por clave compuesta del evento. En HIS real no… (+11 more)

### Community 5 - "run_bronze"
Cohesion: 0.13
Nodes (21): BronzeWriter, DataFrame, SparkSession, Persiste las fuentes crudas en el Data Lake (Parquet)., Orquesta la carga de fuentes crudas hacia la capa Bronze., run_bronze(), HisReader, DataFrame (+13 more)

### Community 6 - "ipress"
Cohesion: 0.12
Nodes (31): atenciones_his, categorizaciones, especialidades, ipress, ubigeo, dim_ipress, dim_tiempo, dim_ubigeo (+23 more)

### Community 7 - "SemanticEncoder"
Cohesion: 0.21
Nodes (4): SemanticEncoder, SemanticEncoderTest, java.util.regex.Pattern, org.junit.jupiter.api.Test

### Community 8 - "SALUD CERCA — Documentación del Sistema"
Cohesion: 0.04
Nodes (47): 10. Control de calidad y pruebas, 11. Dashboard geo-analítico, 12. Guía de uso, 13. Roadmap y pendientes, 14. Motor de derivación inteligente, 15.1 Clustering DBSCAN de IPRESS activas (`ml/clustering_dbscan.py`), 15.2 Forecast mensual estilo Prophet (`ml/forecast.py`), 15. Módulo ML (+39 more)

### Community 9 - "mvnw"
Cohesion: 0.33
Nodes (6): mvnw script, clean(), die(), exec_maven(), set_java_home(), verbose()

### Community 10 - "test_derivacion.py"
Cohesion: 0.39
Nodes (7): _psql(), _read_csv(), test_generador_derivaciones_validas(), test_recomendar_no_incluye_origen(), test_recomendar_respeta_nivel_de_especialidad(), test_recomendar_retorna_candidatos_activos_ordenados(), skipif

### Community 11 - "CorsConfig.java"
Cohesion: 0.43
Nodes (5): CorsConfig, org.springframework.context.annotation.Bean, org.springframework.context.annotation.Configuration, org.springframework.web.servlet.config.annotation.WebMvcConfigurer, WebMvcConfigurer

### Community 12 - "generar_dashboard.py"
Cohesion: 0.48
Nodes (6): cargar_datos(), main(), num(), psql(), Ejecuta un SELECT y devuelve filas como listas de strings., render_html()

### Community 13 - "test_idempotencia.py"
Cohesion: 0.47
Nodes (5): main(), Lee los conteos de la BD (devuelve tupla ordenada)., Ejecuta una etapa del pipeline con el entorno Java/Hadoop., run_pipeline(), snapshot_db()

### Community 25 - "DespachoService"
Cohesion: 0.19
Nodes (7): DespachoService, EmergenciaMapper, DespachoController, AsignacionDto, EmergenciaDto, EmergenciaNuevaDto, org.springframework.web.bind.annotation.PostMapping

### Community 26 - "SALUD CERCA — Plan de Producto"
Cohesion: 0.07
Nodes (25): 1. Problema, 2. Solución: los 3 actores, 3. Módulos funcionales (M1–M6), 4.1 Ciudadano — SOS (free vs premium), 4.2 Operador B2B — ciclo completo (cliente que paga), 4.3 Contribuidor — red humana pagada (modelo Waze-salud), 4.4 Flujo de datos (persistencia), 4. Flujos de trabajo (+17 more)

### Community 28 - "AGENTS.md — Reglas permanentes para sesiones de IA (opencode)"
Cohesion: 0.25
Nodes (7): AGENTS.md — Reglas permanentes para sesiones de IA (opencode), 🎯 Contexto estratégico (no olvidar), 🗂️ Convenciones del repo, 💰 Economía de tokens, ⚠️ Entorno local conocido, graphify, 🧠 Sistema de conocimiento (obligatorio)

### Community 29 - "🗺️ SALUD CERCA — Mapa de Contenido"
Cohesion: 0.25
Nodes (8): 00 · Dashboard, 01 · Producto, 02 · Arquitectura, 03 · Sesiones (bitácora), 04 · Decisiones (ADRs), Convenciones del vault, ¿Qué es SaludCerca?, 🗺️ SALUD CERCA — Mapa de Contenido

### Community 30 - "Estado del Proyecto"
Cohesion: 0.29
Nodes (7): ⚠️ Cambio de estrategia 2026-08-22, ✅ Completado (base analítica), ✅ Completado — F-C1: Datos nacionales reales, Estado del Proyecto, Métricas clave del negocio (a instrumentar desde F1), ⏳ Pendiente, Roadmap maestro

### Community 31 - "Fuentes de Datos Investigadas (reales)"
Cohesion: 0.40
Nodes (5): Canal MINADO (gratuito/freemium), Canal OFICIAL (gratuito, batch), Estrategia de matching, Fuentes de Datos Investigadas (reales), Hallazgos regulatorios relevantes

### Community 32 - "Suscripciones y Economía"
Cohesion: 0.40
Nodes (5): Costos operativos estimados (MVP), Ejemplo de unit economics, Planes (precios orientativos mercado peruano), Reglas económicas de la red de contribuidores, Suscripciones y Economía

### Community 33 - "Visión de Producto"
Cohesion: 0.40
Nodes (5): Los 3 actores y qué gana cada uno, Por qué ganamos (moat), Problema, Propuesta de valor, Visión de Producto

### Community 34 - "Sesión 2026-08-22 — Sincronización, investigación y plan integral"
Cohesion: 0.33
Nodes (6): Hallazgos / bloqueos, Hecho, Objetivo, Sesión 2026-08-22 — Sincronización, investigación y plan integral, Siguiente sesión, Smoke test end-to-end (aprobado)

### Community 35 - "ADR-003 — Conocimiento: Obsidian vault versionado + Graphify"
Cohesion: 0.40
Nodes (5): ADR-003 — Conocimiento: Obsidian vault versionado + Graphify, Consecuencias, Contexto, Decisión, Flujo de trabajo permanente

### Community 36 - "Backlog priorizado"
Cohesion: 0.20
Nodes (8): 🔥 Ahora (F0), Backlog priorizado, 💡 Después (F2+), 📌 Siguiente (F1 — MVP despacho), ADR-002 — Stack móvil: React Native + PWA, Consecuencias, Contexto, Decisión

### Community 37 - "Evolución Tiempo Real (F0)"
Cohesion: 0.50
Nodes (4): Decisiones de diseño F0, Endpoints nuevos (backend), Evolución Tiempo Real (F0), Modelo operativo nuevo

### Community 38 - "test_minado.py"
Cohesion: 0.07
Nodes (47): main(), CLI: construye data/ipress_master.csv (RENIPRESS + OSM fusionados)., buscar_candidato(), _celda(), construir_indice(), distancia_m(), fusionar(), Matching espacial+nombre entre POIs OSM y registros RENIPRESS. (+39 more)

### Community 40 - "ADR-001 — Estrategia B2B primero (operadores de ambulancias)"
Cohesion: 0.50
Nodes (4): ADR-001 — Estrategia B2B primero (operadores de ambulancias), Consecuencias, Contexto, Decisión

### Community 41 - "ContribucionController.java"
Cohesion: 0.22
Nodes (6): ContribucionService, ContribucionController, ReporteContribucionDto, TareaVerificacionDto, org.springframework.http.ResponseEntity, org.springframework.web.bind.annotation.ExceptionHandler

### Community 42 - "org.springframework.web.bind.annotation.GetMapping"
Cohesion: 0.24
Nodes (5): DerivacionController, DerivacionDto, HealthController, org.springframework.web.bind.annotation.GetMapping, org.springframework.web.bind.annotation.RequestMapping

### Community 43 - "BusquedaService"
Cohesion: 0.30
Nodes (4): BusquedaService, ResultadoEspecialidad, BusquedaController, ResultadoBusquedaDto

### Community 44 - "2026-08-22 — Pivot ciudadano + F-C1 datos nacionales"
Cohesion: 0.25
Nodes (8): 2026-08-22 — Pivot ciudadano + F-C1 datos nacionales, Construido (F-C1), Contexto, Demo end-to-end (mismo día), Hallazgos / lecciones, Investigación web, Lecciones de depuración (para futuras sesiones), Siguiente sesión

### Community 45 - "Módulo data-mining (F-C1)"
Cohesion: 0.40
Nodes (4): Decisiones técnicas, Fuentes, Módulo data-mining (F-C1), Uso

### Community 46 - "cargar_db.py"
Cohesion: 0.67
Nodes (3): _ejecutar(), main(), Carga data/ipress_master.csv al PostgreSQL del Docker (COPY desde stdin).

### Community 47 - "ADR-004 — Cara ciudadana primero (supera ADR-001)"
Cohesion: 0.50
Nodes (4): ADR-004 — Cara ciudadana primero (supera ADR-001), Consecuencias, Contexto, Decisión

### Community 48 - "ADR-005 — Routing: Valhalla self-hosted + tráfico propio"
Cohesion: 0.50
Nodes (4): ADR-005 — Routing: Valhalla self-hosted + tráfico propio, Consecuencias, Contexto, Decisión

### Community 49 - "ADR-006 — MVP con fuentes de datos 100% gratuitas"
Cohesion: 0.50
Nodes (4): ADR-006 — MVP con fuentes de datos 100% gratuitas, Consecuencias, Contexto, Decisión

### Community 52 - "CatalogoService"
Cohesion: 0.25
Nodes (5): CatalogoService, CatalogoController, EstablecimientoDto, org.springframework.web.bind.annotation.CrossOrigin, org.springframework.web.bind.annotation.RestController

### Community 53 - "org.springframework.jdbc.core.JdbcTemplate"
Cohesion: 0.38
Nodes (5): DerivacionService, org.springframework.jdbc.core.JdbcTemplate, org.springframework.jdbc.core.RowMapper, org.springframework.stereotype.Service, org.springframework.transaction.annotation.Transactional

### Community 54 - "java.sql.ResultSet"
Cohesion: 0.33
Nodes (4): AmbulanciaCercanaMapper, Override, AmbulanciaCercanaDto, java.sql.ResultSet

## Knowledge Gaps
- **127 isolated node(s):** `pe.saludcerca:backend`, `fuentes_datos`, `🧠 Sistema de conocimiento (obligatorio)`, `💰 Economía de tokens`, `🗂️ Convenciones del repo` (+122 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SALUD CERCA — Documentación del Sistema` connect `SALUD CERCA — Documentación del Sistema` to `SALUD CERCA — Plan de Producto`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `PipelineConfig` connect `PipelineConfig` to `run_bronze`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `DataCleaner` (e.g. with `SilverWriter` and `.__init__()`) actually correct?**
  _`DataCleaner` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `PipelineConfig` (e.g. with `main()` and `BronzeWriter`) actually correct?**
  _`PipelineConfig` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `pe.saludcerca:backend`, `fuentes_datos`, `🧠 Sistema de conocimiento (obligatorio)` to the rest of the system?**
  _127 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_ml.py` be split into smaller, more focused modules?**
  _Cohesion score 0.061952074810052604 - nodes in this community are weakly interconnected._
- **Should `PipelineConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.058445353594389245 - nodes in this community are weakly interconnected._