package pe.saludcerca.backend.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import java.util.List;

import org.junit.jupiter.api.Test;

/**
 * Verifica el decodificador de encoded polyline precisión 6 que usa Valhalla.
 * Referencia generada con el algoritmo estándar (Google/Mapbox) en Python
 * para los puntos clásicos (38.5,-120.2) (40.7,-120.95) (43.252,-126.453).
 */
class RutaServiceTest {

    private static final double TOL = 1e-5;

    @Test
    void decodificaPolyline6Conocida() {
        var puntos = RutaService.decodificarPolyline6(
                "_izlhA~rlgdF_{geC~ywl@_kwzCn`{nI");
        assertThat(puntos).hasSize(3);
        assertThat(puntos.get(0).get(0)).isCloseTo(38.5, within(TOL));
        assertThat(puntos.get(0).get(1)).isCloseTo(-120.2, within(TOL));
        assertThat(puntos.get(1).get(0)).isCloseTo(40.7, within(TOL));
        assertThat(puntos.get(1).get(1)).isCloseTo(-120.95, within(TOL));
        assertThat(puntos.get(2).get(0)).isCloseTo(43.252, within(TOL));
        assertThat(puntos.get(2).get(1)).isCloseTo(-126.453, within(TOL));
    }

    @Test
    void cadenaVaciaDaListaVacia() {
        assertThat(RutaService.decodificarPolyline6(""))
                .isEqualTo(List.of());
    }
}
