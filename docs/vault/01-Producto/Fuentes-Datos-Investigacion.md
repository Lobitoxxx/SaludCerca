---
tags: [datos, investigacion, fuentes]
estado: estable
actualizado: 2026-08-22
---

# Fuentes de Datos Investigadas (reales)

> Investigación web del 2026-08-22. Alimenta el módulo de enriquecimiento ([[Modulos-M1-M6]] M6) y la fase F2.

## Canal OFICIAL (gratuito, batch)

| Fuente | Qué aporta | URL clave | Nota |
|---|---|---|---|
| **RENIPRESS SUSALUD** | **~35.000 IPRESS** (19× nuestro dataset sintético de 1.844): código único, estado ACTIVO/Cierre/Baja, servicios autorizados, director médico, teléfono, horario | datosabiertos.gob.pe/dataset/minsa-ipress · CSV directo publicado por SUSALUD | Actualización mensual. RENAES (MINSA) es el antecesor; RENIPRESS es el vigente |
| **SUSALUD Recursos por IPRESS** | Consultorios físicos/funcionales y **N° DE AMBULANCIAS POR IPRESS** ⭐ | datos.susalud.gob.pe/dataset | Crítico para dimensionar flota nacional |
| **SUSALUD F500.2** | Histórico disponibilidad camas UCI/hospitalización | datos.susalud.gob.pe | Base para validar hospital_capacidad_rt |
| **HIS-MINSA / SIS** | Atenciones reales por establecimiento (morbilidad, emergencias) | datosabiertos.gob.pe grupo MINSA/SIS | Reemplaza el dataset sintético |
| **MINSA REUNIS** | Población estimada por distrito año en curso | minsa.gob.pe/reunis | Demanda potencial |
| **INEI** | Proyecciones población en **1.874 distritos** (nuestro ubigeo tiene 957) | inei.gob.pe | Índice cobertura/10k hab correcto |

## Canal MINADO (gratuito/freemium)

| Fuente | Qué aporta | Costo |
|---|---|---|
| **OSM Overpass API** | POIs salud `amenity=hospital/clinic/doctors/pharmacy` con coords, teléfono, horarios, operador. Captura clínicas privadas fuera del foco RENIPRESS. Instancias públicas gratuitas (overpass-api.de, maps.mail.ru, private.coffee) | Gratis |
| **Google Places API** | Metadata premium: horarios ocupados, popularidad, reviews | $200/mes crédito gratis; luego pago → usar SOLO top 500 |

## Estrategia de matching
Fuzzy-join entre fuentes por `nombre_normalizado + dirección + distancia geo < 200m`
→ tabla puente con `confianza_match`. Sin match = candidato nuevo a verificar por [[Modulos-M1-M6|M6 contribuidores]].

## Hallazgos regulatorios relevantes
- RENIPRESS es declaración jurada de la IPRESS ante SUSALUD (información supervisable).
- Línea gratuita SUSALUD 113 opc.7 recibe denuncias de establecimientos irregulares → señal útil para tareas de verificación.
- SAMU (106) tiene dataset abierto en el grupo MINSA → benchmark de tiempos de respuesta.
