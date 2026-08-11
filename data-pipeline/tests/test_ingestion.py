# ============================================================================
# SALUD CERCA - tests/test_ingestion.py
# ----------------------------------------------------------------------------
# Verifica la lectura masiva de las fuentes: esquemas tipados, conteos y
# aislamiento de registros corruptos (modo PERMISSIVE).
# ============================================================================

from __future__ import annotations

from pyspark.sql.types import DoubleType, StringType

from ingestion import HisReader, RenipressReader, UbigeoReader

RENIPRESS_PATH = "../data/output/renipress.csv"
HIS_PATH = "../data/output/his_atenciones.csv"
UBIGEO_PATH = "../data/output/ubigeo.csv"


def test_renipress_conteo_y_esquema(spark):
    df = RenipressReader.read(spark, RENIPRESS_PATH)
    assert df.count() == 1844

    tipos = dict(df.dtypes)
    assert tipos["codigo_renipress"] == "string"
    assert tipos["latitud"] == "double"
    assert tipos["longitud"] == "double"
    # Booleano se lee como string en crudo (conversión ocurre en Silver)
    assert tipos["tiene_ambulancia"] == "string"


def test_renipress_sin_corruptos(spark):
    df = RenipressReader.read(spark, RENIPRESS_PATH)
    # PERMISSIVE: la columna _corrupt_record solo se materializa si hay filas malas
    if "_corrupt_record" in df.columns:
        corruptos = df.filter("_corrupt_record IS NOT NULL")
        assert corruptos.count() == 0


def test_his_conteo_y_esquema(spark):
    df = HisReader.read(spark, HIS_PATH)
    assert df.count() == 350_000

    tipos = dict(df.dtypes)
    assert tipos["fecha_atencion"] == "date"
    assert tipos["edad_paciente"] == "int"
    assert tipos["tiempo_espera_min"] == "int"


def test_his_fechas_en_rango(spark):
    from datetime import date

    df = HisReader.read(spark, HIS_PATH)
    desde = df.agg({"fecha_atencion": "min"}).collect()[0][0]
    hasta = df.agg({"fecha_atencion": "max"}).collect()[0][0]
    assert isinstance(desde, date)
    assert desde >= date(2024, 1, 1)
    assert hasta <= date(2024, 12, 31)


def test_ubigeo_conteo_y_tipos(spark):
    df = UbigeoReader.read(spark, UBIGEO_PATH)
    assert df.count() == 957
    tipos = dict(df.dtypes)
    assert tipos["codigo_ubigeo"] == "string"
    assert tipos["latitud_centroide"] == "double"
    assert tipos["longitud_centroide"] == "double"
