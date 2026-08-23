package pe.saludcerca.backend.web;

import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import pe.saludcerca.backend.service.DespachoService;
import pe.saludcerca.backend.web.dto.AmbulanciaCercanaDto;
import pe.saludcerca.backend.web.dto.AsignacionDto;
import pe.saludcerca.backend.web.dto.EmergenciaDto;
import pe.saludcerca.backend.web.dto.EmergenciaNuevaDto;

/** Endpoints operativos de despacho (flota, GPS y emergencias). */
@RestController
@RequestMapping("/api/despacho")
public class DespachoController {

    private final DespachoService service;

    public DespachoController(DespachoService service) {
        this.service = service;
    }

    /** Unidades DISPONIBLES más cercanas a un punto. */
    @GetMapping("/ambulancias/cercanas")
    public List<AmbulanciaCercanaDto> ambulanciasCercanas(
            @RequestParam double lat,
            @RequestParam double lon,
            @RequestParam(defaultValue = "25") double radioKm,
            @RequestParam(defaultValue = "BASICA") String tipoMin,
            @RequestParam(defaultValue = "5") int limite) {
        return service.ambulanciasCercanas(lat, lon, radioKm, tipoMin, limite);
    }

    /** Reporte de posición GPS desde la app del conductor. */
    @PostMapping("/ambulancias/{id}/posicion")
    public ResponseEntity<Void> reportarPosicion(
            @PathVariable int id,
            @RequestParam double lat,
            @RequestParam double lon,
            @RequestParam(required = false) Integer velocidadKmh) {
        service.reportarPosicion(id, lat, lon, velocidadKmh);
        return ResponseEntity.accepted().build();
    }

    /** Crear emergencia (canal APP/PWA/WHATSAPP/LLAMADA/PANEL). */
    @PostMapping("/emergencias")
    public ResponseEntity<EmergenciaDto> crearEmergencia(@RequestBody EmergenciaNuevaDto dto) {
        EmergenciaDto creada = service.crearEmergencia(dto);
        return ResponseEntity.status(201).body(creada);
    }

    /** Cola operativa de emergencias activas. */
    @GetMapping("/emergencias/activas")
    public List<EmergenciaDto> emergenciasActivas() {
        return service.emergenciasActivas();
    }

    /** Asignar una unidad disponible a una emergencia. */
    @PostMapping("/emergencias/{emergenciaId}/asignar/{ambulanciaId}")
    public ResponseEntity<AsignacionDto> asignar(
            @PathVariable Long emergenciaId, @PathVariable int ambulanciaId) {
        AsignacionDto asignacion = service.asignar(emergenciaId, ambulanciaId);
        return asignacion != null ? ResponseEntity.ok(asignacion)
                                  : ResponseEntity.notFound().build();
    }
}
