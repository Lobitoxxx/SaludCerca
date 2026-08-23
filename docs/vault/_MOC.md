---
tags: [moc, indice]
estado: estable
actualizado: 2026-08-22
---

# 🗺️ SALUD CERCA — Mapa de Contenido

> Punto de entrada del vault. **Leyendo esto primero se entiende el proyecto completo sin abrir código.**

## ¿Qué es SaludCerca?
Sistema geo-analítico de cobertura sanitaria del Perú que evoluciona hacia una **plataforma SaaS de emergencias médicas y despacho de ambulancias por suscripción**.
- Documento técnico actual: [[Arquitectura-Actual]] · Detalle completo: `docs/SISTEMA.md`
- Plan de producto: `docs/PRODUCTO.md` · Visión: [[Vision-Producto]]

## 00 · Dashboard
| Nota | Contenido |
|---|---|
| [[Estado-Proyecto]] | Fase actual F0→F5 con checklist de avance |
| [[Backlog]] | Tareas pendientes priorizadas |

## 01 · Producto
| Nota | Contenido |
|---|---|
| [[Vision-Producto]] | Problema, propuesta de valor, actores |
| [[Modulos-M1-M6]] | Resumen funcional de los 6 módulos |
| [[Suscripciones-Economia]] | Planes de pago, fondo de datos |
| [[Fuentes-Datos-Investigacion]] | APIs y datasets reales investigados (URLs) |

## 02 · Arquitectura
| Nota | Contenido |
|---|---|
| [[Arquitectura-Actual]] | Lakehouse medallón + PostGIS/pgvector + API (lo construido) |
| [[Evolucion-Tiempo-Real]] | Capa operativa nueva: despacho, contribuidores (F0) |
| `data-mining/README.md` | Catálogo nacional real: RENIPRESS+OSM → ipress_master (F-C1) |

## 03 · Sesiones (bitácora)
| Nota | Fecha | Resumen |
|---|---|---|
| [[2026-08-22-Sincronizacion-y-Planificacion]] | 2026-08-22 | Repo sincronizado, investigación fuentes, plan integral, arranque F0 |
| [[2026-08-22-Portal-Ciudadano-FC1]] | 2026-08-22 | Pivot ciudadano (ADR-004), F-C1 completo: 38.8k establecimientos reales en BD |

## 04 · Decisiones (ADRs)
| ADR | Decisión |
|---|---|
| [[ADR-004-Ciudadano-Primero]] | **VIGENTE**: cara ciudadana primero; B2B reutiliza después |
| [[ADR-005-Routing-Valhalla-Trafico-Propio]] | Valhalla self-hosted + tráfico propio desde telemetría |
| [[ADR-006-Fuentes-Gratis-MVP]] | MVP con RENIPRESS+OSM+datos abiertos; Google Places diferido |
| [[ADR-001-Estrategia-B2B-Primero]] | ~SUPERADO por ADR-004~ (histórico) |
| [[ADR-002-Stack-Movil-ReactNative-PWA]] | React Native + PWA para la cara ciudadana |
| [[ADR-003-Conocimiento-Obsidian-Graphify]] | Vault Obsidian versionado + grafo Graphify para optimizar tokens |

---

## Convenciones del vault
1. **Notas atómicas**: una nota = un concepto, con frontmatter (`tags`, `estado`, `actualizado`).
2. **Wikilinks** `[[]]` entre notas → alimenta el graph view de Obsidian.
3. **Diagramas en Mermaid** dentro de bloques ```mermaid``` (renderiza en Obsidian y GitHub).
4. Tras cada hito: actualizar [[Estado-Proyecto]], crear nota en `03-Sesiones/`, correr `graphify . --update`.
