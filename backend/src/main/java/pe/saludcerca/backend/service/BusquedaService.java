package pe.saludcerca.backend.service;

import java.util.List;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;

import pe.saludcerca.backend.semantic.SemanticEncoder;
import pe.saludcerca.backend.web.dto.IpressDto;
import pe.saludcerca.backend.web.dto.ResultadoBusquedaDto;

/**
 * Búsqueda semántica sobre pgvector. El texto de la consulta se codifica con
 * {@link SemanticEncoder} (mismo embedding que el pipeline Python) y se ordenan
 * las IPRESS por similitud coseno ({@code <=>}) contra {@code ipress.descripcion_emb}.
 */
@Service
public class BusquedaService {

    private final JdbcTemplate jdbc;

    public BusquedaService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** IPRESS más similares semánticamente a {@code texto}. */
    public List<ResultadoBusquedaDto> buscarIpress(String texto, int topK) {
        String emb = SemanticEncoder.embedPostgres(texto);
        String sql = """
                SELECT i.codigo_renipress, i.nombre, c.codigo, c.nombre AS categoria_nombre,
                       c.nivel_atencion, i.departamento, i.provincia, i.distrito,
                       i.latitud, i.longitud, i.estado_operativo, i.capacidad_camas,
                       i.capacidad_consultorios, i.telefono, i.propietario,
                       (1.0 - (i.descripcion_emb <=> ?::vector)) AS similitud
                  FROM ipress i
                  JOIN categorizaciones c ON c.id = i.categoria_id
                 ORDER BY i.descripcion_emb <=> ?::vector ASC
                 LIMIT ?
                """;
        return jdbc.query(sql, (rs, rowNum) -> {
            IpressDto ipress = new IpressDto(
                    rs.getString("codigo_renipress"),
                    rs.getString("nombre"),
                    rs.getString("codigo"),
                    rs.getString("categoria_nombre"),
                    rs.getInt("nivel_atencion"),
                    rs.getString("departamento"),
                    rs.getString("provincia"),
                    rs.getString("distrito"),
                    rs.getObject("latitud", Double.class),
                    rs.getObject("longitud", Double.class),
                    rs.getString("estado_operativo"),
                    rs.getInt("capacidad_camas"),
                    rs.getInt("capacidad_consultorios"),
                    rs.getString("telefono"),
                    rs.getString("propietario"));
            return new ResultadoBusquedaDto(ipress, rs.getDouble("similitud"));
        }, emb, emb, topK);
    }

    /** Especialidades del catálogo más similares semánticamente a {@code texto}. */
    public List<ResultadoEspecialidad> buscarEspecialidad(String texto, int topK) {
        String emb = SemanticEncoder.embedPostgres(texto);
        String sql = """
                SELECT e.id, e.codigo, e.nombre, e.complejidad_minima, e.descripcion,
                       (1.0 - (e.descripcion_emb <=> ?::vector)) AS similitud
                  FROM especialidades e
                 ORDER BY e.descripcion_emb <=> ?::vector ASC
                 LIMIT ?
                """;
        return jdbc.query(sql, (rs, rowNum) -> new ResultadoEspecialidad(
                rs.getInt("id"),
                rs.getString("codigo"),
                rs.getString("nombre"),
                rs.getInt("complejidad_minima"),
                rs.getString("descripcion"),
                rs.getDouble("similitud")), emb, emb, topK);
    }

    /** Especialidad con su similitud (para la búsqueda semántica de catálogo). */
    public record ResultadoEspecialidad(
            int id, String codigo, String nombre,
            int complejidadMinima, String descripcion, double similitud) {
    }
}
