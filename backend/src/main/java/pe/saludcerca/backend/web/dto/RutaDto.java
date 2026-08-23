package pe.saludcerca.backend.web.dto;

import java.util.List;

/** Resultado de ruta entre dos puntos (Valhalla), con geometría lista para Leaflet. */
public record RutaDto(
        double distanciaKm,
        double minutosEta,
        String costing,
        List<List<Double>> geometria) {
}
