package pe.saludcerca.backend.web.dto;

/** Unidad DISPONIBLE cercana a un punto (resultado de ambulancia_disponible_cercana). */
public record AmbulanciaCercanaDto(
        Integer id,
        String placa,
        String tipo,
        Integer organizacionId,
        double distanciaKm,
        Long ultimaPosicionEpochMs) {
}
