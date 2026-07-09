from __future__ import annotations

from importlib.metadata import version
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
    if 'SPARK_LOCAL_IP' not in os.environ:
        os.environ['SPARK_LOCAL_IP'] = '127.0.0.1'
    os.environ['SPARK_SUBMIT_OPTS'] = '-Djava.security.manager=allow'
    os.environ['_JAVA_OPTIONS'] = '-Djava.security.manager=allow'
    
    master_url = settings.run.pyspark_master
    is_distributed = master_url != "local[*]"

    spark_builder = (
        SparkSession.builder.appName("spark_queries")
        .master(master_url)
        .config("spark.driver.memory", settings.run.spark_driver_memory)
        .config("spark.executor.memory", settings.run.spark_executor_memory)
        .config("spark.log.level", settings.run.spark_log_level)
        .config("spark.driver.host", os.environ.get('POD_IP', '127.0.0.1'))
        .config("spark.driver.bindAddress", "0.0.0.0")
        .config("spark.driver.extraJavaOptions", "-Djava.security.manager=allow -Djava.security.policy==")
        .config("spark.executor.extraJavaOptions", "-Djava.security.manager=allow -Djava.security.policy==")
        .config("spark.hadoop.security.authentication", "simple")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
    )
    
    if is_distributed:
        spark_builder = (
            spark_builder
            .config("spark.dynamicAllocation.enabled", "true")
            .config("spark.dynamicAllocation.minExecutors", "1")
            .config("spark.dynamicAllocation.maxExecutors", "6")
            .config("spark.dynamicAllocation.initialExecutors", "2")
            .config("spark.dynamicAllocation.shuffleTracking.enabled", "true")
        )
    
    spark = spark_builder.getOrCreate()
    
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


def get_executor_count() -> int:
    master_url = settings.run.pyspark_master
    if master_url and master_url != "local[*]":
        try:
            spark = get_or_create_spark()
            mem_status = spark.sparkContext.getExecutorMemoryStatus()
            return max(0, len(mem_status) - 1)
        except Exception:
            return 0
    return 0


def run_query(query_number: int, df: DataFrame) -> None:
    def query():
        if settings.scale_factor == 1 and settings.run.check_results:
            return df.toPandas()

        return df.collect()
    run_query_generic(
        query,
        query_number,
        "pyspark",
        library_version=version("pyspark"),
        query_checker=check_query_result_pd,
    )
