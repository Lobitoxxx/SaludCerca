package pe.saludcerca.backend.web;

import java.util.List;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import pe.saludcerca.backend.service.BusquedaService;
import pe.saludcerca.backend.service.BusquedaService.ResultadoEspecialidad;
import pe.saludcerca.backend.web.dto.ResultadoBusquedaDto;

/**
 * Búsqueda semántica: codifica el texto con {@code SemanticEncoder} (mismos
 * embeddings que el pipeline Python) y busca por similitud coseno en pgvector.
 */
@RestController
@RequestMapping("/api/buscar")
public class BusquedaController {

    private final BusquedaService service;

    public BusquedaController(BusquedaService service) {
        this.service = service;
    }

    /** IPRESS más similares semánticamente a un texto (topK). */
    @GetMapping("/ipress")
    public List<ResultadoBusquedaDto> buscarIpress(
            @RequestParam String texto,
            @RequestParam(defaultValue = "5") int topK) {
        return service.buscarIpress(texto, Math.min(Math.max(topK, 1), 20));
    }

    /** Especialidades más similares semánticamente a un texto (topK). */
    @GetMapping("/especialidad")
    public List<ResultadoEspecialidad> buscarEspecialidad(
            @RequestParam String texto,
            @RequestParam(defaultValue = "3") int topK) {
        return service.buscarEspecialidad(texto, Math.min(Math.max(topK, 1), 10));
    }
}
