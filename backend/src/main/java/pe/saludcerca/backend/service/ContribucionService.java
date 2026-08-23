package pe.saludcerca.backend.service;

import java.util.List;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import pe.saludcerca.backend.web.dto.ReporteContribucionDto;
import pe.saludcerca.backend.web.dto.TareaVerificacionDto;

/** Red humana de verificación: cola geo-asignada y recepción de reportes. */
@Service
public class ContribucionService {

    private final JdbcTemplate jdbc;

    public ContribucionService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** Tareas PENDIENTES cercanas al contribuidor, por prioridad y distancia (KNN). */
    public List<TareaVerificacionDto> tareasCercanas(double lat, double lon, double radioKm, int limite) {
        String sql = """
                SELECT t.id, t.ipress_id, i.nombre, t.tipo, t.prioridad,
                       t.latitud, t.longitud, t.recompensa,
                       ROUND((ST_Distance(t.geom::geography,
                                         ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography)
                              / 1000.0)::numeric, 2) AS distancia_km
                  FROM tareas_verificacion t
                  JOIN ipress i ON i.id = t.ipress_id
                 WHERE t.estado IN ('PENDIENTE', 'ASIGNADA')
                   AND ST_DWithin(t.geom::geography,
                                  ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography, ? * 1000)
                 ORDER BY t.prioridad DESC, distancia_km ASC
                 LIMIT ?
                """;
        return jdbc.query(sql, (rs, n) -> new TareaVerificacionDto(
                rs.getLong("id"),
                rs.getInt("ipress_id"),
                rs.getString("nombre"),
                rs.getString("tipo"),
                rs.getInt("prioridad"),
                rs.getDouble("latitud"),
                rs.getDouble("longitud"),
                rs.getDouble("distancia_km"),
                rs.getBigDecimal("recompensa")),
                lon, lat, lon, lat, radioKm, Math.min(limite, 50));
    }

    /**
     * Recibe un reporte de contribuidor.
     * Datos triviales (HORARIO/TELEFONO) quedan PENDIENTE para auto-validación batch;
     * datos críticos pasan por validar_reporte() del validador humano.
     */
    @Transactional
    public Long recibirReporte(ReporteContribucionDto dto) {
        if (dto.contribuidorId() == null) {
            throw new IllegalArgumentException("Se requiere contribuidor autenticado");
        }
        if (dto.ipressId() == null || dto.campoReportado() == null || dto.valorNuevo() == null) {
            throw new IllegalArgumentException("ipressId, campoReportado y valorNuevo son obligatorios");
        }
        if (dto.latitudReporte() != null && dto.longitudReporte() != null) {
            Boolean enGeocerca = jdbc.queryForObject("""
                    SELECT ST_DWithin(ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography,
                                      i.geom::geography, 500)
                      FROM ipress i WHERE i.id = ?
                    """, Boolean.class, dto.longitudReporte(), dto.latitudReporte(), dto.ipressId());
            if (!Boolean.TRUE.equals(enGeocerca)) {
                throw new IllegalArgumentException("El reporte no está dentro de la geocerca de la IPRESS");
            }
        }
        return jdbc.queryForObject("""
                INSERT INTO reportes_contribucion
                    (tarea_id, contribuidor_id, ipress_id, campo_reportado,
                     valor_nuevo, evidencia_url, latitud_reporte, longitud_reporte)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """, Long.class,
                dto.tareaId(), dto.contribuidorId(), dto.ipressId(),
                dto.campoReportado(), dto.valorNuevo(), dto.evidenciaUrl(),
                dto.latitudReporte(), dto.longitudReporte());
    }
}
