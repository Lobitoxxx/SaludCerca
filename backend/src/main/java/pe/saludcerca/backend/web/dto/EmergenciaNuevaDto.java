package pe.saludcerca.backend.web.dto;

/** Solicitud de creación de emergencia (canal ciudadano o panel operador). */
public record EmergenciaNuevaDto(
        String canal,
        String telefonoCiudadano,
        String direccionReferencia,
        double latitud,
        double longitud,
        String triaje,
        String descripcion,
        Integer especialidadRequerida) {
}
