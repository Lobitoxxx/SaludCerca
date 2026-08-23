package pe.saludcerca.backend.service;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;

import pe.saludcerca.backend.web.dto.EstablecimientoDto;

/** Búsqueda sobre el catálogo nacional real (ipress_master, F-C1). */
@Service
public class CatalogoService {

    private static final String COLUMNAS = """
            id, nombre, tipo, sector, categoria,
            departamento, provincia, distrito,
            direccion, telefono, horario, abierto_24h,
            latitud, longitud, confianza
            """;

    private final JdbcTemplate jdbc;

    public CatalogoService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static String selectBase() {
        return "SELECT " + COLUMNAS + "\n  FROM ipress_master\n";
    }

    private static final RowMapper<EstablecimientoDto> MAPPER = (rs, i) -> mapear(rs);

    private static EstablecimientoDto mapear(ResultSet rs) throws SQLException {
        Double lat = rs.getObject("latitud", Double.class);
        Double lon = rs.getObject("longitud", Double.class);
        return new EstablecimientoDto(
                rs.getLong("id"),
                rs.getString("nombre"),
                rs.getString("tipo"),
                rs.getString("sector"),
                rs.getString("categoria"),
                rs.getString("departamento"),
                rs.getString("provincia"),
                rs.getString("distrito"),
                rs.getString("direccion"),
                rs.getString("telefono"),
                rs.getString("horario"),
                (Boolean) rs.getObject("abierto_24h"),
                lat,
                lon,
                null,
                rs.getInt("confianza"));
    }

    /** Establecimientos activos con ubicación dentro de un radio, por distancia. */
    public List<EstablecimientoDto> cercanos(double lat, double lon,
                                             double radioKm, List<String> tipos,
                                             int limite) {
        StringBuilder sql = new StringBuilder("SELECT " + COLUMNAS + """
                 , ROUND((ST_Distance(geom::geography,
                        ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography)
                        / 1000.0)::numeric, 2) AS distancia_km
                  FROM ipress_master
               WHERE activo
                 AND geom IS NOT NULL
                 AND ST_DWithin(geom::geography,
                        ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography, ? * 1000)
            """);
        var params = new java.util.ArrayList<Object>(
                List.of(lon, lat, lon, lat, Math.min(radioKm, 50)));
        if (tipos != null && !tipos.isEmpty()) {
            sql.append("  AND tipo = ANY (string_to_array(?, ','))\n");
            params.add(String.join(",", tipos));
        }
        sql.append(" ORDER BY geom <-> ST_SetSRID(ST_MakePoint(?, ?), 4326)\n LIMIT ?");
        params.add(lon);
        params.add(lat);
        params.add(Math.min(limite, 200));

        return jdbc.query(sql.toString(), (rs, i) -> {
            EstablecimientoDto base = mapear(rs);
            return new EstablecimientoDto(base.id(), base.nombre(), base.tipo(),
                    base.sector(), base.categoria(), base.departamento(),
                    base.provincia(), base.distrito(), base.direccion(),
                    base.telefono(), base.horario(), base.abierto24h(),
                    base.latitud(), base.longitud(),
                    rs.getDouble("distancia_km"), base.confianza());
        }, params.toArray());
    }

    /** Búsqueda fuzzy por nombre con filtros opcionales de zona/tipo. */
    public List<EstablecimientoDto> buscar(String q, String departamento,
                                           String tipo, int limite) {
        String sql = selectBase() + """
               WHERE activo
                 AND (nombre_norm % ? OR nombre ILIKE ('%' || ? || '%'))
            """;
        var params = new java.util.ArrayList<Object>(List.of(q, q));
        if (departamento != null && !departamento.isBlank()) {
            sql += "   AND UPPER(departamento) = UPPER(?)\n";
            params.add(departamento);
        }
        if (tipo != null && !tipo.isBlank()) {
            sql += "   AND tipo = ?\n";
            params.add(tipo);
        }
        sql += " ORDER BY confianza DESC, nombre LIMIT ?";
        params.add(Math.min(limite, 100));
        return jdbc.query(sql, MAPPER, params.toArray());
    }

    /** Ficha completa de un establecimiento. */
    public EstablecimientoDto ficha(long id) {
        return jdbc.queryForObject(
                selectBase() + " WHERE id = ?", MAPPER, id);
    }
}
