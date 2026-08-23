-- ============================================================================
-- 11_trafico_segmentos.sql — Semilla de tráfico propio (ADR-005, fase F-C2)
-- ----------------------------------------------------------------------------
-- Almacena velocidades observadas por segmento OSM para ajustar el ETA de
-- Valhalla según la hora del día. La fuente inicial será telemetría de flota
-- (fase F-C4); hoy queda como esquema base para pruebas con datos sintéticos.
--
-- Aplicar manualmente si el volumen ya existe:
--   docker compose exec -T db psql -U saludcerca -d saludcerca < db/init/11_trafico_segmentos.sql
-- ============================================================================

-- Velocidad media observada por segmento OSM, hora y tipo de día.
CREATE TABLE IF NOT EXISTS trafico_segmento (
    id             BIGSERIAL PRIMARY KEY,
    way_id         BIGINT        NOT NULL,          -- id del way en OpenStreetMap
    geom           GEOMETRY(LINESTRING, 4326),      -- traza aproximada del segmento
    hora           SMALLINT      NOT NULL CHECK (hora BETWEEN 0 AND 23),
    dia_tipo       TEXT          NOT NULL DEFAULT 'HABIL'
                                 CHECK (dia_tipo IN ('HABIL', 'FIN_SEMANA', 'FERIADO')),
    velocidad_kmh  NUMERIC(5,2)  NOT NULL CHECK (velocidad_kmh > 0 AND velocidad_kmh <= 150),
    muestras       INTEGER       NOT NULL DEFAULT 0 CHECK (muestras >= 0),
    confianza      SMALLINT      NOT NULL DEFAULT 0
                                 CHECK (confianza BETWEEN 0 AND 100),
    actualizado_en TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (way_id, hora, dia_tipo)
);

COMMENT ON TABLE  trafico_segmento IS 'Velocidades por segmento OSM/hora/día para ETA dinámico (telemetría futura de flota)';
COMMENT ON COLUMN trafico_segmento.confianza IS '0-100: crece con muestras y frescura; alimenta el peso al promediar';

CREATE INDEX IF NOT EXISTS idx_trafico_geom ON trafico_segmento USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_trafico_way  ON trafico_segmento (way_id);
