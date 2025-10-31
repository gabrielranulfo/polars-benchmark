from __future__ import annotations

from typing import TYPE_CHECKING

from pyspark.sql import SparkSession

from queries.common_utils import (
    check_query_result_pd,
    get_table_path,
    run_query_generic,
)
from settings import Settings

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

settings = Settings()

def get_or_create_spark() -> SparkSession:
    import os
    
    # Configurações agressivas para evitar problemas de segurança
    os.environ['SPARK_LOCAL_IP'] = '127.0.0.1'
    os.environ['SPARK_SUBMIT_OPTS'] = '-Djava.security.manager=allow'
    os.environ['_JAVA_OPTIONS'] = '-Djava.security.manager=allow'
    
    spark = (
        SparkSession.builder.appName("spark_queries")
        .master("local[*]")
        .config("spark.driver.memory", settings.run.spark_driver_memory)
        .config("spark.executor.memory", settings.run.spark_executor_memory)
        .config("spark.log.level", settings.run.spark_log_level)
        # Configurações para desabilitar segurança
        .config("spark.driver.extraJavaOptions", "-Djava.security.manager=allow -Djava.security.policy==")
        .config("spark.executor.extraJavaOptions", "-Djava.security.manager=allow -Djava.security.policy==")
        .config("spark.hadoop.security.authentication", "simple")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .getOrCreate()
    )
    
    # Reduzir logging
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def _read_ds(table_name: str) -> DataFrame:
    if settings.run.io_type == "skip":
        # TODO: Persist data in memory before query
        msg = "cannot run PySpark starting from an in-memory representation"
        raise RuntimeError(msg)

    path = get_table_path(table_name)

    if settings.run.io_type == "parquet":
        df = get_or_create_spark().read.parquet(str(path))
    elif settings.run.io_type == "csv":
        df = get_or_create_spark().read.csv(str(path), header=True, inferSchema=True)
    else:
        msg = f"unsupported file type: {settings.run.io_type!r}"
        raise ValueError(msg)

    df.createOrReplaceTempView(table_name)
    return df


def get_line_item_ds() -> DataFrame:
    return _read_ds("lineitem")


def get_orders_ds() -> DataFrame:
    return _read_ds("orders")


def get_customer_ds() -> DataFrame:
    return _read_ds("customer")


def get_region_ds() -> DataFrame:
    return _read_ds("region")


def get_nation_ds() -> DataFrame:
    return _read_ds("nation")


def get_supplier_ds() -> DataFrame:
    return _read_ds("supplier")


def get_part_ds() -> DataFrame:
    return _read_ds("part")


def get_part_supp_ds() -> DataFrame:
    return _read_ds("partsupp")


def run_query(query_number: int, df: DataFrame) -> None:
    query = df.toPandas
    run_query_generic(
        query, query_number, "pyspark", query_checker=check_query_result_pd
    )
