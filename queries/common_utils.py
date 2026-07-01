from __future__ import annotations

import re
import sys
import os
import time
from importlib.metadata import version
from pathlib import Path
from subprocess import run, Popen
from typing import TYPE_CHECKING, Any

from linetimer import CodeTimer

from prometheus_client import CollectorRegistry, Gauge, pushadd_to_gateway

from settings import Settings

if TYPE_CHECKING:
    from collections.abc import Callable

    import pandas as pd
    import polars as pl

settings = Settings()


def get_table_path(table_name: str) -> Path:
    """Return the path to the given table."""
    ext = settings.run.io_type if settings.run.include_io else "parquet"
    return settings.dataset_base_dir / f"{table_name}.{ext}"


def log_query_timing(
    solution: str, version: str, query_number: int, time: float
) -> None:
    output_path = Path("output/run/timings.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # include PID so we can correlate timings with monitoring logs
    pid = os.getpid()

    with output_path.open("a") as f:
        # add header including pid if file is empty
        if f.tell() == 0:
            f.write("solution,version,query_number,duration[s],io_type,scale_factor,pid\n")

        line = (
            ",".join(
                [
                    solution,
                    version,
                    str(query_number),
                    str(time),
                    settings.run.io_type,
                    str(settings.scale_factor),
                    str(pid),
                ]
            )
            + "\n"
        )
        f.write(line)

def on_second_call(func: Any) -> Any:
    def helper(*args: Any, **kwargs: Any) -> Any:
        helper.calls += 1  # type: ignore[attr-defined]

        # first call is outside the function
        # this call must set the result
        if helper.calls == 1:  # type: ignore[attr-defined]
            # include IO will compute the result on the 2nd call
            if not settings.run.include_io:
                helper.result = func(*args, **kwargs)  # type: ignore[attr-defined]
            return helper.result  # type: ignore[attr-defined]

        # second call is in the query, now we set the result
        if settings.run.include_io and helper.calls == 2:  # type: ignore[attr-defined]
            helper.result = func(*args, **kwargs)  # type: ignore[attr-defined]

        return helper.result  # type: ignore[attr-defined]

    helper.calls = 0  # type: ignore[attr-defined]
    helper.result = None  # type: ignore[attr-defined]

    return helper

def execute_all(library_name: str) -> None:
    print(settings.model_dump_json())

    query_numbers = _get_query_numbers(library_name)

    with CodeTimer(name=f"Overall execution of ALL {library_name} queries", unit="s"):

        for query_number in query_numbers:

            process = Popen([sys.executable, "-m", f"queries.{library_name}.q{query_number}"])
            start = time.time()

            worker_count = _get_worker_count(library_name)
            _push_metrics(library=library_name, query_number=query_number, worker_count=worker_count)

            process.wait()

            duration = time.time() - start
            worker_count = _get_worker_count(library_name)
            _push_metrics(library=library_name, query_number=0, worker_count=worker_count, duration=duration)

def _get_pushgateway_url() -> str | None:
    host = os.getenv("PUSHGATEWAY_HOST", "pushgateway")
    port = os.getenv("PUSHGATEWAY_PORT", "9091")
    return f"{host}:{port}"


def _push_metrics(
    library: str,
    query_number: int,
    worker_count: int = 0,
    duration: float | None = None,
) -> None:
    url = _get_pushgateway_url()
    if not url:
        return
    try:
        registry = CollectorRegistry()

        g = Gauge("tpch_query_number", "", ["library"], registry=registry)
        g.labels(library=library).set(query_number)

        w = Gauge("tpch_worker_count", "", ["library"], registry=registry)
        w.labels(library=library).set(worker_count)

        if duration is not None:
            d = Gauge("tpch_query_duration_seconds", "", ["library", "query"], registry=registry)
            d.labels(library=library, query=str(query_number)).set(duration)

        pushadd_to_gateway(url, job="tpch", registry=registry)
    except Exception:
        pass


def _get_worker_count(library_name: str) -> int:
    try:
        if library_name == "dask":
            from queries.dask.utils import get_worker_count
            return get_worker_count()
        elif library_name == "pyspark":
            from queries.pyspark.utils import get_executor_count
            return get_executor_count()
    except Exception:
        pass
    return 0


def _get_query_numbers(library_name: str) -> list[int]:
    """Get the query numbers that are implemented for the given library."""
    query_numbers = []

    path = Path(__file__).parent / library_name
    expr = re.compile(r"q(\d+).py$")

    for file in path.iterdir():
        match = expr.search(str(file))
        if match is not None:
            query_numbers.append(int(match.group(1)))

    return sorted(query_numbers)

def run_query_generic(
    query: Callable[..., Any],
    query_number: int,
    library_name: str,
    library_version: str | None = None,
    query_checker: Callable[..., None] | None = None,
) -> None:
    """Execute a query."""
    with CodeTimer(name=f"Run {library_name} query {query_number}", unit="s") as timer:
        result = query()

    if settings.run.log_timings:
        log_query_timing(
            solution=library_name,
            version=library_version or version(library_name),
            query_number=query_number,
            time=timer.took,
        )

    if settings.run.check_results:
        if query_checker is None:
            msg = "cannot check results if no query checking function is provided"
            raise ValueError(msg)
        if settings.scale_factor != 1:
            msg = f"cannot check results when scale factor is not 1, got {settings.scale_factor}"
            raise RuntimeError(msg)
        query_checker(result, query_number)

    if settings.run.show_results:
        print(result)

def check_query_result_pl(result: pl.DataFrame, query_number: int) -> None:
    """Assert that the Polars result of the query is correct."""
    from polars.testing import assert_frame_equal

    expected = _get_query_answer_pl(query_number)
    assert_frame_equal(result, expected, check_dtype=False)

def check_query_result_pd(result: pd.DataFrame, query_number: int) -> None:
    """Assert that the pandas result of the query is correct."""
    from pandas.testing import assert_frame_equal

    expected = _get_query_answer_pd(query_number)
    assert_frame_equal(result.reset_index(drop=True), expected, check_dtype=False)

def _get_query_answer_pl(query: int) -> pl.DataFrame:
    """Read the true answer to the query from disk as a Polars DataFrame."""
    from polars import read_parquet

    path = settings.paths.answers / f"q{query}.parquet"
    return read_parquet(path)

def _get_query_answer_pd(query: int) -> pd.DataFrame:
    """Read the true answer to the query from disk as a pandas DataFrame."""
    from pandas import read_parquet

    path = settings.paths.answers / f"q{query}.parquet"
    return read_parquet(path, dtype_backend="pyarrow")