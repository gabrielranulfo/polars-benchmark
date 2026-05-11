#!/bin/bash
# Extract benchmark results from Kubernetes persistent volume
# Usage: ./scripts/k8s/extract-results.sh [local-path]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOCAL_PATH="${1:-${PROJECT_ROOT}/output/k8s-results}"

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section "Extract Benchmark Results"

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found. Please install kubectl."
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace tpch-benchmark &> /dev/null; then
    log_error "Namespace tpch-benchmark not found. Deploy first with: make k8s-deploy-all"
    exit 1
fi

# Create local output directory
mkdir -p "$LOCAL_PATH"
log_info "Results will be saved to: $LOCAL_PATH"

# Get PVC pod (any pod that has the volume mounted)
log_info "Finding pod with mounted PVC..."
POD=$(kubectl get pods -n tpch-benchmark -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$POD" ]; then
    log_error "No pods found in namespace. Deploy first with: make k8s-deploy-all"
    exit 1
fi

log_info "Using pod: $POD"

# Copy files from pod
log_section "Copying benchmark files from pod"

# Copy timings
if kubectl exec -n tpch-benchmark "$POD" -- test -f /root/polars-benchmark/output/run/timings.csv 2>/dev/null; then
    log_info "Copying timings.csv..."
    kubectl cp tpch-benchmark/"$POD":/root/polars-benchmark/output/run/timings.csv "$LOCAL_PATH/timings.csv"
    log_info "✓ timings.csv"
else
    log_info "⊘ timings.csv not found (benchmark not executed yet)"
fi

# Copy memory monitor
if kubectl exec -n tpch-benchmark "$POD" -- test -f /root/polars-benchmark/output/run/memory_monitor.csv 2>/dev/null; then
    log_info "Copying memory_monitor.csv..."
    kubectl cp tpch-benchmark/"$POD":/root/polars-benchmark/output/run/memory_monitor.csv "$LOCAL_PATH/memory_monitor.csv"
    log_info "✓ memory_monitor.csv"
else
    log_info "⊘ memory_monitor.csv not found"
fi

# Copy CPU monitor
if kubectl exec -n tpch-benchmark "$POD" -- test -f /root/polars-benchmark/output/run/cpu_monitor.csv 2>/dev/null; then
    log_info "Copying cpu_monitor.csv..."
    kubectl cp tpch-benchmark/"$POD":/root/polars-benchmark/output/run/cpu_monitor.csv "$LOCAL_PATH/cpu_monitor.csv"
    log_info "✓ cpu_monitor.csv"
else
    log_info "⊘ cpu_monitor.csv not found"
fi

# Show extracted files
log_section "Extracted Files"
if [ -d "$LOCAL_PATH" ]; then
    ls -lh "$LOCAL_PATH"
    echo ""
    log_info "Files successfully extracted!"
else
    log_error "Failed to extract files"
    exit 1
fi

# Show data preview if available
if [ -f "$LOCAL_PATH/timings.csv" ]; then
    log_section "Timings Preview"
    head -5 "$LOCAL_PATH/timings.csv"
    echo "..."
fi

if [ -f "$LOCAL_PATH/memory_monitor.csv" ]; then
    log_section "Memory Monitor Preview"
    head -5 "$LOCAL_PATH/memory_monitor.csv"
    echo "..."
fi

if [ -f "$LOCAL_PATH/cpu_monitor.csv" ]; then
    log_section "CPU Monitor Preview"
    head -5 "$LOCAL_PATH/cpu_monitor.csv"
    echo "..."
fi

log_section "Done!"
log_info "Results available at: $LOCAL_PATH"
