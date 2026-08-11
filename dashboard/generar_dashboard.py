# ============================================================================
# SALUD CERCA - dashboard/generar_dashboard.py
# ----------------------------------------------------------------------------
# Genera un dashboard HTML autónomo (Leaflet + Chart.js desde CDN) leyendo la
# capa Gold de PostgreSQL + PostGIS + pgvector vía docker compose exec.
#
#   Uso:
#     python dashboard/generar_dashboard.py   # -> dashboard/index.html
#     start dashboard/index.html              # abre en el navegador
#
# Sin dependencias externas (solo stdlib). Requiere el contenedor db arriba.
# ============================================================================

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "index.html"

DB_USER = "saludcerca"
DB_NAME = "saludcerca"


def psql(query: str) -> list[list[str]]:
    """Ejecuta un SELECT y devuelve filas como listas de strings."""
    cmd = [
        "docker", "compose", "exec", "-T", "db",
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-tA", "-F", "|", "-c", query,
    ]
    proc = subprocess.run(cmd, capture_output=True, cwd=ROOT)
    if proc.returncode != 0:
        raise RuntimeError(f"psql falló: {proc.stderr.decode('utf-8', 'replace')}")
    out = proc.stdout.decode("utf-8", "replace")
    return [row.split("|") for row in out.strip().splitlines() if row.strip()]


def num(v: str) -> float | int | None:
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Consultas de la capa Gold
# ---------------------------------------------------------------------------

def cargar_datos() -> dict:
    kpi_row = psql(
        "SELECT "
        " (SELECT count(*) FROM ipress),"
        " (SELECT count(*) FROM ipress WHERE estado_operativo='ACTIVO'),"
        " (SELECT count(*) FROM atenciones_his),"
        " (SELECT COALESCE(SUM(num_atenciones),0) FROM fact_atenciones_medicas),"
        " (SELECT count(*) FROM fact_atenciones_medicas),"
        " (SELECT count(*) FROM vw_brechas_cobertura WHERE brecha='DESIERTO_SANITARIO'),"
        " (SELECT count(*) FROM vw_brechas_cobertura WHERE brecha='DEFICIT_MODERADO')"
    )[0]
    kpis = {
        "total_ipress": num(kpi_row[0]),
        "activas": num(kpi_row[1]),
        "atenciones": num(kpi_row[2]),
        "atenciones_fact": num(kpi_row[3]),
        "fact_filas": num(kpi_row[4]),
        "desiertos": num(kpi_row[5]),
        "deficit": num(kpi_row[6]),
    }

    cobertura = [
        {
            "departamento": r[0],
            "total_ipress": num(r[1]),
            "activas": num(r[2]),
            "nivel_primario": num(r[3]),
            "nivel_secundario": num(r[4]),
            "nivel_terciario": num(r[5]),
            "saturacion": num(r[6]),
            "indice_cobertura": num(r[7]),
            "lat": num(r[8]),
            "lon": num(r[9]),
        }
        for r in psql(
            "SELECT departamento, total_ipress, ipress_activas, nivel_primario,"
            " nivel_secundario, nivel_terciario, saturacion_promedio, indice_cobertura,"
            " ST_Y(geom_centroide), ST_X(geom_centroide)"
            " FROM vw_cobertura_regional ORDER BY total_ipress DESC"
        )
    ]

    # Serie mensual nacional (todas las atenciones agregadas por mes)
    serie = [
        {"mes": r[0], "atenciones": num(r[1]), "emergencias": num(r[2])}
        for r in psql(
            "SELECT to_char(mes, 'YYYY-MM'), SUM(total_atenciones), SUM(total_emergencias)"
            " FROM vw_atenciones_mensual GROUP BY 1 ORDER BY 1"
        )
    ]

    # Top 10 IPRESS por saturación promedio (todo el periodo cargado).
    # NOTA: vw_saturacion_ipress usa una ventana de 90 días; para un batch
    # histórico se consulta el fact directamente.
    saturadas = [
        {"nombre": r[0], "saturacion": num(r[1]), "atenciones": num(r[2])}
        for r in psql(
            "SELECT d.nombre, ROUND(AVG(f.tasa_saturacion), 2), SUM(f.num_atenciones)"
            " FROM fact_atenciones_medicas f"
            " JOIN dim_ipress d ON d.ipress_key = f.ipress_key"
            " GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
        )
    ]

    # Distribución de brechas por departamento
    brechas = [
        {"departamento": r[0], "brecha": r[1], "n": num(r[2])}
        for r in psql(
            "SELECT departamento, brecha, count(*) FROM vw_brechas_cobertura"
            " GROUP BY 1, 2 ORDER BY 1"
        )
    ]

    # Top 10 distritos con peor cobertura (mayor distancia a IPRESS activa)
    top_brechas = [
        {"distrito": r[0], "km": num(r[1]), "brecha": r[2]}
        for r in psql(
            "SELECT departamento || ' / ' || provincia || ' / ' || distrito,"
            " km_ipress_mas_cercana, brecha"
            " FROM vw_brechas_cobertura"
            " WHERE km_ipress_mas_cercana IS NOT NULL"
            " ORDER BY km_ipress_mas_cercana DESC LIMIT 10"
        )
    ]

    return {
        "kpis": kpis,
        "cobertura": cobertura,
        "serie": serie,
        "saturadas": saturadas,
        "brechas": brechas,
        "top_brechas": top_brechas,
        "generado": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ---------------------------------------------------------------------------
# Plantilla HTML
# ---------------------------------------------------------------------------

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SALUD CERCA - Dashboard geo-analítico</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<style>
  :root { --sc:#0d6e8e; --sc2:#18a0b0; }
  body { background:#f4f7f9; font-family:Segoe UI, Roboto, sans-serif; }
  header { background:linear-gradient(90deg, var(--sc), var(--sc2)); color:#fff; padding:1.2rem 1.5rem; }
  header h1 { margin:0; font-weight:600; font-size:1.4rem; }
  header small { opacity:.9; }
  .kpi { background:#fff; border-radius:12px; padding:1rem 1.2rem; box-shadow:0 1px 4px rgba(0,0,0,.08); }
  .kpi .valor { font-size:1.7rem; font-weight:700; color:var(--sc); }
  .kpi .etiqueta { font-size:.78rem; color:#6c757d; text-transform:uppercase; letter-spacing:.4px; }
  .panel { background:#fff; border-radius:12px; box-shadow:0 1px 4px rgba(0,0,0,.08); padding:1rem; }
  .panel h2 { font-size:1rem; font-weight:600; color:#333; margin-bottom:.8rem; }
  #mapa { height:440px; border-radius:12px; z-index:1; }
  table { font-size:.85rem; }
  .footer { color:#8a94a6; font-size:.8rem; text-align:center; padding:1rem 0 2rem; }
</style>
</head>
<body>

<header>
  <h1>SALUD CERCA &mdash; Dashboard geo-anal\u00edtico de cobertura sanitaria</h1>
  <small>Lakehouse Medall\u00f3n &middot; PySpark &middot; PostgreSQL + PostGIS + pgvector &middot; generado: __GENERADO__</small>
</header>

<main class="container-fluid px-4 py-4">

  <!-- KPIs -->
  <div class="row g-3 mb-4">
    <div class="col-6 col-md-3"><div class="kpi"><div class="valor">__KPI_IPRESS__</div><div class="etiqueta">Establecimientos</div></div></div>
    <div class="col-6 col-md-3"><div class="kpi"><div class="valor">__KPI_ACTIVAS__</div><div class="etiqueta">IPRESS activas</div></div></div>
    <div class="col-6 col-md-3"><div class="kpi"><div class="valor">__KPI_ATENCIONES__</div><div class="etiqueta">Atenciones HIS 2024</div></div></div>
    <div class="col-6 col-md-3"><div class="kpi"><div class="valor">__KPI_DESIERTOS__</div><div class="etiqueta">Desiertos sanitarios</div></div></div>
  </div>

  <div class="row g-3">
    <!-- Mapa -->
    <div class="col-lg-8">
      <div class="panel"><h2>Cobertura por departamento (radio = IPRESS, color = saturaci\u00f3n promedio)</h2>
        <div id="mapa"></div>
      </div>
    </div>
    <!-- Serie mensual -->
    <div class="col-lg-4">
      <div class="panel"><h2>Tendencia mensual de atenciones</h2>
        <canvas id="graficaSerie"></canvas>
      </div>
      <div class="panel mt-3"><h2>Top 10 IPRESS saturadas</h2>
        <table class="table table-sm"><thead><tr><th>Establecimiento</th><th class="text-end">Saturaci\u00f3n %</th></tr></thead>
        <tbody id="tablaSaturadas"></tbody></table>
      </div>
    </div>
  </div>

  <div class="row g-3 mt-0">
    <div class="col-lg-7">
      <div class="panel"><h2>IPRESS por departamento</h2><canvas id="graficaCobertura" height="120"></canvas></div>
    </div>
    <div class="col-lg-5">
      <div class="panel"><h2>Peores brechas de cobertura (km a la IPRESS activa m\u00e1s cercana)</h2>
        <table class="table table-sm"><thead><tr><th>Distrito</th><th class="text-end">Km</th><th>Brecha</th></tr></thead>
        <tbody id="tablaBrechas"></tbody></table>
      </div>
    </div>
  </div>

  <div class="footer">Datos sint\u00e9ticos 2024 &middot; RENIPRESS + HIS-MINSA &middot; modelos: Star Schema / Geo-anal\u00edtica / pgvector</div>
</main>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<script>
const DATOS = __DATOS__;

// ---------- Mapa ----------
const mapa = L.map('mapa');
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap &copy; CARTO'
}).addTo(mapa);

const marcadores = [];
const colorSat = (s) => {
  if (s == null) return '#9aa4af';
  if (s < 33) return '#2e9e6b';
  if (s < 66) return '#e6a23c';
  return '#d64545';
};
DATOS.cobertura.forEach(d => {
  if (d.lat == null || d.lon == null) return;
  const m = L.circleMarker([d.lat, d.lon], {
    radius: Math.max(6, Math.sqrt(d.total_ipress || 0) * 2.2),
    color: '#fff', weight: 1, fillColor: colorSat(d.saturacion), fillOpacity: .85
  }).addTo(mapa);
  m.bindTooltip(
    `<b>${d.departamento}</b><br>` +
    `IPRESS: ${d.total_ipress} (${d.activas} activas)<br>` +
    `Saturaci\u00f3n prom: ${d.saturacion ?? 'n/d'}%<br>` +
    `\u00cdndice cobertura: ${d.indice_cobertura ?? 'n/d'}/10k hab`
  );
  marcadores.push(m);
});
if (marcadores.length) mapa.fitBounds(L.featureGroup(marcadores).getBounds().pad(0.1));
else mapa.setView([-9.19, -75.01], 5);

// ---------- Serie mensual ----------
new Chart(document.getElementById('graficaSerie'), {
  type: 'line',
  data: {
    labels: DATOS.serie.map(s => s.mes),
    datasets: [
      { label: 'Atenciones', data: DATOS.serie.map(s => s.atenciones), borderColor: '#0d6e8e', tension: .3, fill: false },
      { label: 'Emergencias', data: DATOS.serie.map(s => s.emergencias), borderColor: '#d64545', tension: .3, fill: false }
    ]
  },
  options: { responsive: true, plugins: { legend: { position: 'bottom' } }, scales: { y: { beginAtZero: true } } }
});

// ---------- IPRESS por departamento ----------
const topDept = DATOS.cobertura.slice(0, 12).reverse();
new Chart(document.getElementById('graficaCobertura'), {
  type: 'bar',
  data: {
    labels: topDept.map(d => d.departamento),
    datasets: [{
      label: 'IPRESS totales', data: topDept.map(d => d.total_ipress), backgroundColor: '#18a0b0'
    }, {
      label: 'Activas', data: topDept.map(d => d.activas), backgroundColor: '#2e9e6b'
    }]
  },
  options: { indexAxis: 'y', responsive: true, plugins: { legend: { position: 'bottom' } } }
});

// ---------- Tabla de IPRESS saturadas ----------
document.getElementById('tablaSaturadas').innerHTML = DATOS.saturadas.map(d =>
  `<tr><td>${d.nombre}</td><td class="text-end"><b>${d.saturacion}</b></td></tr>`
).join('') || '<tr><td colspan="2">Sin datos</td></tr>';

// ---------- Tabla de brechas ----------
document.getElementById('tablaBrechas').innerHTML = DATOS.top_brechas.map(d =>
  `<tr><td>${d.distrito}</td><td class="text-end"><b>${d.km}</b> km</td><td>${d.brecha}</td></tr>`
).join('') || '<tr><td colspan="3">Sin datos</td></tr>';
</script>
</body>
</html>
"""


def render_html(datos: dict) -> str:
    k = datos["kpis"]
    html = HTML
    html = html.replace("__GENERADO__", datos["generado"])
    html = html.replace("__KPI_IPRESS__", f"{k['total_ipress']:,}".replace(",", "."))
    html = html.replace("__KPI_ACTIVAS__", f"{k['activas']:,}".replace(",", "."))
    html = html.replace("__KPI_ATENCIONES__", f"{k['atenciones']:,}".replace(",", "."))
    html = html.replace("__KPI_DESIERTOS__", f"{k['desiertos']:,}".replace(",", "."))
    html = html.replace("__DATOS__", json.dumps(datos, ensure_ascii=False))
    return html


def main() -> None:
    print("Consultando capa Gold ...")
    datos = cargar_datos()
    print(f"  departamentos : {len(datos['cobertura'])}")
    print(f"  serie mensual  : {len(datos['serie'])} meses")
    print(f"  IPRESS top saturadas : {len(datos['saturadas'])}")
    OUT.write_text(render_html(datos), encoding="utf-8")
    print(f"Dashboard generado: {OUT}")


if __name__ == "__main__":
    main()
