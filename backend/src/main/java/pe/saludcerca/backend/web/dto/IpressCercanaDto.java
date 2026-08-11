package pe.saludcerca.backend.web.dto;

/** IPRESS activa con distancia en km al punto de consulta. */
public record IpressCercanaDto(
        String codigoRenipress,
        String nombre,
        String categoria,
        String categoriaNombre,
        int nivelAtencion,
        String departamento,
        String provincia,
        String distrito,
        Double latitud,
        Double longitud,
        int capacidadCamas,
        int capacidadConsultorios,
        Double distanciaKm) {
}
