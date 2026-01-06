import duckdb
from duckdb import DuckDBPyRelation

from queries.common_utils import (
    check_query_result_pl,
    get_table_path,
    run_query_generic,
)
from settings import Settings

settings = Settings()


def _scan_ds(table_name: str) -> str:
    path = get_table_path(table_name)
    path_str = str(path)

    if settings.run.io_type == "skip":
        name = path_str.replace("/", "_").replace(".", "_").replace("-", "_")
        duckdb.sql(
            f"create temp table if not exists {name} as select * from read_parquet('{path_str}');"
        )
        return name
    elif settings.run.io_type == "parquet":
        name = path_str.replace("/", "_").replace(".", "_").replace("-", "_")
        # create a temp table from the parquet file so queries can reference a table name
        duckdb.sql(
            f"create temp table if not exists {name} as select * from read_parquet('{path_str}');"
        )
        return name
    elif settings.run.io_type == "csv":
        name = path_str.replace("/", "_").replace(".", "_").replace("-", "_")
        # create a temp table from the csv file so queries can reference a table name
        duckdb.sql(
            f"create temp table if not exists {name} as select * from read_csv_auto('{path_str}');"
        )
        return name
    else:
        msg = f"unsupported file type: {settings.run.io_type!r}"
        raise ValueError(msg)


def get_line_item_ds() -> str:
    return _scan_ds("lineitem")


def get_orders_ds() -> str:
    return _scan_ds("orders")


def get_customer_ds() -> str:
    return _scan_ds("customer")


def get_region_ds() -> str:
    return _scan_ds("region")


def get_nation_ds() -> str:
    return _scan_ds("nation")


def get_supplier_ds() -> str:
    return _scan_ds("supplier")


def get_part_ds() -> str:
    return _scan_ds("part")


def get_part_supp_ds() -> str:
    return _scan_ds("partsupp")


def run_query(query_number: int, context: DuckDBPyRelation) -> None:
    query = context.pl
    run_query_generic(
        query, query_number, "duckdb", query_checker=check_query_result_pl
    )
