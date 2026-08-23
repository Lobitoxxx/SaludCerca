---
tags: [adr, producto, estrategia]
estado: aceptada
fecha: 2026-08-22
---

# ADR-001 — Estrategia B2B primero (operadores de ambulancias)

## Contexto
SaludCerca nace como buscador ciudadano de centros de salud. El pivot a SaaS ([[Vision-Producto]]) exige elegir cliente inicial: ciudadano masivo vs operadores B2B de ambulancias.

Factores:
- El ciudadano exige densidad de datos en tiempo real que aún no tenemos → arranque en frío.
- El operador B2B **paga desde el día 1** (dolor agudo: despacho a ciegas por WhatsApp/radio).
- Nuestro motor `recomendar_derivacion()` ya resuelve su problema core.
- Regulación: operar como software B2B privado evita fricción con SAMU 106 (Ley 29733).

## Decisión
**B2B primero**: organizaciones operadoras (privadas/municipales) con flotas de ambulancias; cara ciudadana (SOS/PWA) llega después (F4-F5), alimentada por los datos que el lado B2B genera.

## Consecuencias
- ✅ Ingresos tempranos por suscripción (~S/250-400/unidad/mes) financian la red de datos ([[Suscripciones-Economia]]).
- ✅ Cada emergencia B2B genera trazabilidad real → moat de datos para la fase ciudadana.
- ⚠️ Ventas consultivas más lentas que self-service ciudadano; requiere pilotos con 2-3 operadores limeños.
- ⚠️ La marca "SaludCerca" ciudadana se construye tarde; mitigable lanzando PWA informativa ligera pronto.
