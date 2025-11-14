#!/bin/bash
#SBATCH --job-name=dissertacao_tpch
#SBATCH --partition=cei
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=4
#SBATCH --time=03:30:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

set -e
git checkout mestrado
docker compose down --rmi all --volumes --remove-orphans
docker system prune -a -f --volumes
docker compose build --no-cache --pull
docker compose up -d --force-recreate
