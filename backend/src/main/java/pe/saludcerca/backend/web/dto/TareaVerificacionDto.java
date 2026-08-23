package pe.saludcerca.backend.web.dto;

/** Tarea de verificación geo-asignada para la red de contribuidores. */
public record TareaVerificacionDto(
        Long id,
        Integer ipressId,
        String ipressNombre,
        String tipo,
        int prioridad,
        double latitud,
        double longitud,
        double distanciaKm,
        java.math.BigDecimal recompensa) {
}
