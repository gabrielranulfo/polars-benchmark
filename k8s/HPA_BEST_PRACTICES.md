# HPA Best Practices e Notas Técnicas

## Conceitos Fundamentais

### Horizontal Pod Autoscaler (HPA)

O HPA automaticamente escala o número de pods baseado em métricas:
- **CPU Utilization**: Porcentagem de CPU sendo usada vs. requested
- **Memory Utilization**: Porcentagem de memória sendo usada vs. requested
- **Custom Metrics**: Métricas customizadas via Prometheus, etc.

## Requisitos Obrigatórios

### 1. Metrics Server

**Essencial para HPA funcionar**

```bash
# Instalar
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verificar
kubectl get deployment -n kube-system metrics-server
kubectl get apiservice v1beta1.metrics.k8s.io -o yaml
```

### 2. Resource Requests e Limits

**SEM REQUESTS, HPA NÃO FUNCIONA**

```yaml
resources:
  requests:
    cpu: "2"           # Obrigatório para HPA baseado em CPU
    memory: "4Gi"      # Obrigatório para HPA baseado em memória
  limits:
    cpu: "4"           # Opcional, mas recomendado
    memory: "8Gi"      # Opcional, mas recomendado
```

### 3. Métricas Estáveis

HPA precisa de pelo menos 15-30 segundos de dados antes de escalar:
- Default: 15 segundos entre decisões
- Scale-up: Pode ser mais agressivo (15s intervals)
- Scale-down: Mais conservador (300s stabilization window)

## Configuração do HPA

### Threshold de CPU (Dask)

```yaml
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      type: Utilization
      averageUtilization: 70  # Scale quando avg CPU > 70%
```

**Cálculo:**
```
Pod Usage: 1400m (1.4 CPU)
Request: 2000m (2 CPU)
Utilization: (1400/2000) * 100 = 70%
→ HPA triggera
```

### Threshold de Memória

```yaml
metrics:
- type: Resource
  resource:
    name: memory
    target:
      type: Utilization
      averageUtilization: 80  # Scale quando avg Memory > 80%
```

### Scale-Up Policy (Agressivo)

```yaml
behavior:
  scaleUp:
    stabilizationWindowSeconds: 0   # Sem espera
    policies:
    - type: Percent
      value: 100                    # Dobra os pods
      periodSeconds: 15             # A cada 15s
    - type: Pods
      value: 2                       # OU adiciona 2 pods
      periodSeconds: 15
    selectPolicy: Max               # Usa o mais agressivo
```

### Scale-Down Policy (Conservador)

```yaml
behavior:
  scaleDown:
    stabilizationWindowSeconds: 300  # Espera 5 minutos
    policies:
    - type: Percent
      value: 50                      # Remove 50% dos pods
      periodSeconds: 60
    - type: Pods
      value: 1                       # OU remove 1 pod
      periodSeconds: 60
    selectPolicy: Min                # Usa o mais conservador
```

## Debugging e Troubleshooting

### Verificar Status HPA

```bash
# Listar HPAs
kubectl get hpa -n tpch-benchmark

# Output esperado:
# NAME                 REFERENCE                       TARGETS           MINPODS MAXPODS REPLICAS AGE
# dask-worker-hpa      Deployment/dask-worker          23%/70%, 45%/80%  2       10      3        5m
#
# - 23% CPU (threshold 70%) → NÃO escala
# - 45% memory (threshold 80%) → NÃO escala
# - 3 replicas ativos (min 2, max 10)

# Ver detalhes completos
kubectl describe hpa -n tpch-benchmark dask-worker-hpa

# Output esperado inclui:
# - Current Replicas: 3
# - Desired Replicas: 3
# - Conditions: ScalingActive (True), ResourceMetricsFound (True)
# - Events: Indicam decisões de escalamento
```

### Problema: HPA não está escalando

**Checklist:**

1. **Metrics-server instalado?**
   ```bash
   kubectl get deployment -n kube-system metrics-server
   kubectl logs -n kube-system deployment/metrics-server
   ```

2. **Resources definidos?**
   ```bash
   kubectl get pods -n tpch-benchmark -o yaml | grep -A5 "resources:"
   # Deve ter "requests:" com cpu e memory
   ```

3. **Métricas disponíveis?**
   ```bash
   kubectl top pods -n tpch-benchmark
   # Deve mostrar CPU e MEMORY
   
   # Se não funciona, checar raw metrics:
   kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/tpch-benchmark/pods
   ```

4. **HPA configurado corretamente?**
   ```bash
   kubectl get hpa -n tpch-benchmark dask-worker-hpa -o yaml | grep -A10 "metrics:"
   ```

5. **Carga de trabalho?**
   ```bash
   # Se pods têm baixo uso, HPA não vai escalar!
   kubectl top pods -n tpch-benchmark -l app=dask-benchmark,component=worker
   ```

### Problema: Pods em estado Pending

```bash
# Descrever pod para ver por quê
kubectl describe pod -n tpch-benchmark <pod-name>

# Causas comuns:
# - Insufficient CPU/Memory nos nodes
# - NodeSelector/Affinity não matching
# - PVC não disponível

# Verificar recursos do node
kubectl describe nodes
kubectl top nodes
```

### Problema: HPA criando muitos pods rapidamente

**Usar stabilization window para desacelerar:**

```yaml
behavior:
  scaleUp:
    stabilizationWindowSeconds: 30   # Esperar 30s antes de nova decisão
```

## Fórmula de Escalamento

### Cálculo de Replicas Desejadas

```
desiredReplicas = ceil[currentReplicas * (currentMetric / targetMetric)]

Exemplo:
- Current: 2 replicas
- Current CPU avg: 90%
- Target CPU: 70%

desiredReplicas = ceil[2 * (90 / 70)] = ceil[2.57] = 3
→ Escala para 3 replicas
```

## Otimização por Framework

### Dask

**Características:**
- Workers são stateless (podem ser adicionados/removidos facilmente)
- Distribuem trabalho via scheduler
- Scale-up deve ser rápido, scale-down pode ser lento

**Recomendação:**
```yaml
minReplicas: 2        # Sempre ter reserve
maxReplicas: 10       # Limite para evitar custos
thresholds:
  cpu: 70%            # Escala com menos uso (mais sensível)
  memory: 80%         # Mais tolerante à memória
```

### PySpark

**Características:**
- Executors podem ter estado local
- Mais pesado que Dask para escalar
- Mais sensível a perda de dados durante scale-down

**Recomendação:**
```yaml
minReplicas: 2        # Sempre ter reserve
maxReplicas: 10       # Limite conservador
thresholds:
  cpu: 75%            # Menos sensível que Dask
  memory: 80%
scaleDownWindow: 600  # Esperar mais antes de descer
```

## Integração com CI/CD

### Teste de HPA com Load Test

```bash
# 1. Deploy
make k8s-deploy-dask

# 2. Esperar estabilizar (30s)
sleep 30

# 3. Monitorar em background
make k8s-monitor-dask &

# 4. Executar load test
make k8s-load-test-dask

# 5. Observar escalamento
# → Pods devem aumentar durante teste
# → Pods devem diminuir após teste (lentamente)
```

## Monitoramento em Produção

### Prometheus Queries para HPA

```promql
# Taxa de escalamento (pods/minute)
rate(kube_deployment_status_replicas[5m])

# Utilização de CPU
sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) / 
sum(kube_pod_container_resource_requests_cpu_cores) by (pod)

# Utilização de Memória
sum(container_memory_working_set_bytes) by (pod) / 
sum(kube_pod_container_resource_requests_memory_bytes) by (pod)

# HPA Events
ALERTS{alertname="HorizontalPodAutoscalerMaxedOut"}
```

### Alertas Recomendados

```yaml
# HPA maxed out (sempre no máximo)
expr: kube_hpa_status_current_replicas == kube_hpa_status_desired_replicas 
      and kube_hpa_status_desired_replicas == kube_hpa_spec_max_replicas

# Pods em Pending (recursos insuficientes)
expr: kube_pod_status_phase{phase="Pending"} > 0

# Metrics Server não respondendo
expr: up{job="metrics-server"} == 0
```

## Casos de Uso e Exemplos

### Caso 1: Benchmark TPC-H em Dask

```bash
# Setup
make k8s-deploy-dask
sleep 30

# Monitorar
make k8s-monitor-dask &

# Executar benchmark
kubectl exec -it -n tpch-benchmark deployment/dask-worker -- \
  python -m queries.dask

# Esperado:
# - Começa com 2 replicas
# - CPU e memory aumentam
# - HPA escala para 3-4 replicas em ~1min
# - Após query terminar, reduz lentamente
```

### Caso 2: Teste de Limite de Escalamento

```bash
# Deploy com limite menor
kubectl set env deployment/dask-worker -n tpch-benchmark \
  DASK_WORKER_MAX_MEMORY=2Gi

# Executar carga pesada
make k8s-load-test-dask

# HPA deve escalar para max replicas (10)
# Se não conseguir atender, vai gerar alertas
```

## Referências

- [Kubernetes HPA Official Docs](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Metrics Server](https://github.com/kubernetes-sigs/metrics-server)
- [HPA Behavior v2](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#configurable-scaling-behavior)
- [Dask Kubernetes](https://kubernetes.dask.org/)
- [Spark on Kubernetes](https://spark.apache.org/docs/latest/running-on-kubernetes.html)

## Checklist de Deploy

- [ ] Metrics-server instalado e funcional
- [ ] Namespace criado
- [ ] RBAC configurado
- [ ] Resources (requests/limits) definidos
- [ ] HPA configurado com thresholds apropriados
- [ ] Load test executado e observado
- [ ] Monitoramento + alertas configurados
- [ ] Documentação atualizada
