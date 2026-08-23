package pe.saludcerca.backend.service;

import java.math.BigDecimal;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Types;
import java.util.List;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import pe.saludcerca.backend.web.dto.AmbulanciaCercanaDto;
import pe.saludcerca.backend.web.dto.AsignacionDto;
import pe.saludcerca.backend.web.dto.EmergenciaDto;
import pe.saludcerca.backend.web.dto.EmergenciaNuevaDto;

/** Lógica operativa de despacho: flota, emergencias y asignación con SLA. */
@Service
public class DespachoService {

    private final JdbcTemplate jdbc;

    public DespachoService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** Unidades DISPONIBLES más cercanas a un punto (KNN geography). */
    public List<AmbulanciaCercanaDto> ambulanciasCercanas(
            double lat, double lon, double radioKm, String tipoMin, int limite) {
        String sql = """
                SELECT id, placa, tipo, organizacion_id,
                       distancia_km,
                       EXTRACT(EPOCH FROM ultima_posicion) * 1000 AS ultima_posicion_ms
                  FROM ambulancia_disponible_cercana(?, ?, ?, ?, ?)
                """;
        return jdbc.query(sql, new AmbulanciaCercanaMapper(),
                lat, lon, radioKm, tipoMin, Math.min(limite, 50));
    }

    /** Reporte de posición GPS desde la app del conductor. */
    @Transactional
    public void reportarPosicion(int ambulanciaId, double lat, double lon, Integer velocidadKmh) {
        jdbc.update("""
                INSERT INTO posiciones_ambulancia (ambulancia_id, latitud, longitud, velocidad_kmh)
                VALUES (?, ?, ?, ?)
                """, ps -> {
            ps.setInt(1, ambulanciaId);
            ps.setDouble(2, lat);
            ps.setDouble(3, lon);
            if (velocidadKmh != null) {
                ps.setInt(4, velocidadKmh);
            } else {
                ps.setNull(4, Types.SMALLINT);
            }
        });
        jdbc.update("""
                UPDATE ambulancias
                   SET latitud = ?, longitud = ?,
                       geom = ST_SetSRID(ST_MakePoint(?, ?), 4326),
                       ultima_posicion = NOW()
                 WHERE id = ?
                """, lat, lon, lon, lat, ambulanciaId);
    }

    /** Crea una emergencia con triaje y código único por fecha. */
    @Transactional
    public EmergenciaDto crearEmergencia(EmergenciaNuevaDto dto) {
        String codigo = "EMG-" + java.time.LocalDate.now().toString().replace("-", "")
                + "-" + System.currentTimeMillis() % 100000;
        Long id = jdbc.queryForObject("""
                INSERT INTO emergencias (codigo, canal, ciudadano_telefono,
                                         direccion_referencia, latitud, longitud,
                                         triaje, descripcion, especialidad_requerida)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """, Long.class,
                codigo, dto.canal(), dto.telefonoCiudadano(), dto.direccionReferencia(),
                dto.latitud(), dto.longitud(), dto.triaje(), dto.descripcion(),
                dto.especialidadRequerida());
        return detalleEmergencia(id);
    }

    /** Cola operativa: emergencias activas ordenadas por gravedad y antigüedad. */
    public List<EmergenciaDto> emergenciasActivas() {
        String sql = """
                SELECT id, codigo, canal, estado, triaje, latitud, longitud,
                       direccion_referencia, hospital_destino_id,
                       EXTRACT(EPOCH FROM creada_en) * 1000          AS creada_ms,
                       EXTRACT(EPOCH FROM asignada_en) * 1000        AS asignada_ms,
                       EXTRACT(EPOCH FROM llegada_escena_en) * 1000  AS escena_ms
                  FROM emergencias
                 WHERE estado IN ('RECIBIDA', 'ASIGNADA', 'EN_ATENCION', 'EN_TRASLADO')
                 ORDER BY CASE triaje WHEN 'C1' THEN 1 WHEN 'C2' THEN 2
                                      WHEN 'C3' THEN 3 ELSE 4 END ASC,
                          creada_en ASC
                """;
        return jdbc.query(sql, new EmergenciaMapper());
    }

    /** Asigna una unidad a una emergencia: registra distancia real y sella SLA. */
    @Transactional
    public AsignacionDto asignar(Long emergenciaId, int ambulanciaId) {
        BigDecimal distanciaKm = jdbc.queryForObject("""
                SELECT ROUND((ST_Distance(e.geom::geography, a.geom::geography) / 1000.0)::numeric, 2)
                  FROM emergencias e, ambulancias a
                 WHERE e.id = ? AND a.id = ?
                   AND e.geom IS NOT NULL AND a.geom IS NOT NULL
                """, BigDecimal.class, emergenciaId, ambulanciaId);

        Long asignacionId = jdbc.queryForObject("""
                INSERT INTO asignaciones (emergencia_id, ambulancia_id, estado, distancia_km)
                VALUES (?, ?, 'ACEPTADA', ?)
                RETURNING id
                """, Long.class, emergenciaId, ambulanciaId, distanciaKm);

        jdbc.update("UPDATE emergencias SET estado = 'ASIGNADA', asignada_en = NOW() WHERE id = ?",
                emergenciaId);
        jdbc.update("UPDATE ambulancias SET estado = 'EN_CAMINO' WHERE id = ?", ambulanciaId);

        return new AsignacionDto(asignacionId, emergenciaId, ambulanciaId, "ACEPTADA",
                distanciaKm, null);
    }

    private EmergenciaDto detalleEmergencia(Long id) {
        String sql = """
                SELECT id, codigo, canal, estado, triaje, latitud, longitud,
                       direccion_referencia, hospital_destino_id,
                       EXTRACT(EPOCH FROM creada_en) * 1000          AS creada_ms,
                       EXTRACT(EPOCH FROM asignada_en) * 1000        AS asignada_ms,
                       EXTRACT(EPOCH FROM llegada_escena_en) * 1000  AS escena_ms
                  FROM emergencias WHERE id = ?
                """;
        return jdbc.query(sql, new EmergenciaMapper(), id).stream().findFirst().orElse(null);
    }

    private static Long epochMs(ResultSet rs, String columna) throws SQLException {
        java.math.BigDecimal v = rs.getBigDecimal(columna);
        return rs.wasNull() || v == null ? null : v.longValue();
    }

    private static final class AmbulanciaCercanaMapper implements RowMapper<AmbulanciaCercanaDto> {
        @Override
        public AmbulanciaCercanaDto mapRow(ResultSet rs, int i) throws SQLException {
            return new AmbulanciaCercanaDto(
                    rs.getInt("id"), rs.getString("placa"), rs.getString("tipo"),
                    rs.getInt("organizacion_id"), rs.getDouble("distancia_km"),
                    epochMs(rs, "ultima_posicion_ms"));
        }
    }

    private static final class EmergenciaMapper implements RowMapper<EmergenciaDto> {
        @Override
        public EmergenciaDto mapRow(ResultSet rs, int i) throws SQLException {
            Integer hosp = rs.getObject("hospital_destino_id", Integer.class);
            return new EmergenciaDto(
                    rs.getLong("id"), rs.getString("codigo"), rs.getString("canal"),
                    rs.getString("estado"), rs.getString("triaje"),
                    rs.getDouble("latitud"), rs.getDouble("longitud"),
                    rs.getString("direccion_referencia"), hosp,
                    epochMs(rs, "creada_ms"),
                    epochMs(rs, "asignada_ms"),
                    epochMs(rs, "escena_ms"));
        }
    }
}
