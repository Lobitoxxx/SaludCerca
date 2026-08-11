package pe.saludcerca.backend.web;

import java.time.LocalDate;
import java.util.List;

import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import pe.saludcerca.backend.service.DerivacionService;
import pe.saludcerca.backend.web.dto.DerivacionDto;

/** Motor de derivación inteligente (anti-saturación) vía REST. */
@RestController
@RequestMapping("/api/derivacion")
public class DerivacionController {

    private final DerivacionService service;

    public DerivacionController(DerivacionService service) {
        this.service = service;
    }

    /** Recomienda destinos ACTIVOS, de nivel adecuado, no saturados y cercanos. */
    @GetMapping("/recomendar")
    public List<DerivacionDto> recomendar(
            @RequestParam String origen,
            @RequestParam(required = false) Integer especialidad,
            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate fecha,
            @RequestParam(defaultValue = "5") int topN) {
        return service.recomendar(origen, especialidad, fecha, topN);
    }
}
