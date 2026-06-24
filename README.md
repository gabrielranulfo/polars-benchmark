# TPC-H Benchmark com Elasticidade (Dask + PySpark)

Este repositório é um fork do [pola-rs/tpch](https://github.com/pola-rs/tpch) adaptado para avaliar **elasticidade (auto-scaling)** em processamento distribuído de dados com Dask e PySpark em Kubernetes.

O benchmark executa as 22 queries do **TPC-H** (padrão da indústria para decisão de suporte) em múltiplos frameworks:

| Framework | Modo Local | Modo Distribuído |
|-----------|-----------|------------------|
| **Polars** | ✅ `lf.collect()` | ❌ |
| **pandas** | ✅ | ❌ |
| **DuckDB** | ✅ | ❌ |
| **Modin** | ✅ Ray local | ❌ |
| **Dask** | ✅ `scheduler="threads"` | ✅ `Client(tcp://...)` + HPA |
| **PySpark** | ✅ `master="local[*]"` | ✅ `master=spark://...` + HPA |

---

## Índice

- [Pré-requisitos](#pré-requisitos)
- [Setup Local](#setup-local)
- [Gerar Dados TPC-H](#gerar-dados-tpc-h)
- [Executar Benchmarks](#executar-benchmarks)
  - [Selecionar Bibliotecas](#selecionar-bibliotecas)
  - [Modo Distribuído (Dask)](#modo-distribuído-dask)
  - [Modo Distribuído (PySpark)](#modo-distribuído-pyspark)
- [Monitoramento](#monitoramento)
- [Docker](#docker)
- [Kubernetes](#kubernetes)
  - [Deploy Completo](#deploy-completo)
  - [HPA (Horizontal Pod Autoscaler)](#hpa-horizontal-pod-autoscaler)
  - [Teste de Carga](#teste-de-carga)
  - [Extrair Resultados](#extrair-resultados)
  - [Limpeza](#limpeza)
- [Configurações por Ambiente](#configurações-por-ambiente)

---

## Pré-requisitos

- **Python 3.11+**
- **Make**
- **Docker** (para imagens dos benchmarks)
- **Kubernetes cluster** (v1.19+) com **Metrics Server** (para HPA)
- **kubectl** configurado

---

## Setup Local

```shell
git clone https://github.com/gabrielranulfo/polars-benchmark.git
cd polars-benchmark
git checkout mestrado-elasticidade

# Criar virtualenv e instalar dependências
make .venv
```

---

## Gerar Dados TPC-H

```shell
# Compilar o gerador de dados TPC-H
make -C tpch-dbgen

# Gerar dados (scale factor 1 = ~1GB)
make tables SCALE_FACTOR=1
```

Para gerar datasets maiores: `SCALE_FACTOR=10` (~10GB), `SCALE_FACTOR=100` (~100GB).

### Sincronizar Dados para o Kubernetes

O cluster K8s usa um PVC separado (`tpch-data-pvc`) que monta os dados em `/root/polars-benchmark/data/tables/` dentro dos pods. Para disponibilizar os dados no cluster:

```bash
# Na máquina que gerou os dados, copiar para a máquina do cluster
# (ex: SCP, USB drive, etc.) até o diretório data/tables/ do repositório.

# Já na máquina do cluster, copiar os dados para todos os nós KIND:
./scripts/k8s/copy-data-to-kind.sh [SCALE_FACTOR]
```

### Mudar Escala no Kubernetes

Para executar o benchmark com outro scale factor no cluster:

1. **Gerar os dados** na máquina onde os dados TPC-H são gerados:
   ```bash
   make tables SCALE_FACTOR=10
   ```

2. **Transferir** a pasta `data/tables/scale-10/` para a máquina do cluster K8s.

3. **Copiar para todos os nós KIND** na máquina do cluster:
   ```bash
   ./scripts/k8s/copy-data-to-kind.sh 10
   ```

4. **Configurar o scale factor** nos deployments:
   ```bash
   kubectl set env deployment/pyspark-driver SCALE_FACTOR=10
   kubectl set env deployment/pyspark-master SCALE_FACTOR=10
   kubectl set env deployment/pyspark-worker SCALE_FACTOR=10
   kubectl delete pod -n tpch-benchmark --all
   ```

O código lê `SCALE_FACTOR` (default `1.0` em `settings.py:125`) e monta o path `data/tables/scale-{factor}/` automaticamente.

---

## Executar Benchmarks

```shell
# Executar todas as bibliotecas
./run.sh

# Ou via make diretamente
make run-all               # duckdb + polars + pandas + pyspark + dask
make run-polars            # apenas Polars
make run-pandas            # apenas pandas
make run-duckdb            # apenas DuckDB
make run-dask              # apenas Dask
make run-pyspark           # apenas PySpark
make run-modin             # apenas Modin
```

### Selecionar Bibliotecas

Use a variável `RUN_LIBRARIES` no `run.sh` para escolher quais bibliotecas executar:

```shell
# Apenas Dask e PySpark
RUN_LIBRARIES="dask,pyspark" ./run.sh

# Apenas Polars e DuckDB
RUN_LIBRARIES="polars,duckdb" ./run.sh

# Apenas Dask
RUN_LIBRARIES="dask" ./run.sh
```

### Modo Distribuído (Dask)

Por padrão o Dask roda local (`scheduler="threads"`). Para modo distribuído:

```shell
export RUN_DASK_SCHEDULER="tcp://<scheduler-host>:8786"
./run.sh
# ou apenas Dask:
RUN_DASK_SCHEDULER="tcp://dask-scheduler:8786" RUN_LIBRARIES="dask" ./run.sh
```

Quando configurado com um endereço `tcp://...`, o código cria um `dask.distributed.Client` conectado ao scheduler. Os workers registrados no scheduler recebem as tarefas automaticamente — se o HPA adicionar mais workers, o Dask redistribui a carga.

### Modo Distribuído (PySpark)

Por padrão o PySpark roda local (`master="local[*]"`). Para modo distribuído:

```shell
export RUN_PYSPARK_MASTER="spark://<master-host>:7077"
./run.sh
# ou apenas PySpark:
RUN_PYSPARK_MASTER="spark://pyspark-master:7077" RUN_LIBRARIES="pyspark" ./run.sh
```

Em modo distribuído, o Spark ativa automaticamente o `dynamicAllocation`, que adiciona/remove executors conforme a demanda.

---

## Monitoramento

Durante a execução, três arquivos CSV são gerados em `output/run/`:

| Arquivo | Conteúdo |
|---------|----------|
| `timings.csv` | Duração de cada query (solução, versão, query, tempo, scale factor, PID) |
| `cpu_monitor.csv` | Uso de CPU do processo a cada 500ms |
| `memory_monitor.csv` | Uso de memória do processo a cada 500ms |

O monitoramento é feito por query individual: cada query roda em um subprocesso separado, e os monitores capturam CPU e memória desse processo (e seus filhos) em tempo real.

---

## Docker

As imagens Docker empacotam o código e as dependências para execução em Kubernetes.

```shell
# Build das imagens
make docker-build-dask        # gabrielranulfo/tpch-benchmark:dask-latest
make docker-build-pyspark     # gabrielranulfo/tpch-benchmark:pyspark-latest
make docker-build-all         # ambas

# Push para Docker Hub
make docker-push-dask
make docker-push-pyspark
make docker-push-all
```

As imagens já vêm com o código da branch `mestrado-elasticidade` e podem ser configuradas via variáveis de ambiente no momento do deploy.

---

## Kubernetes

### Deploy Completo

```shell
# Deploy Dask + PySpark com HPA
make k8s-deploy-all

# Ou individualmente
make k8s-deploy-dask
make k8s-deploy-pyspark
```

Isso cria no namespace `tpch-benchmark`:

| Recurso | Dask | PySpark |
|---------|------|---------|
| **Scheduler/Master** | `dask-scheduler` | `pyspark-master` |
| **Workers/Executors** | `dask-worker` (começa com 2) | `pyspark-worker` (começa com 2) |
| **HPA** | `dask-worker-hpa` | `pyspark-worker-hpa` |
| **Persistência (saídas)** | PVC `tpch-output-pvc` | PVC `tpch-output-pvc` |
| **Persistência (dados TPC-H)** | PVC `tpch-data-pvc` | PVC `tpch-data-pvc` |

### Configurar Modo Distribuído no K8s

Os deployments em K8s já incluem essas variáveis nos manifestos YAML (ver `k8s/pyspark/deployment.yaml` e `k8s/dask/deployment.yaml`). Apenas certifique-se de que os dados foram copiados para os nós (veja [Sincronizar Dados para o Kubernetes](#sincronizar-dados-para-o-kubernetes)).

```shell
# Dask — worker conecta ao scheduler
kubectl set env deployment/dask-worker -n tpch-benchmark \
  RUN_DASK_SCHEDULER="tcp://dask-scheduler:8786"

# PySpark — driver conecta ao master
kubectl set env deployment/pyspark-driver -n tpch-benchmark \
  RUN_PYSPARK_MASTER="spark://pyspark-master:7077"
```

### HPA (Horizontal Pod Autoscaler)

O HPA escala automaticamente workers/executors com base em CPU e memória:

| Parâmetro | Dask | PySpark |
|-----------|------|---------|
| **Threshold CPU** | 70% | 75% |
| **Threshold Memória** | 80% | 80% |
| **Min Replicas** | 2 | 2 |
| **Max Replicas** | 10 | 10 |
| **Scale Up** | +100% a cada 15s | +100% a cada 15s |
| **Scale Down** | -50% a cada 60s (espera 5min) | -50% a cada 60s (espera 5min) |

Quando o uso de CPU ou memória ultrapassa o threshold, o HPA aumenta o número de pods. Quando o负载 cai, ele reduz lentamente.

### Executar Benchmarks no Cluster

```shell
# Dask — executa dentro de um worker
kubectl exec -it -n tpch-benchmark deployment/dask-worker -- \
  python -m queries.dask

# PySpark — executa no driver
kubectl exec -it -n tpch-benchmark deployment/pyspark-driver -- \
  python -m queries.pyspark
```

### Teste de Carga

Para simular carga e observar o HPA em ação:

```shell
# Teste de carga Dask (5 minutos)
make k8s-load-test-dask

# Monitorar HPA em tempo real (em outro terminal)
make k8s-monitor-dask
```

### Extrair Resultados

Os resultados das execuções ficam no PVC `tpch-output-pvc` (montado em `/root/polars-benchmark/output/run/`). Para extraí-los:

```shell
# Extrair timings, CPU e memória do cluster
make k8s-extract-results

# Os arquivos são salvos em output/k8s-results/
```

### Monitoramento em Tempo Real

```shell
# Status do cluster
make k8s-status

# Monitorar HPA
make k8s-monitor-dask
make k8s-monitor-pyspark
make k8s-monitor-all
```

### Limpeza

```shell
# Remover recursos do cluster
make k8s-cleanup-dask
make k8s-cleanup-pyspark
make k8s-cleanup-all

# Limpar tudo (incluindo dados locais)
make clean
```

---

## Configurações por Ambiente

### Local (desenvolvimento)

```bash
# .env ou export
export RUN_LIBRARIES="polars,pandas,duckdb"
export RUN_DASK_SCHEDULER="threads"
export RUN_PYSPARK_MASTER="local[*]"
export SCALE_FACTOR=1
```

### Kubernetes (produção/distribuído)

```bash
# Configuração para deploy no K8s
export RUN_LIBRARIES="dask,pyspark"
export RUN_DASK_SCHEDULER="tcp://dask-scheduler:8786"
export RUN_PYSPARK_MASTER="spark://pyspark-master:7077"
export K8S_ENABLED="true"
export SCALE_FACTOR=1
```

### Fluxo entre máquinas

Este repositório é usado em duas máquinas diferentes:

| Máquina | Função | Comandos típicos |
|---------|--------|------------------|
| **Máquina onde os dados TPC-H são gerados** | Geração dos dados, build das imagens Docker, desenvolvimento local | `make tables`, `make docker-build-all`, `make run-polars` |
| **Máquina do cluster K8s** | Execução distribuída no Kubernetes | `make k8s-deploy-all`, `./scripts/k8s/copy-data-to-kind.sh` |

Os dados gerados na primeira máquina devem ser transferidos para a segunda (via SCP, pendrive, etc.) antes de executar `copy-data-to-kind.sh`.

---

## Estrutura do Projeto

```
├── queries/                    # Implementação das 22 queries TPC-H
│   ├── polars/                 #   Polars (local)
│   ├── pandas/                 #   pandas (local)
│   ├── duckdb/                 #   DuckDB (local)
│   ├── modin/                  #   Modin (Ray local)
│   ├── dask/                   #   Dask (local ou distribuído)
│   ├── pyspark/                #   PySpark (local ou distribuído)
│   ├── common_utils.py         #   Orquestração e monitoramento
│   ├── monitor_de_cpu.py       #   Monitor de CPU em tempo real
│   └── monitor_de_memoria.py   #   Monitor de memória em tempo real
├── docker/                     # Dockerfiles para Dask e PySpark
├── k8s/                        # Manifestos Kubernetes
│   ├── base/                   #   Namespace, RBAC, Persistência
│   ├── dask/                   #   Deployment + HPA do Dask
│   └── pyspark/                #   Deployment + HPA do PySpark
├── scripts/k8s/                # Scripts de deploy, monitor, load test
├── settings.py                 # Configurações centralizadas (env vars)
├── run.sh                      # Script de execução principal
└── Makefile                    # Comandos automatizados
