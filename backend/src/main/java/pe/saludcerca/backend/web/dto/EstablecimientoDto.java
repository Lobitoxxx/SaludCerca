package pe.saludcerca.backend.web.dto;

/** Establecimiento del catálogo nacional real (ipress_master). */
public record EstablecimientoDto(
        long id,
        String nombre,
        String tipo,
        String sector,
        String categoria,
        String departamento,
        String provincia,
        String distrito,
        String direccion,
        String telefono,
        String horario,
        Boolean abierto24h,
        Double latitud,
        Double longitud,
        Double distanciaKm,
        Integer confianza) {
}
