export RUN_LOG_TIMINGS=1
#export SCALE_FACTOR=1.0

# Define N_CORES com valor padrão de 2 caso não esteja definido
export N_CORES=${N_CORES:-8}

export POLARS_MAX_THREADS=$N_CORES
export SPARK_CORES=$N_CORES
export DASK_WORKER_CONCURRENCY=$N_CORES
export MODIN_CPUS=$N_CORES

#export MODIN_MEMORY=8g
#export MODIN_BLOCK_SIZE=128m
#export MODIN_MEMORY_PER_NODE=8g
#export MODIN_MEMORY_PER_NODE=8g

#echo run with cached IO

#export pasta=$PWD

#rm -rfv $pasta/output/*

make tables SCALE_FACTOR=$SCALE_FACTOR

make run-all

#make run-duckdb

#make plot