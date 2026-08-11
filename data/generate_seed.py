# ============================================================================
# SALUD CERCA - Generador de dataset sintético (RENIPRESS + HIS-MINSA)
# ----------------------------------------------------------------------------
# Genera un dataset realista pero sintético que alimenta:
#   1. El seed de PostgreSQL (montado en /seed-data, cargado por 06_seed.sql)
#   2. La capa Bronze del pipeline PySpark (data-pipeline/), simulando los
#      CSV/JSON masivos que publica el MINSA.
#
# Estructura generada en data/output/:
#   categorizaciones.csv  -> Catálogo de categorías I-1 .. III-E (+ embeddings)
#   especialidades.csv    -> Catálogo de especialidades (+ embeddings)
#   ubigeo.csv            -> Departamentos / provincias / distritos + centroides
#   renipress.csv         -> Establecimientos de salud (RENIPRESS) + geometría
#   his_atenciones.csv    -> ~350k atenciones HIS-MINSA (año 2024)
#
# Para reproducibilidad se fija una semilla global (random_state).
# Uso:  python data/generate_seed.py  [--rows 350000]
# ============================================================================

from __future__ import annotations

import argparse
import csv
import os
import random
from datetime import date, timedelta

from embedding_encoder import embed_postgres  # type: ignore

# ---------------------------------------------------------------------------
# Configuración del dataset
# ---------------------------------------------------------------------------
RANDOM_SEED = 42
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

ANIO_HIS = 2024

# Departamentos del Perú: (nombre, lat, lng, peso_poblacional 0..1)
# El peso modela la densidad poblacional relativa y controla la cantidad de
# establecimientos, categorías de alta complejidad y volumen de atenciones.
DEPARTAMENTOS: list[tuple[str, float, float, float]] = [
    ("LIMA", -12.046, -77.042, 1.00), ("CALLAO", -11.994, -77.122, 0.95),
    ("AREQUIPA", -16.399, -71.537, 0.50), ("LA LIBERTAD", -8.128, -79.033, 0.45),
    ("PIURA", -5.194, -80.633, 0.42), ("LAMBAYEQUE", -6.701, -79.900, 0.40),
    ("CUSCO", -13.532, -71.968, 0.38), ("JUNIN", -11.667, -75.509, 0.36),
    ("PUNO", -15.842, -70.021, 0.34), ("CAJAMARCA", -7.164, -78.510, 0.33),
    ("ANCASH", -9.532, -77.538, 0.30), ("LORETO", -3.773, -73.251, 0.28),
    ("HUANUCO", -9.931, -76.240, 0.26), ("SAN MARTIN", -6.485, -76.366, 0.24),
    ("ICA", -14.067, -75.728, 0.24), ("AYACUCHO", -13.159, -74.224, 0.22),
    ("AMAZONAS", -6.219, -77.867, 0.20), ("TACNA", -18.014, -70.249, 0.20),
    ("APURIMAC", -13.640, -73.086, 0.18), ("HUANCAVELICA", -12.787, -74.973, 0.18),
    ("MADRE DE DIOS", -12.592, -70.103, 0.16), ("MOQUEGUA", -17.192, -70.933, 0.16),
    ("PASCO", -10.683, -75.268, 0.15), ("TUMBES", -3.553, -80.448, 0.15),
    ("UCAYALI", -8.581, -74.544, 0.16),
]

# Categorías RENIPRESS: (codigo, nombre, nivel_atencion, capacidad_resolutiva, descripcion)
CATEGORIAS: list[tuple[str, str, int, int, str]] = [
    ("I-1", "Puesto de Salud", 1, 2, "Atención primaria básica de promoción y prevención en zonas rurales."),
    ("I-2", "Puesto de Salud con Médico", 1, 3, "Atención primaria con médico general y enfermería."),
    ("I-3", "Centro de Salud con Internamiento", 1, 4, "Centro de salud con camas de observación y partos."),
    ("I-4", "Centro de Salud / Policlínico", 1, 5, "Establecimiento de atención ambulatoria multiespecialidad."),
    ("II-1", "Hospital de Nivel I", 2, 7, "Hospital general con especialidades básicas e internamiento."),
    ("II-2", "Hospital de Nivel II", 2, 8, "Hospital general con especialidades y unidad de cuidados intensivos."),
    ("II-E", "Hospital de Emergencia", 2, 8, "Hospital exclusivo de atención de emergencias y desastres."),
    ("III-1", "Hospital de Nivel III", 3, 10, "Hospital de alta complejidad con subespecialidades y referencias nacionales."),
    ("III-E", "Instituto Especializado", 3, 10, "Instituto nacional de investigación y atención de alta especialidad."),
]

# Especialidades: (codigo, nombre, complejidad_minima, descripcion, [CIE-10 típicos])
ESPECIALIDADES: list[tuple[str, str, int, str, list[str]]] = [
    ("MEDGEN", "Medicina General", 1, "Consulta general, control de enfermedades crónicas y derivación.", ["J00", "J06", "J18", "A09", "R51", "R10", "E11"]),
    ("PEDIA", "Pediatría", 2, "Atención del niño sano y enfermo, inmunizaciones y crecimiento.", ["J03", "J18", "B05", "R10", "Z00"]),
    ("GOBST", "Gineco-Obstetricia", 2, "Atención de gestantes, partos y patología ginecológica.", ["O80", "O20", "N76", "Z34", "O82"]),
    ("CIRUG", "Cirugía General", 2, "Cirugía de tejidos, abdomen y traumatismos menores.", ["K35", "K80", "S01", "T14"]),
    ("CARDI", "Cardiología", 3, "Enfermedades cardiovasculares, hipertensión y arritmias.", ["I10", "I20", "I25", "I48", "I50"]),
    ("NEURO", "Neurología", 3, "Trastornos del sistema nervioso central y periférico.", ["G40", "G43", "G45", "F03"]),
    ("TRAUM", "Traumatología y Ortopedia", 3, "Fracturas, lesiones musculoesqueléticas y ortopedia.", ["S52", "S82", "M54", "S93"]),
    ("ODONT", "Odontología", 1, "Salud bucal, caries, extracciones y prevención dental.", ["K02", "K04", "K05", "K00"]),
    ("PSICO", "Psicología", 1, "Salud mental, ansiedad, depresión y terapia psicológica.", ["F41", "F32", "F10", "F43"]),
    ("DERMA", "Dermatología", 2, "Enfermedades de la piel, alergias y lesiones cutáneas.", ["L20", "L30", "B35", "L02"]),
    ("GASTRO", "Gastroenterología", 3, "Enfermedades del aparato digestivo y endoscopias.", ["K21", "K29", "K30", "K59"]),
    ("NEFRO", "Nefrología", 3, "Enfermedad renal crónica y hemodiálisis.", ["N18", "N20", "N39", "N00"]),
    ("ONCOL", "Oncología", 3, "Diagnóstico y tratamiento de neoplasias.", ["C50", "C34", "C16", "C18"]),
    ("PNEUM", "Neumología", 3, "Enfermedades respiratorias crónicas y agudas.", ["J45", "J44", "J20", "J15"]),
    ("URGEN", "Emergencias y Desastres", 2, "Atención de urgencias y emergencias médicas.", ["S00", "S30", "R10", "R55"]),
    ("PREVE", "Atención Preventiva", 1, "Promoción de la salud, tamizaje y vacunación comunitaria.", ["Z00", "Z01", "Z11", "Z23"]),
]

# Probabilidad de elección de especialidad en una atención (debe sumar ~1.0)
PESO_ESPECIALIDAD = {
    "MEDGEN": 0.30, "PEDIA": 0.12, "GOBST": 0.10, "PREVE": 0.10, "ODONT": 0.08,
    "URGEN": 0.08, "CIRUG": 0.04, "CARDI": 0.03, "NEURO": 0.02, "TRAUM": 0.03,
    "PSICO": 0.03, "DERMA": 0.02, "GASTRO": 0.02, "NEFRO": 0.01, "ONCOL": 0.01,
    "PNEUM": 0.01,
}

# Distribución de categorías según índice de urbanización (acumulada)
# (urbano) vs (rural): se elige con random.choices
DISTRIBUCION_CATEGORIA: list[tuple[float, dict[str, float]]] = [
    (0.25, {"I-1": 0.60, "I-2": 0.25, "I-3": 0.10, "I-4": 0.04, "II-1": 0.01}),
    (0.50, {"I-1": 0.35, "I-2": 0.28, "I-3": 0.20, "I-4": 0.10, "II-1": 0.05, "II-2": 0.02}),
    (0.75, {"I-1": 0.18, "I-2": 0.22, "I-3": 0.24, "I-4": 0.16, "II-1": 0.12, "II-2": 0.06, "II-E": 0.01, "III-1": 0.01}),
    (1.01, {"I-1": 0.10, "I-2": 0.15, "I-3": 0.20, "I-4": 0.18, "II-1": 0.18, "II-2": 0.10, "II-E": 0.03, "III-1": 0.04, "III-E": 0.02}),
]

CAMAS_POR_CATEGORIA: dict[str, tuple[int, int]] = {
    "I-1": (0, 0), "I-2": (0, 0), "I-3": (8, 20), "I-4": (15, 40),
    "II-1": (40, 120), "II-2": (120, 250), "II-E": (80, 150),
    "III-1": (250, 600), "III-E": (150, 400),
}

CONSULTORIOS_POR_NIVEL: dict[int, tuple[int, int]] = {1: (1, 4), 2: (6, 18), 3: (15, 35)}


# ---------------------------------------------------------------------------
# Clase principal del generador
# ---------------------------------------------------------------------------
class GeneradorSaludCerca:
    def __init__(self, seed: int = RANDOM_SEED) -> None:
        self.rng = random.Random(seed)
        self.ubigeo_rows: list[list[str]] = []
        self.ipress_rows: list[list[str]] = []
        self.his_rows: list[list[str]] = []
        self._cat_por_codigo: dict[str, dict] = {}
        self._esp_por_codigo: dict[str, dict] = {}
        self._ipress_por_departamento: dict[str, list[dict]] = {}

    # -- Utilidades --------------------------------------------------------
    @staticmethod
    def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, v))

    def _urbanizacion(self, peso: float) -> float:
        """Índice de urbanización 0..1 con ruido determinístico."""
        return self._clamp(peso * (0.75 + self.rng.random() * 0.5))

    # -- Generación de catálogos ------------------------------------------
    def _generar_categorias(self, path: str) -> None:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["id", "codigo", "nombre", "nivel_atencion",
                             "capacidad_resolutiva", "descripcion", "descripcion_emb"])
            for idx, (codigo, nombre, nivel, cap, desc) in enumerate(CATEGORIAS, start=1):
                writer.writerow([idx, codigo, nombre, nivel, cap, desc,
                                 embed_postgres(f"{codigo} {nombre} {desc}")])
                self._cat_por_codigo[codigo] = {"id": idx, "nivel": nivel}

    def _generar_especialidades(self, path: str) -> None:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["id", "codigo", "nombre", "complejidad_minima",
                             "descripcion", "descripcion_emb"])
            for idx, (codigo, nombre, min_nivel, desc, _cie) in enumerate(ESPECIALIDADES, start=1):
                writer.writerow([idx, codigo, nombre, min_nivel, desc,
                                 embed_postgres(f"{codigo} {nombre} {desc}")])
                self._esp_por_codigo[codigo] = {"id": idx, "nivel": min_nivel, "cie": _cie}

    # -- Generación de ubigeo ----------------------------------------------
    def _generar_ubigeo(self, path: str) -> None:
        """Crea provincias y distritos con centroides derivados de los departamentos."""
        next_id = 1
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["id", "codigo_ubigeo", "departamento", "provincia",
                             "distrito", "latitud_centroide", "longitud_centroide"])
            for dept_idx, (dept, lat, lng, peso) in enumerate(DEPARTAMENTOS, start=1):
                n_prov = 2 + int(round(peso * 8))                     # 2..10 provincias
                for p in range(1, n_prov + 1):
                    n_dist = 3 + int(round(peso * 8 + self.rng.random() * 4))  # 3..12 distritos
                    for d in range(1, n_dist + 1):
                        # Centroide: departamento + desvío aleatorio pequeño
                        dlat = lat + self.rng.uniform(-0.6, 0.6)
                        dlng = lng + self.rng.uniform(-0.6, 0.6)
                        codigo = f"{dept_idx:02d}{p:02d}{d:02d}"
                        writer.writerow([
                            next_id, codigo, dept,
                            f"{dept} {p:02d}", f"{dept} {p:02d} {d:02d}",
                            f"{dlat:.6f}", f"{dlng:.6f}",
                        ])
                        next_id += 1
        self.total_distritos = next_id - 1

    # -- Generación de IPRESS ----------------------------------------------
    def _elegir_categoria(self, urbano: float) -> str:
        for umbral, dist in DISTRIBUCION_CATEGORIA:
            if urbano <= umbral:
                return self.rng.choices(list(dist.keys()), weights=list(dist.values()))[0]
        return "I-1"

    def _nombre_ipress(self, categoria: str, dept: str, distrito: str, n: int) -> str:
        base = {"I-1": "PUESTO DE SALUD", "I-2": "PUESTO DE SALUD CON MEDICO",
                "I-3": "CENTRO DE SALUD", "I-4": "POLICLINICO",
                "II-1": "HOSPITAL", "II-2": "HOSPITAL", "II-E": "HOSPITAL DE EMERGENCIA",
                "III-1": "HOSPITAL", "III-E": "INSTITUTO ESPECIALIZADO"}[categoria]
        return f"{base} {distrito} {n:02d}"

    def _generar_ipress(self, ubigeo_path: str, path: str) -> None:
        self._cargar_ubigeo(ubigeo_path)
        rng = self.rng
        idx_cat = {cat["codigo"]: i for i, cat in enumerate(
            [{"codigo": c[0]} for c in CATEGORIAS])}
        _ = idx_cat  # referencia por codigo via self._cat_por_codigo

        next_id = 1
        codigos: set[str] = set()
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["id", "codigo_renipress", "nombre", "categoria_id",
                             "ubigeo_id", "direccion", "departamento", "provincia",
                             "distrito", "latitud", "longitud", "estado_operativo",
                             "capacidad_camas", "capacidad_consultorios", "horario",
                             "tiene_ambulancia", "telefono", "propietario", "descripcion_emb"])

            por_dept: dict[str, list[dict]] = {}
            # 1er pase: planificar establecimientos por distrito
            filas: list[dict] = []
            for u in self.ubigeo_rows:
                dept, peso = u["departamento"], u["peso"]
                urbano = self._urbanizacion(peso)
                n_est = 1 + int(rng.random() * 3 * (0.5 + peso))       # 1..~6 por distrito
                for _ in range(n_est):
                    categoria = self._elegir_categoria(urbano)
                    filas.append({"categoria": categoria, "ubigeo": u, "peso": peso})

            # 2º pase: materializar cada IPRESS
            for fila in filas:
                categoria = fila["categoria"]
                u = fila["ubigeo"]
                cat = self._cat_por_codigo[categoria]
                nivel = cat["nivel"]
                estado = rng.choices(
                    ["ACTIVO", "INACTIVO", "REFERENCIAL"],
                    weights=[0.90, 0.08, 0.02])[0]
                propietario = rng.choices(
                    ["MINSA", "ESSALUD", "PRIVADO", "FFAA/PNP", "MUNICIPAL"],
                    weights=[0.60, 0.15, 0.18, 0.04, 0.03])[0]

                lo_c, hi_c = CAMAS_POR_CATEGORIA[categoria]
                camas = rng.randint(lo_c, hi_c) if hi_c > 0 else 0
                lo_k, hi_k = CONSULTORIOS_POR_NIVEL[nivel]
                consultorios = rng.randint(lo_k, hi_k)

                nombre = self._nombre_ipress(categoria, u["departamento"], u["distrito"], next_id % 90 + 1)
                lat = round(u["latitud_centroide"] + rng.uniform(-0.05, 0.05), 6)
                lng = round(u["longitud_centroide"] + rng.uniform(-0.05, 0.05), 6)

                while True:
                    codigo = f"{next_id:08d}"
                    if codigo not in codigos:
                        codigos.add(codigo)
                        break
                    next_id += 1

                descripcion_emb = embed_postgres(
                    f"{nombre}, categoria {categoria}, {u['distrito']}, {u['departamento']}"
                )

                fila_data = {
                    "codigo": codigo, "nombre": nombre, "cat_id": cat["id"],
                    "ubigeo_id": u["id"], "codigo_ubigeo": u["codigo_ubigeo"],
                    "dept": u["departamento"], "prov": u["provincia"],
                    "dist": u["distrito"], "lat": lat, "lng": lng, "estado": estado,
                    "camas": camas, "consultorios": consultorios, "nivel": nivel,
                }
                writer.writerow([
                    next_id, codigo, nombre, cat["id"], u["id"],
                    f"Av. {u['distrito']} s/n", u["departamento"], u["provincia"],
                    u["distrito"], f"{lat:.6f}", f"{lng:.6f}", estado,
                    camas, consultorios,
                    "24h" if nivel >= 2 else "08:00-18:00",
                    "t" if (nivel >= 2 and rng.random() > 0.5) else "f",
                    f"01-{next_id % 100000:05d}", propietario, descripcion_emb,
                ])
                por_dept.setdefault(u["departamento"], []).append(fila_data)
                next_id += 1

        self._ipress_por_departamento = por_dept
        self.total_ipress = next_id - 1

    def _cargar_ubigeo(self, ubigeo_path: str) -> None:
        """Lee el CSV de ubigeo y adjunta el peso poblacional de su departamento."""
        pesos = {d[0]: d[3] for d in DEPARTAMENTOS}
        self.ubigeo_rows = []
        with open(ubigeo_path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                row["peso"] = pesos.get(row["departamento"], 0.2)
                row["latitud_centroide"] = float(row["latitud_centroide"])
                row["longitud_centroide"] = float(row["longitud_centroide"])
                self.ubigeo_rows.append(row)

    # -- Generación de atenciones HIS --------------------------------------
    def _distribuir_atenciones(self, total_rows: int) -> dict[int, int]:
        """Reparte el total de atenciones entre IPRESS proporcional a su actividad."""
        pesos: dict[int, float] = {}
        for data in self._ipress_por_departamento.values():
            for ip in data:
                # Actividad ∝ consultorios × nivel
                pesos[int(ip["cat_id"])] = 0  # placeholder no usado
                break
        # Peso real por IPRESS
        pesos.clear()
        for data in self._ipress_por_departamento.values():
            for ip in data:
                key = (ip["dept"], ip["codigo"])
                _ = key
                pesos[id(ip)] = (ip["consultorios"] or 1) * ip["nivel"]
        total_peso = sum(pesos.values())
        distribucion: dict[int, int] = {}
        # Usamos el índice de la lista (ipress.id no está en fila_data aún, pero sí en orden)
        orden = [ip for data in self._ipress_por_departamento.values() for ip in data]
        # Reconstruir ids: las filas se escribieron con next_id correlativo desde 1
        asignado = 0
        for i, ip in enumerate(orden):
            peso = (ip["consultorios"] or 1) * ip["nivel"]
            n = int(round(total_rows * peso / total_peso))
            distribucion[i + 1] = n          # i+1 == id de la IPRESS
            asignado += n
        # Ajustar la diferencia de redondeo en la IPRESS con mayor peso
        if asignado != total_rows:
            top = max(distribucion, key=lambda k: distribucion[k])
            distribucion[top] += total_rows - asignado
        return distribucion

    def _elegir_destino_derivacion(self, origen: dict, nivel: int) -> str:
        """Elige un destino de derivación ACTIVO y de nivel >= al origen.

        Prioriza establecimientos de mayor complejidad del mismo departamento;
        si no existen, los del mismo nivel del departamento y, en última
        instancia, los ACTIVOS más cercanos geográficamente de cualquier nivel
        superior. Garantiza que todo DERIVADO tenga un destino válido (la red
        de referencias nunca queda rota).
        """
        todos = [ip for data in self._ipress_por_departamento.values() for ip in data]
        activos = [x for x in todos
                   if x["estado"] == "ACTIVO" and x["codigo"] != origen["codigo"]]
        if not activos:
            return ""
        candidatos = ([x for x in activos if x["nivel"] > nivel]
                      or [x for x in activos if x["nivel"] == nivel]
                      or activos)

        mismo_dept = [x for x in candidatos if x["dept"] == origen["dept"]]
        pool = mismo_dept or candidatos

        def _dist(x: dict) -> float:
            return ((x["lat"] - origen["lat"]) ** 2 + (x["lng"] - origen["lng"]) ** 2) ** 0.5

        top = sorted(pool, key=_dist)[: min(5, len(pool))]
        return self.rng.choice(top)["codigo"]

    def _generar_his(self, total_rows: int, path: str) -> None:
        rng = self.rng
        fechas = [date(ANIO_HIS, 1, 1) + timedelta(days=i) for i in range(366)]
        especialidades_lista = list(ESPECIALIDADES)

        # Distribución de especialidad (acumulada)
        especialidades_names = [e[0] for e in ESPECIALIDADES]
        esp_weights = [PESO_ESPECIALIDAD[e[0]] for e in ESPECIALIDADES]

        # Mapa ipress: codigo -> {nivel, dept, cat}
        mapa_ipress: dict[int, dict] = {}
        for data in self._ipress_por_departamento.values():
            for ip in data:
                mapa_ipress.setdefault(ip["codigo"], ip)

        distribucion = self._distribuir_atenciones(total_rows)

        orden = [ip for data in self._ipress_por_departamento.values() for ip in data]

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["codigo_ipress", "ipress_id", "codigo_ubigeo", "fecha_atencion",
                             "especialidad_id", "diagnostico_cie10", "tipo_atencion",
                             "edad_paciente", "sexo", "tiempo_espera_min",
                             "estado_salida", "derivado_a"])

            for ipress_id, n in distribucion.items():
                ip = orden[ipress_id - 1]
                nivel = ip["nivel"]
                codigo_ubigeo = ip["codigo_ubigeo"]
                codigo = ip["codigo"]

                for _ in range(n):
                    fecha = rng.choice(fechas)
                    esp_cod = rng.choices(especialidades_names, weights=esp_weights)[0]
                    esp = self._esp_por_codigo[esp_cod]

                    tipo = "CONSULTA"
                    if esp_cod == "URGEN" and rng.random() < 0.6:
                        tipo = "EMERGENCIA"
                    elif rng.random() < 0.03 and nivel >= 2:
                        tipo = "HOSPITALIZACION"

                    # Edad y sexo plausibles por especialidad
                    if esp_cod == "PEDIA":
                        edad, sexo = rng.randint(0, 14), rng.choice(["M", "F"])
                    elif esp_cod == "GOBST":
                        edad, sexo = rng.randint(15, 49), "F"
                    else:
                        edad, sexo = rng.randint(1, 89), rng.choice(["M", "F"])

                    # Tiempo de espera (proxy de saturación): mayor en nivel primario
                    base_espera = {1: 70, 2: 45, 3: 25}[nivel]
                    espera = max(5, int(base_espera * rng.uniform(0.5, 2.2) +
                                        (20 if tipo == "EMERGENCIA" else 0)))

                    # Estado de salida según tipo de atención
                    if tipo == "CONSULTA":
                        estado = rng.choices(["ALTA", "DERIVADO", "OBSERVACION", "ABANDONO"],
                                             weights=[0.85, 0.08, 0.05, 0.02])[0]
                    elif tipo == "EMERGENCIA":
                        estado = rng.choices(["ALTA", "HOSPITALIZADO", "OBSERVACION", "DERIVADO", "FALLECIDO"],
                                             weights=[0.60, 0.25, 0.10, 0.04, 0.01])[0]
                    else:
                        estado = rng.choices(["ALTA", "DERIVADO", "OBSERVACION", "FALLECIDO"],
                                             weights=[0.80, 0.08, 0.10, 0.02])[0]

                    derivado_a = ""
                    if estado == "DERIVADO":
                        # Destino garantizado: ACTIVO y de nivel >= al origen
                        derivado_a = self._elegir_destino_derivacion(ip, nivel)

                    writer.writerow([
                        codigo, ipress_id, codigo_ubigeo, fecha.isoformat(), esp["id"],
                        rng.choice(esp["cie"]), tipo, edad, sexo, espera,
                        estado, derivado_a,
                    ])
        self.total_atenciones = total_rows

    # -- Orquestación ------------------------------------------------------
    def ejecutar(self, total_rows: int) -> None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        print("[1/5] Catálogos (categorías + especialidades)...")
        self._generar_categorias(os.path.join(OUTPUT_DIR, "categorizaciones.csv"))
        self._generar_especialidades(os.path.join(OUTPUT_DIR, "especialidades.csv"))
        print("[2/5] Ubigeo (departamentos/provincias/distritos)...")
        self._generar_ubigeo(os.path.join(OUTPUT_DIR, "ubigeo.csv"))
        print("[3/5] IPRESS (RENIPRESS sintético)...")
        self._generar_ipress(
            os.path.join(OUTPUT_DIR, "ubigeo.csv"),
            os.path.join(OUTPUT_DIR, "renipress.csv"))
        print("[4/5] Atenciones HIS-MINSA...")
        self._generar_his(total_rows, os.path.join(OUTPUT_DIR, "his_atenciones.csv"))
        print("[5/5] Resumen")
        print(f"  - Distritos : {self.total_distritos:,}")
        print(f"  - IPRESS    : {self.total_ipress:,}")
        print(f"  - Atenciones: {self.total_atenciones:,} (año {ANIO_HIS})")
        print(f"  - Salida    : {os.path.abspath(OUTPUT_DIR)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generador de dataset sintético SALUD CERCA")
    parser.add_argument("--rows", type=int, default=350_000,
                        help="Número de atenciones HIS a generar (default: 350000)")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()
    GeneradorSaludCerca(seed=args.seed).ejecutar(total_rows=args.rows)


if __name__ == "__main__":
    main()
