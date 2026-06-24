#!/usr/bin/env bash
# Copy TPC-H data tables to all KIND nodes so the data PV is populated.
# Usage: ./scripts/k8s/copy-data-to-kind.sh [scale_factor]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCALE_FACTOR="${1:-1.0}"

DATA_SRC="$PROJECT_ROOT/data/tables/scale-$SCALE_FACTOR"
PV_ROOT="/data/tpch-benchmark/tables"
NODES=$(kind get nodes --name tpch-cluster 2>/dev/null || echo "")

if [ -z "$NODES" ]; then
    echo "ERROR: KIND cluster 'tpch-cluster' not found. Are you on netsr-cc-proj06?"
    exit 1
fi

if [ ! -d "$DATA_SRC" ]; then
    echo "ERROR: Data not found at $DATA_SRC"
    echo "Run 'make tables SCALE_FACTOR=$SCALE_FACTOR' first."
    exit 1
fi

echo "Copying scale-$SCALE_FACTOR data to KIND nodes..."
for node in $NODES; do
    echo "  -> $node"
    docker exec "$node" mkdir -p "$PV_ROOT/scale-$SCALE_FACTOR"
    docker cp "$DATA_SRC/." "$node:$PV_ROOT/scale-$SCALE_FACTOR/"
done

echo "Done! Data is now available in all nodes."
