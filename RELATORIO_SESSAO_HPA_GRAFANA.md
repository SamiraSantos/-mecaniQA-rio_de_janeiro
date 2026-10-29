# 📊 Relatório da Sessão: HPA, Observabilidade e Teste de Estresse (MecaniQA Tech)

**Data:** 28/10/2026  
**Projeto:** MecaniQA Tech — Orquestração de Containers e Alta Disponibilidade  
**Papéis Envolvidos:** Scrum Master, Arquiteto de Soluções, Piloto e Copiloto  
**Objetivo do Encontro:** Implementar o HPA (*Horizontal Pod Autoscaler*) no Kubernetes, configurar os 4 alarmes no Grafana e validar a resiliência por meio de teste de estresse com injeção de telemetria IoT.

---

## 📌 1. Board do Scrum Master (Timebox: 10 Minutos)

| 📋 Fatos (O que sabemos com certeza) | ❓ Questões (O que precisávamos investigar) | 💡 Ideias & Decisões (O caminho acordado) |
| :--- | :--- | :--- |
| • A API Java roda com requests de `250m` CPU e `384Mi` RAM, com limits de `1 CPU` e `768Mi` RAM no Deployment.<br>• Picos diários de telemetria ocorrem às 08:00 e 17:00.<br>• O Kubernetes necessita do `metrics-server` ativo para que a API de autoscaling consulte o consumo dos pods. | • Como evitar que picos momentâneos de telemetria de sensores disparem falsos alarmes no Grafana?<br>• Como impedir o comportamento de *flapping* (pods nascendo e morrendo sem parar) no HPA?<br>• Qual métrica do HPA tem precedência quando ambas ultrapassam o limiar? | • Definir um *Pending Period* de 3 a 5 min em todos os alarmes do Grafana.<br>• Estabelecer os thresholds de alerta do Grafana (80% CPU / 85% RAM) ligeiramente acima das metas do HPA (70% CPU / 80% RAM), alertando somente em gargalo real.<br>• Usar `autoscaling/v2` com `behavior`: Scale-Up acelerado (+2 pods a cada 30s) e Scale-Down seguro com `stabilizationWindowSeconds: 300` (5 min). |

---

## 🧠 2. Brainstorm Investigativo (Respostas e Decisões do Arquiteto)

### Pergunta 1: Configuração dos 4 Alarmes no Grafana e Limites Antirruído
**Decisão da Equipe:**
Configuração de 4 alarmes com janela de retenção (*pending period*) estrita para blindagem contra falsos positivos:
1. **CPU da Infraestrutura:** Média dos pods > 80% do request contratado por 5 minutos contínuos.
2. **Memória da Infraestrutura:** *Working set* da memória > 85% do limite por 5 minutos contínuos.
3. **Latência da Aplicação (Customizado):** Percentil 95 (P95) das requisições > 1,0 s por 3 minutos contínuos.
4. **Taxa de Erro HTTP (Customizado):** Respostas de falha (HTTP 5xx) > 5% do tráfego total por 3 minutos contínuos.

> **Justificativa do Arquiteto:** Os limiares de infraestrutura (80% CPU e 85% RAM) foram posicionados deliberadamente acima dos limiares de ativação do HPA (70% e 80%). Dessa forma, o time de operações só é acionado se a carga superar a velocidade de escalonamento ou atingir o teto de 10 réplicas.

---

### Pergunta 2: A Mágica do HPA no Kubernetes (`autoscaling/v2`)
**Decisão da Equipe:**
Implementar o manifesto `hpa.yaml` no namespace `mecaniqa` apontando para o Deployment `api`:
* **Réplicas:** Mínimo de 2 pods (garantia de tolerância a falhas) e máximo de 10 pods.
* **Métricas Alvo:** CPU média em 70% do request ou Memória média em 80% do request. Vale a métrica que demandar o maior número de réplicas.
* **Políticas de Comportamento (`behavior`):**
  * `scaleUp`: Imediato (`stabilizationWindowSeconds: 0`), adicionando até 2 pods a cada 30 segundos.
  * `scaleDown`: Janela de estabilização de 300 segundos (5 minutos) com redução paulatina de 1 pod por minuto.

---

### Pergunta 3: Critérios de Sucesso Absoluto do Teste de Estresse
O teste de estresse simulando sensores IoT será declarado um **sucesso absoluto** se atender cumulativamente aos 5 pilares:

1. **Escalonamento Reativo e Autônomo do HPA:** Ao receber a rajada concorrente dos sensores IoT, o HPA identifica a elevação de CPU > 70% ou RAM > 80% e expande as réplicas de 2 para o volume necessário (até o teto de 10 pods) via `kubectl get hpa -w`.
2. **Resiliência e Ausência de Quedas (Zero OOMKilled):** Durante todo o pico de injeção de carga, a API permanece disponível sem reinicializações abruptas por estouro de memória (*Out-Of-Memory*).
3. **Controle de Latência e Taxa de Erro:** O P95 se mantém sob controle e os erros 5xx normalizam abaixo de 5% à medida que as novas réplicas ficam *Ready* e assumem o tráfego balanceado pelo Service.
4. **Ciclo Completo de Alarmes no Grafana:** Os 4 alarmes transitam de `Normal (OK)` ➔ `Pending` ➔ `Alerting / Firing` durante a sobrecarga máxima, e retornam automaticamente para `OK` após o término do teste.
5. **Scale-Down Gradual sem Flapping:** Ao cessar a carga, o HPA respeita a janela de 5 minutos de cooldown e drena os pods excedentes sem oscilações, retornando ao estado base de 2 réplicas.

---

## 🛠️ 3. Estrutura Técnica dos Artefatos

### 3.1. Manifesto do HPA (`k8s/base/hpa.yaml`)
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: mecaniqa
  labels:
    app: api
    app.kubernetes.io/part-of: mecaniqa-tech
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Pods
          value: 2
          periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 60
```

---

### 3.2. Fórmulas PromQL dos 4 Alarmes no Grafana

| Alarme | Expressão PromQL | Pending | Gravidade |
| :--- | :--- | :--- | :--- |
| **1. CPU Infra** | `(sum(rate(container_cpu_usage_seconds_total{namespace="mecaniqa", container="api"}[2m])) / sum(kube_pod_container_resource_requests{namespace="mecaniqa", container="api", resource="cpu"})) * 100 > 80` | `5m` | `Warning` |
| **2. Memória Infra** | `(sum(container_memory_working_set_bytes{namespace="mecaniqa", container="api"}) / sum(kube_pod_container_resource_limits{namespace="mecaniqa", container="api", resource="memory"})) * 100 > 85` | `5m` | `Critical` |
| **3. Latência P95 (App)** | `histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket{namespace="mecaniqa", uri!~"/actuator.*"}[2m])) by (le)) > 1` | `3m` | `Warning` |
| **4. Taxa de Erro (App)** | `(sum(rate(http_server_requests_seconds_count{namespace="mecaniqa", status=~"5.."}[2m])) / sum(rate(http_server_requests_seconds_count{namespace="mecaniqa"}[2m]))) * 100 > 5` | `3m` | `Critical` |

---

## 🚀 4. Guia de Execução para Piloto e Copiloto

### Passo 1: Validar Métricas no Cluster
Antes de aplicar o HPA, certifique-se de que o `metrics-server` está respondendo:
```bash
kubectl get pods -n kube-system
kubectl top pods -n mecaniqa
```
*(Se estiver em cluster kind local e o metrics-server não estiver instalado, aplique o componente com `--kubelet-insecure-tls`)*.

### Passo 2: Aplicar o HPA via Kustomize
```bash
# Na raiz do repositório
kubectl apply -k k8s/overlays/kind
# Ou aplicar diretamente a base
kubectl apply -k k8s/base

# Conferir o HPA ativo
kubectl get hpa -n mecaniqa
```

### Passo 3: Abrir os Terminais de Monitoramento
Abra terminais divididos para acompanhar o comportamento em tempo real:
```bash
# Terminal 1: Acompanhar o HPA
kubectl get hpa -n mecaniqa -w

# Terminal 2: Acompanhar a criação/destruição dos pods
kubectl get pods -n mecaniqa -l app=api -w
```

### Passo 4: Executar o Teste de Estresse dos Sensores IoT
Execute um dos scripts criados na pasta `scripts/`:

* **Opção A (K6 - Recomendado):**
  ```bash
  k6 run scripts/stress_k6.js
  ```
* **Opção B (Python - Sem dependências externas):**
  ```bash
  python scripts/stress_iot.py http://localhost:8081 50 360
  ```
* **Opção C (PowerShell / Windows):**
  ```powershell
  .\scripts\stress_iot.ps1 -ApiUrl "http://localhost:8081" -Concurrency 40 -DurationSeconds 360
  ```

---

## 📷 5. Checklist de Evidências a Coletar e Salvar no Repositório

| # | Evidência | O que deve aparecer na imagem / log |
| :---: | :--- | :--- |
| **1** | **Scale-Up no Terminal** | Terminal com `kubectl get hpa -w` mostrando o `% TARGETS` subindo (ex: `120%/70%`) e as réplicas aumentando de `2` ➔ `4` ➔ `6` ➔ `...`. |
| **2** | **Dashboard de Métricas do Grafana** | Gráficos com as curvas de CPU e Memória atingindo o pico, acompanhadas do gráfico de latência P95 e requisições/s. |
| **3** | **Painel de Alertas do Grafana** | Aba *Alert rules* exibindo os alarmes no estado amarelo `Pending` e depois vermelho `Firing`. |
| **4** | **Scale-Down Pós-Estresse** | Terminal mostrando o HPA aguardando a janela de 5 min (`300s`) e reduzindo gradualmente os pods até retornar a `2 réplicas`. |

