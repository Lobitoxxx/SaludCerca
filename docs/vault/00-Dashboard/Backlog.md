---
tags: [backlog, tareas]
estado: vivo
actualizado: 2026-08-22
---

# Backlog priorizado

## 🔥 Ahora (F0)
- [x] ~~Aplicar 08/09 al contenedor~~ → resuelto recreando volumen limpio (`docker compose down -v && up -d db`); init corrió los 9 scripts sin errores
- [x] Código backend `despacho` + `contribucion` escrito (controllers/services/DTOs records)
- [x] **JDK 17 instalado** (Temurin 17.0.20) — `mvnw package` BUILD SUCCESS, tests OK
- [x] Smoke test API end-to-end contra Docker: cercanas ✓, crear emergencia ✓, asignar ✓, GPS (204) ✓, tareas contribución ✓, reporte válido 201 ✓, geocerca inválida 400 ✓
- [ ] Añadir tests del módulo despacho al CI (job backend)
- [ ] Registro/login de contribuidores (hoy `contribuidorId` viene del cliente; falta auth mínima)

## 📌 Siguiente (F1 — MVP despacho)
- [ ] Elegir motor de rutas: OSRM self-hosted vs Valhalla (decidir en ADR)
- [ ] WebSocket/SSE para mapa en vivo del panel operador
- [ ] Auth JWT multi-tenant (organizaciones) — evaluar Spring Security + refresh
- [ ] PWA ciudadana: botón SOS + GPS + estado de la solicitud
- [ ] Panel operador React: mapa flota + cola emergencias

## 💡 Después (F2+)
- [ ] Módulo `data-mining/`: descarga RENIPRESS real (~35k), minería OSM Overpass Perú, matcher fuzzy
- [ ] Derivación v2: integrar hospital_capacidad_rt en el score
- [ ] Culqi/Izipay: suscripciones + webhooks
- [ ] App móvil React Native (ver [[ADR-002-Stack-Movil-ReactNative-PWA]])
- [ ] Forecast zonal×hora para dynamic standby
- [ ] MCP server de Graphify en opencode.json (opcional)
