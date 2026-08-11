# ============================================================================
# SALUD CERCA - tests/test_bronze_silver.py
# ----------------------------------------------------------------------------
# Integración ligera sobre el lakehouse real: Bronze -> Silver.
# Verifica conteos finales y los invariantes de calidad de la capa Silver.
# ============================================================================

from __future__ import annotations

from pyspark.sql import functions as F

from silver import SilverWriter


def test_silver_ipress_conteo_y_coordenadas(spark, cfg):
    silver = SilverWriter(spark, cfg).construir_ipress()
    assert silver.count() == 1844

    # Geocoding: ninguna IPRESS sin coordenadas tras la imputación
    sin_coords = silver.filter(F.col("latitud").isNull() | F.col("longitud").isNull())
    assert sin_coords.count() == 0

    # Clave natural única y normalizada
    duplicados = (
        silver.groupBy("codigo_renipress").count().filter(F.col("count") > 1)
    )
    assert duplicados.count() == 0
    vacios = silver.filter(F.col("codigo_renipress") == "")
    assert vacios.count() == 0

    # Booleano convertido correctamente (sin nulos)
    nulos_bool = silver.filter(F.col("tiene_ambulancia").isNull())
    assert nulos_bool.count() == 0


def test_silver_his_conteo_y_dominios(spark, cfg):
    silver = SilverWriter(spark, cfg).construir_his()
    # 350.000 crudas - 113 duplicadas = 349.887
    assert silver.count() == 349_887

    # Dominio de tipo_atencion válido y sin fechas nulas
    invalidos = silver.filter(
        ~F.col("tipo_atencion").isin("CONSULTA", "EMERGENCIA", "HOSPITALIZACION", "PREVENTIVA")
    )
    assert invalidos.count() == 0
    fechas_nulas = silver.filter(F.col("fecha_atencion").isNull())
    assert fechas_nulas.count() == 0

    # fecha_key coherente con la partición anio/mes
    incoherentes = silver.filter(F.col("fecha_key") != F.date_format("fecha_atencion", "yyyy-MM"))
    assert incoherentes.count() == 0
