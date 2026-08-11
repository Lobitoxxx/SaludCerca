package pe.saludcerca.backend.web.dto;

/** Representación de un establecimiento de salud (IPRESS). */
public record IpressDto(
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
        String estadoOperativo,
        int capacidadCamas,
        int capacidadConsultorios,
        String telefono,
        String propietario) {
}
