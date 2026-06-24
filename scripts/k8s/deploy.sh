#!/bin/bash
# Deploy HPA infrastructure to Kubernetes
# Usage: ./scripts/k8s/deploy.sh [dask|pyspark|all]

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

# Check if metrics-server is installed (required for HPA)
log_info "Checking if metrics-server is installed..."
if ! kubectl get deployment -n kube-system metrics-server &> /dev/null; then
    log_warn "metrics-server not found in kube-system namespace. Installing it..."
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    sleep 10
    log_info "metrics-server installed. Waiting for it to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/metrics-server -n kube-system
fi

# Deploy namespace and RBAC
log_info "Deploying namespace and RBAC..."
kubectl apply -f "$PROJECT_ROOT/k8s/base/namespace.yaml"
kubectl apply -f "$PROJECT_ROOT/k8s/base/rbac.yaml"

# Deploy persistence
log_info "Deploying persistent volumes..."
kubectl apply -f "$PROJECT_ROOT/k8s/base/persistence.yaml"
kubectl apply -f "$PROJECT_ROOT/k8s/base/data-persistence.yaml"

# Deploy Dask or PySpark
case $TARGET in
    dask)
        log_info "Deploying Dask with HPA..."
        kubectl apply -f "$PROJECT_ROOT/k8s/dask/deployment.yaml"
        kubectl apply -f "$PROJECT_ROOT/k8s/dask/hpa.yaml"
        log_info "Dask deployment complete!"
        log_info "To check HPA status: kubectl get hpa -n tpch-benchmark"
        log_info "To check pods: kubectl get pods -n tpch-benchmark"
        ;;
    pyspark)
        log_info "Deploying PySpark with HPA..."
        kubectl apply -f "$PROJECT_ROOT/k8s/pyspark/deployment.yaml"
        kubectl apply -f "$PROJECT_ROOT/k8s/pyspark/hpa.yaml"
        log_info "PySpark deployment complete!"
        log_info "To check HPA status: kubectl get hpa -n tpch-benchmark"
        log_info "To check pods: kubectl get pods -n tpch-benchmark"
        ;;
    all)
        log_info "Deploying Dask with HPA..."
        kubectl apply -f "$PROJECT_ROOT/k8s/dask/deployment.yaml"
        kubectl apply -f "$PROJECT_ROOT/k8s/dask/hpa.yaml"
        
        log_info "Deploying PySpark with HPA..."
        kubectl apply -f "$PROJECT_ROOT/k8s/pyspark/deployment.yaml"
        kubectl apply -f "$PROJECT_ROOT/k8s/pyspark/hpa.yaml"
        
        log_info "All deployments complete!"
        log_info "To check HPA status: kubectl get hpa -n tpch-benchmark"
        log_info "To check pods: kubectl get pods -n tpch-benchmark"
        ;;
    *)
        log_error "Invalid target: $TARGET. Use 'dask', 'pyspark', or 'all'"
        exit 1
        ;;
esac

log_info "Deployment complete!"
