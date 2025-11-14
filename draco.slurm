#!/bin/bash
#SBATCH --job-name=dissertacao_tpch
#SBATCH --partition=draco
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=4
#SBATCH --time=03:30:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

set -e

git checkout mestrado
#docker build --no-cache -t polars-benchmark .
docker compose build 

docker compose up
