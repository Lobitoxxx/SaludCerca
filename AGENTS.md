# AGENTS.md — Reglas permanentes para sesiones de IA (opencode)

Proyecto: **SaludCerca** — lakehouse geo-analítico sanitario del Perú evolucionando a SaaS de despacho de emergencias/ambulancias por suscripción.
Idioma de trabajo: **español**. Commits estilo convencional (`feat:`, `fix:`, `chore:`, `docs:`).

## 🧠 Sistema de conocimiento (obligatorio)
1. **Inicio de sesión**: leer `docs/vault/_MOC.md` y `graphify-out/GRAPH_REPORT.md` ANTES de explorar código.
2. **Nunca escanear el repo completo si la nota ya responde**: usar lecturas dirigidas (Grep/Glob sobre archivos específicos).
3. **Tras cada hito**: actualizar `docs/vault/00-Dashboard/Estado-Proyecto.md` + `Backlog.md`, crear bitácora en `03-Sesiones/YYYY-MM-DD-<tema>.md`.
4. Si tocas código estructural (esquema DB, endpoints, módulos), actualizar su nota atómica correspondiente.
5. Tras hitos mayores: ejecutar `graphify . --update` (requiere Python; paquete `graphifyy`).

## 💰 Economía de tokens
- Preferir resúmenes del vault y GRAPH_REPORT.md sobre relecturas completas.
- Delegar búsquedas amplias al subagente `explore`; leer archivos puntuales directamente.
- Diagramas en Mermaid dentro de Markdown (renderiza GitHub + Obsidian); nunca generar imágenes binarias.

## 🗂️ Convenciones del repo
| Área | Regla |
|---|---|
| SQL | Scripts en `db/init/NN_*.sql` solo corren en PRIMER arranque del volumen Docker; para volúmenes existentes aplicar manualmente con `docker compose exec -T db psql -U saludcerca -d saludcerca < archivo.sql`. Estilo: cabecera comentada, dominios CHECK, índices GIST para geom |
| Backend | Java 17 + Spring Boot 3.5, JDBC plano con `JdbcTemplate` (sin JPA), DTOs como records, SQL en text blocks |
| Pipeline | PySpark 3.5 medallón Bronze/Silver/Gold; idempotencia obligatoria; escribir MANIFEST |
| Docs | `docs/SISTEMA.md` = técnica canónica · `docs/PRODUCTO.md` = negocio/producto · vault = conocimiento vivo |

## 🎯 Contexto estratégico (no olvidar)
- Cliente inicial: **operadores B2B de ambulancias** (ADR-001); cara ciudadana después.
- Motor estrella a reutilizar: `recomendar_derivacion()` (score 50% anti-saturación / 30% cercanía / 20% nivel+historial).
- Fuentes reales investigadas en `docs/vault/01-Producto/Fuentes-Datos-Investigacion.md` — hoy los datos son sintéticos.
- Roadmap fases F0→F5 en `Estado-Proyecto`; regulatorio clave: SAMU 106, SUSALUD, Ley 29733.

## ⚠️ Entorno local conocido
- Windows + PowerShell 5.1 · Python 3.14 ✓ · Docker ✓ · **JDK no en PATH** (instalar Temurin 17 para build Maven).
- Tests pipeline requieren correr desde `data-pipeline/` (rutas relativas); tests ML calculan su propio root.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
