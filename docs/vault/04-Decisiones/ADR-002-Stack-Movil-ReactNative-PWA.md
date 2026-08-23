---
tags: [adr, stack]
estado: aceptada
fecha: 2026-08-22
---

# ADR-002 — Stack móvil: React Native + PWA

## Contexto
Se necesita cara ciudadana (SOS + GPS) y panel del conductor. El README original ya preveía frontend React para el dashboard.

## Decisión
- **PWA React** primero: botón SOS + geolocalización funciona sin tiendas de apps; MVP más barato ([[Backlog]] F1).
- **React Native** después para la app instalable (push notifications fiables, background location) reutilizando lógica JS/TS.

## Consecuencias
- ✅ Una sola familia tecnológica JS/TS; componentes compartibles PWA↔RN.
- ✅ WhatsApp Business API cubre a usuarios sin app (canal crítico en Perú).
- ⚠️ Background GPS en iOS exige app nativa → justifica RN en F5, no antes.
