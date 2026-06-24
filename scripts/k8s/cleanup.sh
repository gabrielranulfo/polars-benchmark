#!/bin/bash
# Clean up Kubernetes deployments
# Usage: ./scripts/k8s/cleanup.sh [dask|pyspark|all]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET="${1:-all}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found. Please install kubectl."
    exit 1
fi

# Function to delete resources
delete_resources() {
    local target=$1
    
    case $target in
        dask)
            log_info "Deleting Dask HPA..."
            kubectl delete hpa -n tpch-benchmark dask-worker-hpa --ignore-not-found=true
            
            log_info "Deleting Dask deployment..."
            kubectl delete deployment -n tpch-benchmark dask-scheduler dask-worker --ignore-not-found=true
            
            log_info "Deleting Dask services..."
            kubectl delete service -n tpch-benchmark dask-scheduler --ignore-not-found=true
            ;;
        pyspark)
            log_info "Deleting PySpark HPA..."
            kubectl delete hpa -n tpch-benchmark pyspark-worker-hpa --ignore-not-found=true
            
            log_info "Deleting PySpark deployments..."
            kubectl delete deployment -n tpch-benchmark pyspark-driver pyspark-master pyspark-worker --ignore-not-found=true
            
            log_info "Deleting PySpark services..."
            kubectl delete service -n tpch-benchmark pyspark-master --ignore-not-found=true
            ;;
        all)
            delete_resources "dask"
            delete_resources "pyspark"
            
            log_info "Deleting persistence resources..."
            kubectl delete pvc -n tpch-benchmark tpch-output-pvc --ignore-not-found=true
            kubectl delete pv tpch-output-pv --ignore-not-found=true
            
            log_info "Deleting RBAC resources..."
            kubectl delete clusterrolebinding tpch-metrics-reader --ignore-not-found=true dask-metrics-reader pyspark-metrics-reader
            kubectl delete clusterrole tpch-metrics-reader --ignore-not-found=true
            
            log_info "Deleting namespace..."
            kubectl delete namespace tpch-benchmark --ignore-not-found=true
            ;;
        *)
            log_error "Invalid target: $target. Use 'dask', 'pyspark', or 'all'"
            exit 1
            ;;
    esac
}

log_warn "This will delete Kubernetes resources for target: $TARGET"
read -p "Are you sure? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Cleanup cancelled"
    exit 0
fi

delete_resources "$TARGET"
log_info "Cleanup complete!"
