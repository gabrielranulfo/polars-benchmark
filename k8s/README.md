# Kubernetes HPA (Horizontal Pod Autoscaler) - Documentação

## Visão Geral

Este documento descreve como executar benchmarks TPC-H com **autoscaling automático** usando Kubernetes HPA (Horizontal Pod Autoscaler) para Dask e PySpark.

## Pré-requisitos

### Obrigatório
- **Kubernetes cluster** (v1.19+)
  - kubectl instalado e configurado
  - Acesso ao cluster
- **Metrics Server** instalado no cluster (necessário para HPA)
  - Docker ou container runtime
- **Python 3.11+** e requirements do projeto instalados

### Recomendado
- **kubectx** para gerenciar contextos
- **k9s** para UI do Kubernetes
- Mínimo 16GB RAM no cluster para ambos os frameworks
- **PersistentVolume** para persistência de resultados (veja seção de Persistência)

## Persistência de Dados

### Arquivos Gerados Durante Execução

Os benchmarks geram três arquivos de monitoramento:

1. **`output/run/timings.csv`** - Timings de execução de cada query
2. **`output/run/memory_monitor.csv`** - Monitoramento de memória (CPU/MEM a cada intervalo)
3. **`output/run/cpu_monitor.csv`** - Monitoramento de CPU detalhado

### PersistentVolume Configuration

Para que os dados **não sejam perdidos** quando os pods terminarem:

```bash
# 1. O arquivo k8s/base/persistence.yaml configura:
kubectl apply -f k8s/base/persistence.yaml

# 2. Isso cria:
# - PersistentVolume (PV): /data/tpch-benchmark/output no node
# - PersistentVolumeClaim (PVC): tpch-output-pvc para os pods usarem
```

Os pods montam automaticamente esse volume em `/root/polars-benchmark/output`.

> **⚠️ Nota sobre Storage:** 
> - A configuração padrão usa `hostPath` (armazenamento local do node)
> - Para **produção**, considere usar:
>   - **NFS**: Compartilhamento entre nodes
>   - **Cloud Storage**: EBS (AWS), PD (GCP), AzureDisk
>   - **Ceph/Rook**: Armazenamento distribuído
> - Para **desenvolvimento**, `hostPath` é adequado

### Recuperar Resultados

```bash
# Extrair arquivos do cluster para local
make k8s-extract-results

# Ou com caminho customizado
./scripts/k8s/extract-results.sh /tmp/tpch-results

# Arquivos salvos em: output/k8s-results/
# - timings.csv
# - memory_monitor.csv
# - cpu_monitor.csv
```

### Visualizar Resultados

```bash
# Abrir o arquivo localmente
cat output/k8s-results/timings.csv

# Ou usar ferramentas de análise
# - Excel/Google Sheets
# - pandas: pd.read_csv('output/k8s-results/timings.csv')
# - R: read.csv('output/k8s-results/timings.csv')
```

## Estrutura de Diretórios

```
k8s/
├── base/              # Configurações compartilhadas
│   ├── namespace.yaml # Namespace tpch-benchmark
│   └── rbac.yaml      # ServiceAccount e RBAC
├── dask/              # Configurações do Dask
│   ├── deployment.yaml
│   └── hpa.yaml       # HPA para workers
└── pyspark/           # Configurações do PySpark
    ├── deployment.yaml
    └── hpa.yaml       # HPA para workers
docker/
├── Dockerfile.dask    # Imagem otimizada para Dask
└── Dockerfile.pyspark # Imagem otimizada para PySpark
scripts/k8s/
├── deploy.sh          # Deploy para o cluster
├── monitor-hpa.sh     # Monitorar HPA
├── load-test.sh       # Teste de carga
└── cleanup.sh         # Limpeza de recursos
```

## Instalação e Configuração

### 1. Build de Imagens Docker

```bash
# Dask
docker build -t gabrielranulfo/tpch-benchmark:dask-latest -f docker/Dockerfile.dask .

# PySpark
docker build -t gabrielranulfo/tpch-benchmark:pyspark-latest -f docker/Dockerfile.pyspark .

# Push para Docker Hub
docker push gabrielranulfo/tpch-benchmark:dask-latest
docker push gabrielranulfo/tpch-benchmark:pyspark-latest
```

### 2. Preparar o Cluster

```bash
# Verificar conexão
kubectl cluster-info

# Verificar metrics-server
kubectl get deployment -n kube-system metrics-server

# Se não existir, será instalado automaticamente pelo script deploy.sh
```

## Deployment

### Deploy Automático

```bash
# Deploy Dask com HPA
./scripts/k8s/deploy.sh dask

# Deploy PySpark com HPA
./scripts/k8s/deploy.sh pyspark

# Deploy ambos
./scripts/k8s/deploy.sh all
```

### Deploy Manual

```bash
# 1. Criar namespace e RBAC
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/rbac.yaml

# 2. Deploy Dask
kubectl apply -f k8s/dask/deployment.yaml
kubectl apply -f k8s/dask/hpa.yaml

# 3. Deploy PySpark
kubectl apply -f k8s/pyspark/deployment.yaml
kubectl apply -f k8s/pyspark/hpa.yaml
```

## Monitoramento

### Status do Cluster

```bash
# Ver pods
kubectl get pods -n tpch-benchmark

# Ver HPAs
kubectl get hpa -n tpch-benchmark -o wide

# Detalhes do HPA
kubectl describe hpa -n tpch-benchmark dask-worker-hpa
```

### Monitorar em Tempo Real

```bash
# Monitor Dask
./scripts/k8s/monitor-hpa.sh dask

# Monitor PySpark
./scripts/k8s/monitor-hpa.sh pyspark

# Monitor ambos (com intervalo customizado)
./scripts/k8s/monitor-hpa.sh all 10
```

### Logs

```bash
# Logs de um pod
kubectl logs -n tpch-benchmark <pod-name>

# Logs em tempo real
kubectl logs -f -n tpch-benchmark <pod-name>

# Logs de todos os workers
kubectl logs -n tpch-benchmark -l app=dask-benchmark,component=worker --all-containers=true
```

### Métricas

```bash
# CPU e memória dos pods
kubectl top pods -n tpch-benchmark

# CPU e memória dos nodes
kubectl top nodes

# Métricas detalhadas
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/tpch-benchmark/pods
```

## Teste de Carga

### Executar Load Test

```bash
# Teste Dask (5 minutos)
./scripts/k8s/load-test.sh dask 300

# Teste PySpark (10 minutos)
./scripts/k8s/load-test.sh pyspark 600

# Teste customizado (em outro terminal)
./scripts/k8s/monitor-hpa.sh dask  # Monitor durante o teste
```

### Observar Autoscaling

Durante o load test, observe:

```bash
# Ver aumento de pods
kubectl get pods -n tpch-benchmark -w

# Ver HPA reagindo
kubectl get hpa -n tpch-benchmark -w
```

## Configuração HPA

### Dask Worker HPA

**Arquivo:** `k8s/dask/hpa.yaml`

- **Min Replicas:** 2
- **Max Replicas:** 10
- **Triggers:**
  - CPU > 70%
  - Memory > 80%
- **Scale Up:** Agressivo (100% a cada 15s)
- **Scale Down:** Conservador (50% a cada 60s)

### PySpark Executor HPA

**Arquivo:** `k8s/pyspark/hpa.yaml`

- **Min Replicas:** 2
- **Max Replicas:** 10
- **Triggers:**
  - CPU > 75%
  - Memory > 80%
- **Scale Up:** Agressivo (100% a cada 15s)
- **Scale Down:** Conservador (50% a cada 60s)

### Customizar HPA

Para ajustar os limites de CPU/memória, edite `hpa.yaml`:

```yaml
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      type: Utilization
      averageUtilization: 70  # Alterar este valor
```

## Resource Requests e Limits

### Dask

**Scheduler:**
- Requests: 1 CPU, 2Gi RAM
- Limits: 2 CPU, 4Gi RAM

**Workers:**
- Requests: 2 CPU, 4Gi RAM
- Limits: 4 CPU, 8Gi RAM

### PySpark

**Master:**
- Requests: 1 CPU, 2Gi RAM
- Limits: 2 CPU, 4Gi RAM

**Executors:**
- Requests: 2 CPU, 4Gi RAM
- Limits: 4 CPU, 8Gi RAM

**Driver:**
- Requests: 1 CPU, 4Gi RAM
- Limits: 2 CPU, 8Gi RAM

## Troubleshooting

### HPA não está escalando

```bash
# Verificar status do metrics-server
kubectl get deployment -n kube-system metrics-server

# Ver logs do HPA controller
kubectl logs -n kube-system deployment/kube-controller-manager | grep -i horizontal

# Checar status detalhado do HPA
kubectl describe hpa -n tpch-benchmark dask-worker-hpa
```

### Pods em estado Pending

```bash
# Ver eventos
kubectl describe pods -n tpch-benchmark

# Ver recursos disponíveis
kubectl top nodes

# Ver requests vs disponível
kubectl describe nodes
```

### Imagem não encontrada

```bash
# Verificar imagens disponíveis no node
kubectl debug node/<node-name> -it --image=ubuntu

# Pull da imagem manualmente
docker pull gabrielranulfo/tpch-benchmark:dask-latest
```

## Limpeza

### Remove Deployments

```bash
# Remover Dask
./scripts/k8s/cleanup.sh dask

# Remover PySpark
./scripts/k8s/cleanup.sh pyspark

# Remover tudo
./scripts/k8s/cleanup.sh all
```

### Remove Manualmente

```bash
# Remove Dask
kubectl delete -f k8s/dask/
kubectl delete -f k8s/base/

# Remove PySpark
kubectl delete -f k8s/pyspark/
kubectl delete -f k8s/base/

# Remove namespace
kubectl delete namespace tpch-benchmark
```

## Boas Práticas

### Segurança

- [ ] Use private image registry
- [ ] Configure Network Policies
- [ ] Implemente Pod Security Policies
- [ ] Use secrets para credenciais

### Performance

- [ ] Monitore continuamente
- [ ] Ajuste requests/limits com base em métricas
- [ ] Use nodeSelector/affinity para placement
- [ ] Configure resource quotas por namespace

### Observabilidade

- [ ] Configure logging (ELK, Loki, etc.)
- [ ] Configure monitoring (Prometheus, etc.)
- [ ] Configure alertas para HPA events

## Exemplos de Uso

### Deploy Dask com HPA no GKE

```bash
# Usar scripts
./scripts/k8s/deploy.sh dask

# Monitorar
./scripts/k8s/monitor-hpa.sh dask

# Load test
./scripts/k8s/load-test.sh dask 600
```

### Deploy PySpark no EKS

```bash
# Deploy
./scripts/k8s/deploy.sh pyspark

# Monitorar escalamento
watch -n 2 'kubectl get hpa -n tpch-benchmark'

# Verificar logs
kubectl logs -f -n tpch-benchmark deployment/pyspark-driver
```

## Referências

- [Kubernetes HPA Docs](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Metrics Server](https://github.com/kubernetes-sigs/metrics-server)
- [Dask Kubernetes](https://kubernetes.dask.org/)
- [PySpark on Kubernetes](https://spark.apache.org/docs/latest/running-on-kubernetes.html)

## Contato e Suporte

Para dúvidas ou problemas, abra uma issue no repositório.
