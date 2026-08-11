package pe.saludcerca.backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Punto de entrada del backend SALUD CERCA.
 * API REST sobre la capa Gold: IPRESS por cercanía (PostGIS),
 * búsqueda semántica (pgvector) y motor de derivación.
 */
@SpringBootApplication
public class SaludCercaBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(SaludCercaBackendApplication.class, args);
    }
}
