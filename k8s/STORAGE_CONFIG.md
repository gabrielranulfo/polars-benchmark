# Configuração de Storage para Benchmarks

## Tipos de Storage

### 1. HostPath (Padrão - Desenvolvimento)

**Arquivo:** `k8s/base/persistence.yaml`

```yaml
spec:
  hostPath:
    path: /data/tpch-benchmark/output
```

**Vantagens:**
- Simples e sem dependências
- Rápido para desenvolvimento local
- Não requer configuração extra

**Desvantagens:**
- ❌ Dados perdidos se o node morrer
- ❌ Não compartilha entre nodes (single-node only)
- ❌ Inadequado para produção

**Quando usar:**
- Desenvolvimento local
- Testes rápidos
- Clusters single-node (minikube, kind)

---

### 2. NFS (Network File System)

Ideal para compartilhamento entre múltiplos nodes.

```yaml
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: tpch-output-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteMany  # Múltiplos nodes
  nfs:
    server: 192.168.1.100  # IP do servidor NFS
    path: "/exports/tpch-benchmark"
  persistentVolumeReclaimPolicy: Retain

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tpch-output-pvc
  namespace: tpch-benchmark
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
```

**Setup:**

```bash
# 1. No servidor NFS:
sudo mkdir -p /exports/tpch-benchmark
sudo chmod 777 /exports/tpch-benchmark
echo "/exports/tpch-benchmark *(rw,sync,no_subtree_check)" | sudo tee -a /etc/exports
sudo exportfs -a

# 2. No cluster Kubernetes:
# Instalar NFS provisioner
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner
helm install nfs-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --set nfs.server=192.168.1.100 \
  --set nfs.path=/exports/tpch-benchmark

# 3. Aplicar manifest
kubectl apply -f persistence-nfs.yaml
```

---

### 3. AWS EBS (Elastic Block Store)

Melhor para AWS.

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: tpch-output-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  awsElasticBlockStore:
    volumeID: vol-1234567890abcdef0  # ID do EBS
    fsType: ext4

---
apiVersion: v1
kind: StorageClass
metadata:
  name: tpch-ebs
provisioner: ebs.csi.aws.com
parameters:
  type: gp3  # gp2, gp3, io1, io2
  iops: "3000"
  throughput: "125"

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tpch-output-pvc
  namespace: tpch-benchmark
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: tpch-ebs
  resources:
    requests:
      storage: 10Gi
```

**Setup:**

```bash
# 1. Verificar EBS CSI Driver
kubectl get daemonset -n kube-system ebs-csi-node

# 2. Se não existir, instalar
helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
  -n kube-system

# 3. Aplicar manifest
kubectl apply -f persistence-ebs.yaml
```

---

### 4. GCP Persistent Disk

Melhor para GKE.

```yaml
apiVersion: v1
kind: StorageClass
metadata:
  name: tpch-gcp-pd
provisioner: pd.csi.storage.gke.io
parameters:
  type: pd-ssd  # ou pd-standard
  replication-type: regional-pd

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tpch-output-pvc
  namespace: tpch-benchmark
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: tpch-gcp-pd
  resources:
    requests:
      storage: 10Gi
```

---

### 5. Azure Disk

Melhor para AKS.

```yaml
apiVersion: v1
kind: StorageClass
metadata:
  name: tpch-azure
provisioner: disk.csi.azure.com
parameters:
  skuname: Standard_LRS  # ou Premium_LRS

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tpch-output-pvc
  namespace: tpch-benchmark
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: tpch-azure
  resources:
    requests:
      storage: 10Gi
```

---

### 6. Ceph/Rook (Armazenamento Distribuído)

Ideal para clusters multinode sem cloud provider.

```yaml
apiVersion: v1
kind: StorageClass
metadata:
  name: tpch-ceph
provisioner: rook-ceph.rbd.csi.ceph.com
parameters:
  clusterID: rook-ceph
  pool: replicapool
  imageFormat: "2"
  imageFeatures: layering

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tpch-output-pvc
  namespace: tpch-benchmark
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: tpch-ceph
  resources:
    requests:
      storage: 10Gi
```

---

## Comparação de Opções

| Feature | HostPath | NFS | EBS | GCP PD | Azure | Ceph |
|---------|----------|-----|-----|--------|-------|------|
| **Multi-Node** | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Durabilidade** | ⚠️ Local | ⚠️ Rede | ✅ Alta | ✅ Alta | ✅ Alta | ✅ Alta |
| **Performance** | ✅ Rápido | ⚠️ Rede | ✅ Rápido | ✅ Rápido | ✅ Rápido | ✅ Rápido |
| **Setup** | ✅ Simples | ⚠️ Médio | ⚠️ Médio | ✅ Fácil | ✅ Fácil | ⚠️ Complexo |
| **Custo** | ✅ Grátis | ✅ Baixo | ⚠️ Médio | ⚠️ Médio | ⚠️ Médio | ✅ Baixo |
| **Prod Ready** | ❌ Não | ✅ Sim | ✅ Sim | ✅ Sim | ✅ Sim | ✅ Sim |

---

## Como Customizar

### Mudar para NFS

```bash
# 1. Criar arquivo: k8s/base/persistence-nfs.yaml
# (Usar template acima)

# 2. Atualizar scripts/k8s/deploy.sh
# Mudar:
kubectl apply -f "$PROJECT_ROOT/k8s/base/persistence.yaml"
# Para:
kubectl apply -f "$PROJECT_ROOT/k8s/base/persistence-nfs.yaml"

# 3. Deploy
./scripts/k8s/deploy.sh all
```

### Mudar para EBS (AWS)

```bash
# 1. Criar arquivo: k8s/base/persistence-ebs.yaml

# 2. Instalar EBS CSI Driver (uma vez):
helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
  -n kube-system

# 3. Atualizar scripts/k8s/deploy.sh
# Mudar:
kubectl apply -f "$PROJECT_ROOT/k8s/base/persistence.yaml"
# Para:
kubectl apply -f "$PROJECT_ROOT/k8s/base/persistence-ebs.yaml"

# 4. Deploy
./scripts/k8s/deploy.sh all
```

---

## Recuperando Dados

### Com HostPath

```bash
# Acessar node SSH
ssh user@node-ip

# Ver dados
ls -la /data/tpch-benchmark/output/

# Copiar para local
scp -r user@node-ip:/data/tpch-benchmark/output ./
```

### Com NFS

```bash
# Via kubectl cp (recomendado)
make k8s-extract-results

# Ou acessar NFS diretamente
mount -t nfs 192.168.1.100:/exports/tpch-benchmark /mnt/nfs
ls /mnt/nfs/run/
```

### Com Cloud Storage

```bash
# Via kubectl cp (igual para todos)
make k8s-extract-results
```

---

## Boas Práticas

1. **Desenvolvimento**: HostPath é suficiente
2. **Produção**: Use NFS, EBS, GCP PD ou Azure (com replicação)
3. **Multi-Region**: Considere Ceph ou Object Storage (S3, GCS)
4. **Backup**: Sempre tenha backup dos dados importantes
5. **Monitoring**: Configure alertas para espaço em disco cheio

---

## Exemplos Completos

### Setup com NFS

```bash
# 1. Servidor NFS (192.168.1.100)
sudo mkdir -p /exports/tpch
sudo chmod 777 /exports/tpch
echo "/exports/tpch *(rw,sync)" | sudo tee -a /etc/exports
sudo exportfs -a

# 2. Cluster
cat > k8s/base/persistence-nfs.yaml <<EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: tpch-output-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteMany
  nfs:
    server: 192.168.1.100
    path: "/exports/tpch"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tpch-output-pvc
  namespace: tpch-benchmark
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
EOF

# 3. Deploy
make k8s-deploy-all

# 4. Verificar
kubectl get pv,pvc -n tpch-benchmark

# 5. Extrair resultados
make k8s-extract-results
```

---

## Troubleshooting

### PVC em Pending

```bash
kubectl describe pvc tpch-output-pvc -n tpch-benchmark

# Solução: verificar PV disponível
kubectl get pv
```

### NFS Mount Failed

```bash
# Verificar conectividade
kubectl run -it --rm debug --image=ubuntu --restart=Never -- \
  apt-get update && apt-get install -y nfs-common && \
  showmount -e 192.168.1.100
```

### Espaço em Disco Cheio

```bash
# Aumentar tamanho do PVC
kubectl patch pvc tpch-output-pvc -n tpch-benchmark \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```
