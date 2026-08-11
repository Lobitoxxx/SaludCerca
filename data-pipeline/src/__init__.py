# ============================================================================
# SALUD CERCA - data-pipeline
# ----------------------------------------------------------------------------
# Pipeline de Big Data (PySpark) con arquitectura Medallón (Lakehouse):
#
#   Bronze (raw)  -> Silver (limpio)  -> Gold (PostgreSQL + PostGIS + pgvector)
#
#   main.py  --stage bronze|silver|gold|all
#
# Estructura:
#   src/config.py      Configuración + SparkSession tuning
#   src/ingestion.py   Lectura masiva CSV/JSON (RENIPRESS, HIS-MINSA)
#   src/cleaning.py    Deduplicación, geocoding imputado, tipificación
#   src/bronze.py      Persistencia capa Bronze (Parquet crudo)
#   src/silver.py      Limpieza + persistencia capa Silver (Parquet limpio)
#   src/gold.py        UPSERT a PostgreSQL/PostGIS (capa Gold) + OLAP refresh
# ============================================================================
