# ============================================================================
# valhalla-build.ps1 — Construye los tiles del grafo Perú para Valhalla (F-C2)
# ----------------------------------------------------------------------------
# Requisitos: Docker corriendo y data/osm/peru-latest.osm.pbf descargado.
#   https://download.geofabrik.de/south-america/peru-latest.osm.pbf
#
# Uso:
#   powershell -File scripts\valhalla-build.ps1          # build completo
#
# Salida: valhalla_data/ (config.json + tiles/) que sirve docker compose up valhalla
# NOTA: consume ~4GB RAM y 20-60 min según CPU. Idempotente: sobreescribe tiles.
# ============================================================================

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$pbf  = Join-Path $root "data\osm\peru-latest.osm.pbf"
$out  = Join-Path $root "valhalla_data"

if (-not (Test-Path $pbf)) {
    Write-Error "No existe $pbf. Descarga primero el PBF de Geofabrik."
}
New-Item -ItemType Directory -Force $out | Out-Null

$img = "ghcr.io/valhalla/valhalla:latest"
docker pull $img

# 1) config.json con concurrencia limitada (VM Docker tiene ~6GB RAM)
#    OJO: capturar salida y escribirla en ASCII (el '>' de PS5.1 produce UTF-16 que Valhalla no lee)
Write-Host "== Generando config.json =="
$cfg = docker run --rm -v "${out}:/data/valhalla" $img `
    valhalla_build_config --mjolnir-tile-dir /data/valhalla/tiles `
                          --mjolnir-concurrency 4
if ($LASTEXITCODE -ne 0 -or -not $cfg) { Write-Error "valhalla_build_config falló" }
[System.IO.File]::WriteAllLines("$out\config.json", $cfg,
    (New-Object System.Text.ASCIIEncoding))

# 2) Construcción de tiles (paso largo)
Write-Host "== Construyendo tiles (20-60 min) =="
Copy-Item $pbf "$out\peru.pbf" -Force
docker run --rm -v "${out}:/data/valhalla" --memory 4g $img `
    valhalla_build_tiles -c /data/valhalla/config.json /data/valhalla/peru.pbf
if ($LASTEXITCODE -ne 0) { Write-Error "valhalla_build_tiles falló" }

# 3) Extracto de tráfico (necesario para arrancar el servicio)
Write-Host "== Generando traffic extract =="
docker run --rm -v "${out}:/data/valhalla" $img `
    valhalla_build_extract -c /data/valhalla/config.json -v
if ($LASTEXITCODE -ne 0) { Write-Error "valhalla_build_extract falló" }

Remove-Item "$out\peru.pbf" -ErrorAction SilentlyContinue
Write-Host "== Tiles listos. Levanta con: docker compose up -d valhalla =="
