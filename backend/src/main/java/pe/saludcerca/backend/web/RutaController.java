package pe.saludcerca.backend.web;

import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import pe.saludcerca.backend.service.RutaService;
import pe.saludcerca.backend.web.dto.RutaDto;

/** Rutas ciudadanas origen→establecimiento (módulo F-C2). */
@RestController
@RequestMapping("/api/ruta")
@CrossOrigin(origins = "*")
public class RutaController {

    private final RutaService service;

    public RutaController(RutaService service) {
        this.service = service;
    }

    /** Ruta por red vial real con ETA (costing: auto|bicycle|pedestrian|motorcycle). */
    @GetMapping
    public RutaDto ruta(
            @RequestParam double latOrigen,
            @RequestParam double lonOrigen,
            @RequestParam double latDestino,
            @RequestParam double lonDestino,
            @RequestParam(required = false) String costing) {
        return service.ruta(latOrigen, lonOrigen, latDestino, lonDestino, costing);
    }
}
