package pe.saludcerca.backend.web.dto;

/** Reporte enviado por un contribuidor desde la app/campo. */
public record ReporteContribucionDto(
        Long tareaId,
        Integer contribuidorId,
        Integer ipressId,
        String campoReportado,
        String valorNuevo,
        String evidenciaUrl,
        Double latitudReporte,
        Double longitudReporte) {
}
