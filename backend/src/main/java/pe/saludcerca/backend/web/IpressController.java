package pe.saludcerca.backend.web;

import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import pe.saludcerca.backend.service.IpressService;
import pe.saludcerca.backend.web.dto.EspecialidadDto;
import pe.saludcerca.backend.web.dto.IpressCercanaDto;
import pe.saludcerca.backend.web.dto.IpressDto;

/** Endpoints de establecimientos de salud (IPRESS) y catálogos. */
@RestController
@RequestMapping("/api")
public class IpressController {

    private final IpressService service;

    public IpressController(IpressService service) {
        this.service = service;
    }

    /** Detalle de una IPRESS por código RENIPRESS. */
    @GetMapping("/ipress/{codigo}")
    public ResponseEntity<IpressDto> detalle(@PathVariable String codigo) {
        IpressDto ipress = service.detalle(codigo);
        return ipress != null ? ResponseEntity.ok(ipress) : ResponseEntity.notFound().build();
    }

    /** IPRESS ACTIVAS dentro de un radio (km) de un punto, por cercanía. */
    @GetMapping("/ipress/cercanas")
    public List<IpressCercanaDto> cercanas(
            @RequestParam double lat,
            @RequestParam double lon,
            @RequestParam(defaultValue = "25") double radioKm,
            @RequestParam(defaultValue = "10") int limite) {
        return service.cercanas(lat, lon, radioKm, Math.min(limite, 50));
    }

    /** Catálogo de especialidades médicas. */
    @GetMapping("/especialidades")
    public List<EspecialidadDto> especialidades() {
        return service.especialidades();
    }
}
