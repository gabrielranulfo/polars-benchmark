#!/bin/bash
#SBATCH --job-name=dissertacao_tpch
#SBATCH --partition=draco
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=4
#SBATCH --time=03:30:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

export RUN_LOG_TIMINGS=1
export SCALE_FACTOR=1.0

export N_CORES=2

export POLARS_MAX_THREADS=$N_CORES
export SPARK_CORES=$N_CORES
export DASK_WORKER_CONCURRENCY=$N_CORES
export MODIN_CPUS=$N_CORES

#export MODIN_MEMORY=8g
#export MODIN_BLOCK_SIZE=128m
#export MODIN_MEMORY_PER_NODE=8g
#export MODIN_MEMORY_PER_NODE=8g

#echo run with cached IO

make tables SCALE_FACTOR=$SCALE_FACTOR

make  run-modin run-pandas run-polars run-dask run-pyspark

#make plot