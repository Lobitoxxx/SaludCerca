# ============================================================================
# SALUD CERCA - tests/test_cleaning.py
# ----------------------------------------------------------------------------
# Verifica la capa de calidad de datos (Silver):
#   * deduplicación (conserva la fila más reciente)
#   * geocoding imputado con centroide del ubigeo
#   * tipificación de IPRESS (normalización + booleano)
#   * tipificación de HIS (dominios, fechas y fecha_key)
# ============================================================================

from __future__ import annotations

from datetime import date

from pyspark.sql import functions as F
from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

from cleaning import DataCleaner

IPRESS_SCHEMA = StructType(
    [
        StructField("id", IntegerType()),
        StructField("codigo_renipress", StringType()),
        StructField("nombre", StringType()),
        StructField("departamento", StringType()),
        StructField("provincia", StringType()),
        StructField("distrito", StringType()),
        StructField("latitud", DoubleType()),
        StructField("longitud", DoubleType()),
        StructField("estado_operativo", StringType()),
        StructField("capacidad_camas", IntegerType()),
        StructField("capacidad_consultorios", IntegerType()),
        StructField("tiene_ambulancia", StringType()),
    ]
)

UBIGEO_SCHEMA = StructType(
    [
        StructField("id", IntegerType()),
        StructField("codigo_ubigeo", StringType()),
        StructField("latitud_centroide", DoubleType()),
        StructField("longitud_centroide", DoubleType()),
    ]
)

HIS_SCHEMA = StructType(
    [
        StructField("codigo_ipress", StringType()),
        StructField("codigo_ubigeo", StringType()),
        StructField("fecha_atencion", DateType()),
        StructField("especialidad_id", IntegerType()),
        StructField("diagnostico_cie10", StringType()),
        StructField("tipo_atencion", StringType()),
        StructField("edad_paciente", IntegerType()),
        StructField("sexo", StringType()),
    ]
)


def _ipress_df(spark, filas):
    return spark.createDataFrame(filas, schema=IPRESS_SCHEMA)


# -- 1) Deduplicación --------------------------------------------------------

def test_dedup_conserva_la_fila_mas_reciente(spark):
    df = _ipress_df(spark, [
        (1, "A1", "H1", "LIMA", "LIMA", "LIMA", None, None, "ACTIVO", 1, 1, "f"),
        (2, "A1", "H1", "LIMA", "LIMA", "LIMA", None, None, "ACTIVO", 1, 1, "t"),  # duplicado
        (3, "A2", "H2", "LIMA", "LIMA", "LIMA", None, None, "ACTIVO", 2, 2, "f"),
    ])
    resultado = DataCleaner.deduplicar(df, subset=["codigo_renipress"], orden="id")
    assert resultado.count() == 2
    ids = {r["id"] for r in resultado.select("id").collect()}
    # Para "A1" se conserva la de mayor id (más reciente)
    assert ids == {2, 3}


def test_dedup_sin_subset_no_toca(spark):
    df = _ipress_df(spark, [(1, "A1", "H1", "LIMA", "LIMA", "LIMA", None, None, "ACTIVO", 1, 1, "f")])
    resultado = DataCleaner.deduplicar(df, subset=["columna_inexistente"], orden="id")
    assert resultado.count() == 1


# -- 2) Geocoding imputado ---------------------------------------------------

def test_imputar_geocoding_rellena_centroide(spark):
    ipress = _ipress_df(spark, [
        (1, "A1", "H1", "LIMA", "LIMA", "LIMA", None, None, "ACTIVO", 1, 1, "f"),
    ]).withColumn("ubigeo_id", F.lit(10))
    ubigeo = spark.createDataFrame(
        [(10, "010101", -12.5, -77.1)], schema=UBIGEO_SCHEMA
    )
    resultado = DataCleaner.imputar_geocoding(ipress, ubigeo)
    fila = resultado.collect()[0]
    assert fila["latitud"] == -12.5
    assert fila["longitud"] == -77.1


def test_imputar_geocoding_sin_faltantes_no_cambia(spark):
    ipress = _ipress_df(spark, [
        (1, "A1", "H1", "LIMA", "LIMA", "LIMA", -12.0, -77.0, "ACTIVO", 1, 1, "f"),
    ]).withColumn("ubigeo_id", F.lit(10))
    ubigeo = spark.createDataFrame(
        [(10, "010101", -12.5, -77.1)], schema=UBIGEO_SCHEMA
    )
    resultado = DataCleaner.imputar_geocoding(ipress, ubigeo)
    fila = resultado.collect()[0]
    assert fila["latitud"] == -12.0
    assert fila["longitud"] == -77.0


# -- 3) Tipificación IPRESS --------------------------------------------------

def test_tipificar_ipress_convierte_booleano(spark):
    df = _ipress_df(spark, [
        (1, " a1 ", " h ", " lima ", " lima ", " lima ", -12.0, -77.0, " activo ", 1, 1, "t"),
        (2, "b2", "h", "LIMA", "LIMA", "LIMA", -12.0, -77.0, "ACTIVO", 1, 1, "f"),
        (3, "c3", "h", "LIMA", "LIMA", "LIMA", -12.0, -77.0, "ACTIVO", 1, 1, "1"),
        (4, "d4", "h", "LIMA", "LIMA", "LIMA", -12.0, -77.0, "ACTIVO", 1, 1, "0"),
    ])
    resultado = DataCleaner.tipificar_ipress(df).orderBy("id").collect()
    assert resultado[0]["codigo_renipress"] == "A1"
    assert resultado[0]["nombre"] == "H"
    assert resultado[0]["tiene_ambulancia"] is True
    assert resultado[1]["tiene_ambulancia"] is False
    assert resultado[2]["tiene_ambulancia"] is True
    assert resultado[3]["tiene_ambulancia"] is False


def test_tipificar_ipress_capacidades_sin_nulos(spark):
    df = _ipress_df(spark, [
        (1, "A1", "H1", "LIMA", "LIMA", "LIMA", None, None, "ACTIVO", None, None, "f"),
    ])
    resultado = DataCleaner.tipificar_ipress(df).collect()[0]
    assert resultado["capacidad_camas"] == 0
    assert resultado["capacidad_consultorios"] == 0


def test_tipificar_ipress_descarta_codigo_vacio(spark):
    df = _ipress_df(spark, [
        (1, "", "H1", "LIMA", "LIMA", "LIMA", None, None, "ACTIVO", 1, 1, "f"),
        (2, "A1", "H2", "LIMA", "LIMA", "LIMA", None, None, "ACTIVO", 1, 1, "f"),
    ])
    resultado = DataCleaner.tipificar_ipress(df)
    assert resultado.count() == 1
    assert resultado.collect()[0]["codigo_renipress"] == "A1"


# -- 4) Tipificación HIS -----------------------------------------------------

def test_tipificar_his_filtra_dominios_y_fecha_key(spark):
    df = spark.createDataFrame(
        [
            ("00000001", "010101", date(2024, 5, 24), 4, "K80", "consulta", 14, "f"),
            ("00000001", "010101", date(2024, 12, 16), 7, "M54", "EMERGENCIA", 37, "m"),
            ("00000001", "010101", None, 4, "K80", "CONSULTA", 14, "f"),   # fecha inválida
            ("00000001", "010101", date(2024, 6, 1), 4, "K80", "INVALIDO", 14, "f"),  # dominio inválido
        ],
        schema=HIS_SCHEMA,
    )
    resultado = DataCleaner.tipificar_his(df)
    assert resultado.count() == 2

    filas = resultado.orderBy("fecha_atencion").collect()
    assert str(filas[0]["tipo_atencion"]) == "CONSULTA"
    assert str(filas[1]["sexo"]) == "M"
    assert filas[1]["anio"] == 2024
    assert filas[1]["mes"] == 12
    assert filas[1]["fecha_key"] == "2024-12"


def test_tipificar_his_normaliza_cie10(spark):
    df = spark.createDataFrame(
        [
            ("00000001", "010101", date(2024, 1, 5), 4, "k80", "CONSULTA", 14, "f"),
        ],
        schema=HIS_SCHEMA,
    )
    resultado = DataCleaner.tipificar_his(df).collect()[0]
    assert resultado["diagnostico_cie10"] == "K80"
