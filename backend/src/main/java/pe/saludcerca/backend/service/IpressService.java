package pe.saludcerca.backend.service;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;

import pe.saludcerca.backend.web.dto.EspecialidadDto;
import pe.saludcerca.backend.web.dto.IpressCercanaDto;
import pe.saludcerca.backend.web.dto.IpressDto;

/** Consultas de establecimientos (IPRESS) y especialidades sobre la capa Gold. */
@Service
public class IpressService {

    private static final String SELECT_IPRESS =
            """
            SELECT i.codigo_renipress, i.nombre, c.codigo, c.nombre AS categoria_nombre,
                   c.nivel_atencion, i.departamento, i.provincia, i.distrito,
                   i.latitud, i.longitud, i.estado_operativo, i.capacidad_camas,
                   i.capacidad_consultorios, i.telefono, i.propietario
              FROM ipress i
              JOIN categorizaciones c ON c.id = i.categoria_id
            """;

    private final JdbcTemplate jdbc;

    public IpressService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** Detalle completo de una IPRESS por su código RENIPRESS. */
    public IpressDto detalle(String codigoRenipress) {
        return jdbc.query(SELECT_IPRESS + " WHERE i.codigo_renipress = ?",
                new IpressRowMapper(), codigoRenipress).stream().findFirst().orElse(null);
    }

    /** IPRESS ACTIVAS dentro de un radio (km) de un punto, ordenadas por distancia. */
    public List<IpressCercanaDto> cercanas(double lat, double lon, double radioKm, int limite) {
        String sql = """
                SELECT i.codigo_renipress, i.nombre, c.codigo, c.nombre AS categoria_nombre,
                       c.nivel_atencion, i.departamento, i.provincia, i.distrito,
                       i.latitud, i.longitud, i.capacidad_camas, i.capacidad_consultorios,
                       ROUND((ST_Distance(i.geom::geography,
                                          ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography) / 1000.0)::numeric, 2) AS distancia_km
                  FROM ipress i
                  JOIN categorizaciones c ON c.id = i.categoria_id
                 WHERE i.geom IS NOT NULL
                   AND i.estado_operativo = 'ACTIVO'
                   AND ST_DWithin(i.geom::geography,
                                  ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography, ? * 1000)
                 ORDER BY distancia_km ASC
                 LIMIT ?
                """;
        return jdbc.query(sql, new CercanaRowMapper(), lon, lat, lon, lat, radioKm, limite);
    }

    /** Catálogo de especialidades médicas. */
    public List<EspecialidadDto> especialidades() {
        String sql = """
                SELECT id, codigo, nombre, complejidad_minima, descripcion
                  FROM especialidades
                 ORDER BY id
                """;
        return jdbc.query(sql, (rs, i) -> new EspecialidadDto(
                rs.getInt("id"),
                rs.getString("codigo"),
                rs.getString("nombre"),
                rs.getInt("complejidad_minima"),
                rs.getString("descripcion")));
    }

    private static final class IpressRowMapper implements RowMapper<IpressDto> {
        @Override
        public IpressDto mapRow(ResultSet rs, int rowNum) throws SQLException {
            return new IpressDto(
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
        }
    }

    private static final class CercanaRowMapper implements RowMapper<IpressCercanaDto> {
        @Override
        public IpressCercanaDto mapRow(ResultSet rs, int rowNum) throws SQLException {
            return new IpressCercanaDto(
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
                    rs.getInt("capacidad_camas"),
                    rs.getInt("capacidad_consultorios"),
                    rs.getDouble("distancia_km"));
        }
    }
}
