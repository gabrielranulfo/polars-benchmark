from __future__ import annotations
import os, warnings
os.environ["MODIN_ENGINE"] = "Ray"

from typing import TYPE_CHECKING, Any
import modin.pandas as pd

from queries.common_utils import (
    check_query_result_pd,
    get_table_path,
    on_second_call,
    run_query_generic,
)
from settings import Settings

if TYPE_CHECKING:
    from collections.abc import Callable

settings = Settings()

pd.options.mode.copy_on_write = True
os.environ["MODIN_MEMORY"] = str(settings.run.modin_memory)

# Suprimir warnings de todas as bibliotecas relacionadas
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=ImportWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", module="modin")
warnings.filterwarnings("ignore", module="pandas")
warnings.filterwarnings("ignore", module="pyarrow")
warnings.filterwarnings("ignore", module="ray")
warnings.filterwarnings("ignore", module="numpy")
warnings.filterwarnings("ignore", module="dask")
warnings.filterwarnings("ignore")
os.environ["MODIN_DEBUG"] = "0"
os.environ["RAY_DISABLE_IMPORT_WARNING"] = "1"
os.environ["PYARROW_IGNORE_TIMEZONE"] = "1"
os.environ["RAY_SILENT"] = "1"
os.environ["RAY_LOG_TO_STDERR"] = "0"
os.environ["RAY_DISABLE_CUSTOM_LOGGING"] = "1"
os.environ["RAY_disable_pickle_debug"] = "1"
os.environ["RAY_disable_usage_stats"] = "1"
os.environ["RAY_disable_ray_logging"] = "1"
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "0"
#os.environ["RAY_object_store_memory"] = "2000000000"  # 2GB
os.environ["RAY_enable_object_reconstruction"] = "0"
os.environ["PYTHONWARNINGS"] = "ignore"



def _read_ds(table_name: str) -> pd.DataFrame:
    path = get_table_path(table_name)

    if settings.run.io_type in ("parquet", "skip"):
        return pd.read_parquet(path, dtype_backend="numpy_nullable")
    elif settings.run.io_type == "csv":
        df = pd.read_csv(path, dtype_backend="numpy_nullable")
        # TODO: This is slow - we should use the known schema to read dates directly
        for c in df.columns:
            if c.endswith("date"):
                df[c] = df[c].astype("date32[day][pyarrow]")
        return df
    elif settings.run.io_type == "feather":
        return pd.read_feather(path, dtype_backend="pyarrow")
    else:
        msg = f"unsupported file type: {settings.run.io_type!r}"
        raise ValueError(msg)


@on_second_call
def get_line_item_ds() -> pd.DataFrame:
    return _read_ds("lineitem")


@on_second_call
def get_orders_ds() -> pd.DataFrame:
    return _read_ds("orders")


@on_second_call
def get_customer_ds() -> pd.DataFrame:
    return _read_ds("customer")


@on_second_call
def get_region_ds() -> pd.DataFrame:
    return _read_ds("region")


@on_second_call
def get_nation_ds() -> pd.DataFrame:
    return _read_ds("nation")


@on_second_call
def get_supplier_ds() -> pd.DataFrame:
    return _read_ds("supplier")


@on_second_call
def get_part_ds() -> pd.DataFrame:
    return _read_ds("part")


@on_second_call
def get_part_supp_ds() -> pd.DataFrame:
    return _read_ds("partsupp")


def run_query(query_number: int, query: Callable[..., Any]) -> None:
    run_query_generic(
        query,
        query_number,
        "modin",
        query_checker=lambda df, q: check_query_result_pd(df._to_pandas(), q),
    )
