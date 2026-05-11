from pathlib import Path
from typing import Literal, TypeAlias, Any
import os

# pydantic may not be available in restricted environments; provide fallbacks
try:
    from pydantic import computed_field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover - simple stand-ins when libs missing
    # minimal decorator that leaves property untouched
    def computed_field(func):
        return func

    class BaseSettings:  # type: ignore[misc]
        def __init__(self, **kwargs: Any) -> None:  # type: ignore[override]
            for k, v in kwargs.items():
                setattr(self, k, v)

    SettingsConfigDict = dict  # type: ignore[assignment]

IoType: TypeAlias = Literal["skip", "parquet", "feather", "csv"]


class Paths(BaseSettings):
    answers: Path = Path("data/answers")
    tables: Path = Path("data/tables")

    timings: Path = Path("output/run")
    timings_filename: str = "timings.csv"

    plots: Path = Path("output/plot")

    model_config = SettingsConfigDict(
        env_prefix="path_", env_file=".env", extra="ignore"
    )


class Run(BaseSettings):
    io_type: IoType = "parquet"

    log_timings: bool = True
    show_results: bool = False
    check_results: bool = False  # Only available for SCALE_FACTOR=1

    polars_show_plan: bool = False
    polars_eager: bool = False
    polars_streaming: bool = False

    modin_memory: int = 60_000_000_000  # Tune as needed for optimal performance

    spark_driver_memory: str = os.getenv("SPARK_DRIVER_MEMORY", "4g")
    spark_executor_memory: str = os.getenv("SPARK_EXECUTOR_MEMORY", "55g")
    spark_log_level: str = "ERROR"

    @computed_field  # type: ignore[misc]
    @property
    def include_io(self) -> bool:
        return self.io_type != "skip"

    model_config = SettingsConfigDict(
        env_prefix="run_", env_file=".env", extra="ignore"
    )


class Kubernetes(BaseSettings):
    """Kubernetes and HPA configuration for distributed benchmarks"""
    
    # General
    enabled: bool = os.getenv("K8S_ENABLED", "false").lower() == "true"
    namespace: str = os.getenv("K8S_NAMESPACE", "tpch-benchmark")
    
    # Dask configuration
    dask_scheduler_host: str = os.getenv("DASK_SCHEDULER_HOST", "dask-scheduler")
    dask_scheduler_port: int = int(os.getenv("DASK_SCHEDULER_PORT", "8786"))
    dask_worker_replicas_min: int = int(os.getenv("DASK_WORKER_REPLICAS_MIN", "2"))
    dask_worker_replicas_max: int = int(os.getenv("DASK_WORKER_REPLICAS_MAX", "10"))
    dask_worker_cpu_request: str = os.getenv("DASK_WORKER_CPU_REQUEST", "2")
    dask_worker_memory_request: str = os.getenv("DASK_WORKER_MEMORY_REQUEST", "4Gi")
    dask_worker_cpu_threshold: int = int(os.getenv("DASK_WORKER_CPU_THRESHOLD", "70"))
    dask_worker_memory_threshold: int = int(os.getenv("DASK_WORKER_MEMORY_THRESHOLD", "80"))
    
    # PySpark configuration
    pyspark_master_host: str = os.getenv("PYSPARK_MASTER_HOST", "pyspark-master")
    pyspark_master_port: int = int(os.getenv("PYSPARK_MASTER_PORT", "7077"))
    pyspark_executor_replicas_min: int = int(os.getenv("PYSPARK_EXECUTOR_REPLICAS_MIN", "2"))
    pyspark_executor_replicas_max: int = int(os.getenv("PYSPARK_EXECUTOR_REPLICAS_MAX", "10"))
    pyspark_executor_cpu_request: str = os.getenv("PYSPARK_EXECUTOR_CPU_REQUEST", "2")
    pyspark_executor_memory_request: str = os.getenv("PYSPARK_EXECUTOR_MEMORY_REQUEST", "4Gi")
    pyspark_executor_cpu_threshold: int = int(os.getenv("PYSPARK_EXECUTOR_CPU_THRESHOLD", "75"))
    pyspark_executor_memory_threshold: int = int(os.getenv("PYSPARK_EXECUTOR_MEMORY_THRESHOLD", "80"))
    
    # HPA behavior
    hpa_scale_up_window: int = int(os.getenv("HPA_SCALE_UP_WINDOW", "0"))
    hpa_scale_down_window: int = int(os.getenv("HPA_SCALE_DOWN_WINDOW", "300"))
    
    model_config = SettingsConfigDict(
        env_prefix="k8s_", env_file=".env", extra="ignore"
    )


class Plot(BaseSettings):
    show: bool = False
    n_queries: int = 7
    y_limit: float | None = None

    model_config = SettingsConfigDict(
        env_prefix="plot_", env_file=".env", extra="ignore"
    )

class Settings(BaseSettings):
    scale_factor: float = 1.0

    paths: Paths = Paths()
    plot: Plot = Plot()
    run: Run = Run()
    kubernetes: Kubernetes = Kubernetes()

    @computed_field  # type: ignore[misc]
    @property
    def dataset_base_dir(self) -> Path:
        return self.paths.tables / f"scale-{self.scale_factor}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
