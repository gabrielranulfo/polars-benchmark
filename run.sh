export RUN_LOG_TIMINGS=1
export SCALE_FACTOR=1.0

echo run with cached IO
#make tables
make  run-polars run-pyspark
#make  run-polars run-dask run-pandas run-modin run-duckdb
#make plot

#echo run with IO
#export RUN_INCLUDE_IO=1
#make run-all
#make plot
