package pe.saludcerca.backend.web;

import java.util.List;

import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import pe.saludcerca.backend.service.CatalogoService;
import pe.saludcerca.backend.web.dto.EstablecimientoDto;

/** Buscador ciudadano sobre el catálogo nacional (módulo F-C1/F-C3). */
@RestController
@RequestMapping("/api/establecimientos")
@CrossOrigin(origins = "*")
public class CatalogoController {

    private final CatalogoService service;

    public CatalogoController(CatalogoService service) {
        this.service = service;
    }

    /** Establecimientos cercanos a una coordenada (KNN real por red vial aprox). */
    @GetMapping("/cercanos")
    public List<EstablecimientoDto> cercanos(
            @RequestParam double lat,
            @RequestParam double lon,
            @RequestParam(defaultValue = "5") double radioKm,
            @RequestParam(required = false) String tipos,
            @RequestParam(defaultValue = "25") int limite) {
        List<String> listaTipos = tipos == null || tipos.isBlank()
                ? List.of()
                : List.of(tipos.toUpperCase().split("\\s*,\\s*"));
        return service.cercanos(lat, lon, radioKm, listaTipos, limite);
    }

    /** Búsqueda fuzzy por nombre con filtros opcionales. */
    @GetMapping("/buscar")
    public List<EstablecimientoDto> buscar(
            @RequestParam String q,
            @RequestParam(required = false) String departamento,
            @RequestParam(required = false) String tipo,
            @RequestParam(defaultValue = "20") int limite) {
        return service.buscar(q, departamento, tipo, limite);
    }

    /** Ficha de un establecimiento. */
    @GetMapping("/{id}")
    public EstablecimientoDto ficha(@PathVariable long id) {
        return service.ficha(id);
    }
}
