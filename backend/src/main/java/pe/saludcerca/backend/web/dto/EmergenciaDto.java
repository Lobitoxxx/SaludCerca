package pe.saludcerca.backend.web.dto;

/** Vista de emergencia para la cola operativa. */
public record EmergenciaDto(
        Long id,
        String codigo,
        String canal,
        String estado,
        String triaje,
        double latitud,
        double longitud,
        String direccionReferencia,
        Integer hospitalDestinoId,
        Long creadaEnEpochMs,
        Long asignadaEnEpochMs,
        Long llegadaEscenaEpochMs) {
}
