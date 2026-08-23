package pe.saludcerca.backend.web;

import java.util.List;
import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import pe.saludcerca.backend.service.ContribucionService;
import pe.saludcerca.backend.web.dto.ReporteContribucionDto;
import pe.saludcerca.backend.web.dto.TareaVerificacionDto;

/** Endpoints de la red de contribuidores (módulo M6). */
@RestController
@RequestMapping("/api/contribucion")
public class ContribucionController {

    private final ContribucionService service;

    public ContribucionController(ContribucionService service) {
        this.service = service;
    }

    /** Cola de tareas de verificación cercanas al contribuidor. */
    @GetMapping("/tareas")
    public List<TareaVerificacionDto> tareasCercanas(
            @RequestParam double lat,
            @RequestParam double lon,
            @RequestParam(defaultValue = "10") double radioKm,
            @RequestParam(defaultValue = "10") int limite) {
        return service.tareasCercanas(lat, lon, radioKm, limite);
    }

    /** Recibir un reporte desde el campo (valida geocerca de 500 m). */
    @PostMapping("/reportes")
    public ResponseEntity<Long> recibirReporte(@RequestBody ReporteContribucionDto dto) {
        Long id = service.recibirReporte(dto);
        return ResponseEntity.status(201).body(id);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, String>> geocercaInvalida(IllegalArgumentException ex) {
        return ResponseEntity.badRequest().body(Map.of("error", ex.getMessage()));
    }
}
