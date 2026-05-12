#!/bin/bash
# Load test script for HPA - simulates workload to trigger autoscaling
# Usage: ./scripts/k8s/load-test.sh [dask|pyspark] [duration_seconds]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET="${1:-dask}"
DURATION="${2:-300}"  # Default 5 minutes

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

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found. Please install kubectl."
    exit 1
fi

log_section "TPC-H Benchmark Load Test"
log_info "Target: $TARGET"
log_info "Duration: ${DURATION}s"

case $TARGET in
    dask)
        log_info "Creating load test pod for Dask..."
        cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: dask-load-test
  namespace: tpch-benchmark
  labels:
    app: dask-benchmark
    component: load-test
spec:
  serviceAccountName: dask-sa
  containers:
  - name: dask-load-test
    image: gabrielranulfo/tpch-benchmark:dask-latest
    imagePullPolicy: IfNotPresent
    command: ["python"]
    args:
    - "-c"
    - |
      import dask.dataframe as dd
      from dask.distributed import Client
      import time

      # Connect to Dask cluster
      client = Client('dask-scheduler:8786')
      
      # Create a large synthetic dataframe
      print("Creating synthetic data...")
      df = dd.from_delayed(
          [dask.delayed(lambda: __import__('pandas').DataFrame({
              'x': range(100000),
              'y': range(100000)
          })) for _ in range(4)],
          meta={'x': 'i8', 'y': 'i8'}
      )
      
      # Perform computations
      print("Starting computations...")
      start = time.time()
      result = df.groupby('x').y.sum().compute()
      elapsed = time.time() - start
      
      print(f"Computation completed in {elapsed:.2f}s")
      client.close()
    resources:
      requests:
        cpu: "1"
        memory: "2Gi"
      limits:
        cpu: "2"
        memory: "4Gi"
  restartPolicy: Never
EOF
        ;;
    pyspark)
        log_info "Creating load test pod for PySpark..."
        cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: pyspark-load-test
  namespace: tpch-benchmark
  labels:
    app: pyspark-benchmark
    component: load-test
spec:
  serviceAccountName: pyspark-sa
  containers:
  - name: pyspark-load-test
    image: gabrielranulfo/tpch-benchmark:pyspark-latest
    imagePullPolicy: IfNotPresent
    command: ["python"]
    args:
    - "-c"
    - |
      from pyspark.sql import SparkSession
      import time

      # Create Spark session
      spark = SparkSession.builder \
          .appName("tpch-load-test") \
          .master("spark://pyspark-master:7077") \
          .config("spark.executor.instances", "4") \
          .config("spark.executor.cores", "2") \
          .config("spark.executor.memory", "4g") \
          .getOrCreate()

      # Create a large synthetic dataframe
      print("Creating synthetic data...")
      df = spark.range(0, 1000000)

      # Perform computations
      print("Starting computations...")
      start = time.time()
      result = df.groupBy("id").count().collect()
      elapsed = time.time() - start

      print(f"Computation completed in {elapsed:.2f}s")
      spark.stop()
    resources:
      requests:
        cpu: "1"
        memory: "2Gi"
      limits:
        cpu: "2"
        memory: "4Gi"
  restartPolicy: Never
EOF
        ;;
    *)
        log_error "Invalid target: $TARGET. Use 'dask' or 'pyspark'"
        exit 1
        ;;
esac

log_info "Load test pod created. Monitoring status..."

# Wait for pod to complete or timeout
timeout "$DURATION" kubectl wait --for=condition=Ready=False pod \
    -n tpch-benchmark -l "app=${TARGET}-benchmark,component=load-test" \
    --timeout="${DURATION}s" || true

log_info "Load test complete. Checking logs..."
kubectl logs -n tpch-benchmark -l "app=${TARGET}-benchmark,component=load-test" --all-containers=true

log_info "Deleting load test pod..."
kubectl delete pod -n tpch-benchmark -l "app=${TARGET}-benchmark,component=load-test" --ignore-not-found=true

log_section "Load test completed"
log_info "Monitor HPA status with: ./scripts/k8s/monitor-hpa.sh $TARGET"
