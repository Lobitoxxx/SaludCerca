package pe.saludcerca.backend.service;

import java.sql.Date;
import java.time.LocalDate;
import java.util.List;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;

import pe.saludcerca.backend.web.dto.DerivacionDto;

/**
 * Motor de derivación: expone {@code recomendar_derivacion()} de PostgreSQL
 * (score 0-100 anti-saturación) como llamada REST.
 */
@Service
public class DerivacionService {

    private final JdbcTemplate jdbc;

    public DerivacionService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * Recomienda destinos para derivar a un paciente.
     *
     * @param origenCodigo código RENIPRESS del establecimiento origen
     * @param especialidadId id de la especialidad (puede ser null)
     * @param fecha fecha de la derivación (null → hoy)
     * @param topN máximo de candidatos (null → 5)
     */
    public List<DerivacionDto> recomendar(
            String origenCodigo, Integer especialidadId, LocalDate fecha, Integer topN) {
        String sql = """
                SELECT codigo_renipress, nombre, nivel_atencion, departamento,
                       distancia_km, saturacion_promedio, capacidad_disponible,
                       historial_especialidad, score
                  FROM recomendar_derivacion(?, ?, ?, ?)
                """;
        Date fechaSql = (fecha != null) ? Date.valueOf(fecha) : Date.valueOf(LocalDate.now());
        int limite = (topN != null && topN > 0) ? topN : 5;
        return jdbc.query(sql, DERIVACION_MAPPER,
                origenCodigo, especialidadId, fechaSql, limite);
    }

    private static final RowMapper<DerivacionDto> DERIVACION_MAPPER =
            (rs, i) -> new DerivacionDto(
                    rs.getString("codigo_renipress"),
                    rs.getString("nombre"),
                    rs.getInt("nivel_atencion"),
                    rs.getString("departamento"),
                    rs.getDouble("distancia_km"),
                    rs.getDouble("saturacion_promedio"),
                    rs.getDouble("capacidad_disponible"),
                    rs.getLong("historial_especialidad"),
                    rs.getDouble("score"));
}
