#!/bin/bash
# Monitor HPA status and pod scaling
# Usage: ./scripts/k8s/monitor-hpa.sh [dask|pyspark|all]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET="${1:-all}"
INTERVAL="${2:-5}"  # Update interval in seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} kubectl not found. Please install kubectl."
    exit 1
fi

# Function to show HPA status
show_hpa_status() {
    local hpa_name=$1
    log_section "HPA Status: $hpa_name"
    kubectl get hpa -n tpch-benchmark "$hpa_name" -o wide
    
    log_section "HPA Details: $hpa_name"
    kubectl describe hpa -n tpch-benchmark "$hpa_name"
}

# Function to show pod status
show_pod_status() {
    local label=$1
    log_section "Pod Status: $label"
    kubectl get pods -n tpch-benchmark -l "$label" -o wide
    
    log_section "Pod Resource Usage: $label"
    kubectl top pods -n tpch-benchmark -l "$label" --containers 2>/dev/null || echo "Metrics not available yet"
}

# Main monitoring loop
log_info "Starting HPA monitoring (interval: ${INTERVAL}s)..."
log_info "Press Ctrl+C to stop"

while true; do
    clear
    log_section "TPC-H Benchmark HPA Monitoring - $(date '+%Y-%m-%d %H:%M:%S')"
    
    case $TARGET in
        dask)
            show_hpa_status "dask-worker-hpa"
            show_pod_status "app=dask-benchmark,component=worker"
            ;;
        pyspark)
            show_hpa_status "pyspark-worker-hpa"
            show_pod_status "app=pyspark-benchmark,component=worker"
            ;;
        all)
            show_hpa_status "dask-worker-hpa"
            show_pod_status "app=dask-benchmark,component=worker"
            show_hpa_status "pyspark-worker-hpa"
            show_pod_status "app=pyspark-benchmark,component=worker"
            ;;
        *)
            echo -e "${RED}[ERROR]${NC} Invalid target: $TARGET. Use 'dask', 'pyspark', or 'all'"
            exit 1
            ;;
    esac
    
    sleep "$INTERVAL"
done
