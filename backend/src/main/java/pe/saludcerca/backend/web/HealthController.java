package pe.saludcerca.backend.web;

import java.time.OffsetDateTime;
import java.util.Map;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Health-check de la API y de la conexión a la capa Gold. */
@RestController
@RequestMapping("/api/health")
public class HealthController {

    private final JdbcTemplate jdbc;

    public HealthController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping
    public Map<String, Object> health() {
        boolean db;
        try {
            jdbc.queryForObject("SELECT 1", Integer.class);
            db = true;
        } catch (Exception e) {
            db = false;
        }
        return Map.of(
                "status", db ? "ok" : "degradado",
                "db", db,
                "timestamp", OffsetDateTime.now().toString());
    }
}
