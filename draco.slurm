#!/bin/bash
#SBATCH --job-name=artigo_python_nogil
#SBATCH --partition=draco
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=4
#SBATCH --time=03:30:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

export RUN_LOG_TIMINGS=1
export SCALE_FACTOR=1.0

make tables SCALE_FACTOR=$SCALE_FACTOR
make run-pandas 