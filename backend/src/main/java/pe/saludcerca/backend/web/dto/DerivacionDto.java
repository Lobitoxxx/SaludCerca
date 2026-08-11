package pe.saludcerca.backend.web.dto;

/** Candidato devuelto por el motor de derivación ({@code recomendar_derivacion}). */
public record DerivacionDto(
        String codigoRenipress,
        String nombre,
        int nivelAtencion,
        String departamento,
        Double distanciaKm,
        Double saturacionPromedio,
        Double capacidadDisponible,
        Long historialEspecialidad,
        Double score) {
}
