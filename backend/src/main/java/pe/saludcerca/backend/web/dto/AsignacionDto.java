package pe.saludcerca.backend.web.dto;

/** Resultado de una asignación emergencia-ambulancia. */
public record AsignacionDto(
        Long id,
        Long emergenciaId,
        Integer ambulanciaId,
        String estado,
        java.math.BigDecimal distanciaKm,
        Integer etaMin) {
}
