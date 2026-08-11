package pe.saludcerca.backend.web.dto;

/** Resultado de la búsqueda semántica: IPRESS + similitud coseno (0..1). */
public record ResultadoBusquedaDto(
        IpressDto ipress,
        double similitud) {
}
