package pe.saludcerca.backend.web.dto;

/** Especialidad médica del catálogo (con el nivel de atención mínimo requerido). */
public record EspecialidadDto(
        int id,
        String codigo,
        String nombre,
        int complejidadMinima,
        String descripcion) {
}
