# Projeto de Métricas

Stack independente da API Java existente: simulador Python, Prometheus e Grafana
no namespace `metrics`. Não exige Prometheus Operator, RBAC de cluster ou banco
de dados.

## Executar localmente

Na raiz do repositório:

```bash
python -m venv .venv
# Linux/WSL: source .venv/bin/activate
# PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r iot-simulator/requirements.txt
python iot-simulator/main.py
```

Acesse `http://localhost:8000/metrics`. As variáveis opcionais são
`METRICS_PORT=8000`, `SENSOR_COUNT=3` (1 a 100),
`SAMPLE_INTERVAL_SECONDS=2` e `SENSOR_ERROR_RATE=0.05` (0 a 1).
Os valores são sintéticos; cada tentativa produz uma leitura ou uma falha simulada.
Uma falha preserva os últimos valores válidos e incrementa o contador de erros.
O timestamp da última leitura permite detectar dados antigos.

Teste de instrumentação e exposição HTTP:

```bash
python -m unittest discover -s iot-simulator -p 'test_*.py' -v
```

## Deploy em Kubernetes

Pré-requisitos: Docker funcionando, `kubectl` e contexto Kubernetes configurado.
Para aproveitar o cluster kind `mecaniqa` descrito no README principal:

```bash
docker build -t mecaniqa-iot-simulator:1.0.0 iot-simulator
kind load docker-image mecaniqa-iot-simulator:1.0.0 --name mecaniqa
kubectl apply -k k8s/metrics
kubectl rollout status deployment/iot-simulator -n metrics --timeout=180s
kubectl rollout status deployment/prometheus -n metrics --timeout=180s
kubectl rollout status deployment/grafana -n metrics --timeout=180s
kubectl get pods,services -n metrics
```

No WSL, use `sudo docker` e `sudo kind` se necessário. Caso ainda não exista um
cluster, crie-o conforme o README principal antes de carregar a imagem.
Em cluster remoto, publique a imagem em um registry acessível pelos nós e altere
`image` em `simulator.yaml` antes do apply (configure imagePullSecrets se privado).

O Kustomize gera o ConfigMap a partir de `prometheus.yml`, com hash no nome.
Alterações na configuração seguidas de `kubectl apply -k k8s/metrics` provocam
novo rollout do Prometheus. A coleta acontece a cada 15 segundos via Service DNS.
Mantenha uma réplica do simulador: escalar requer descoberta e coleta individual
dos Pods para evitar alternar contadores entre réplicas no mesmo alvo.

## Grafana e dashboards

O Grafana é provisionado automaticamente com Prometheus como fonte de dados.
O dashboard versionado `MecaniQA - Golden Signals` contém exatamente quatro
painéis:

| Painel | Query PromQL base | Objetivo |
| --- | --- | --- |
| CPU | `sum(rate(process_cpu_seconds_total{job="iot-simulator"}[5m]))` | Uso de CPU pelo simulador. |
| Memória | `process_resident_memory_bytes{job="iot-simulator"}` | Memória residente do processo Python. |
| Erro | `erros / (erros + leituras)` | Detectar aumento de falhas das leituras. |
| Sucesso | `leituras / (erros + leituras)` | Confirmar a proporção de leituras válidas. |

Para acessar localmente, execute:

```bash
kubectl port-forward -n metrics service/grafana 3000:3000
```

Abra `http://localhost:3000` e entre com `admin` / `admin`. Em seguida, acesse
**Dashboards > MecaniQA > MecaniQA - Golden Signals**. Essas credenciais são
exclusivas do laboratório; em produção, use um Secret com senha forte.

## Verificar a coleta

Em terminais separados:

```bash
kubectl port-forward -n metrics service/prometheus 9090:9090
kubectl port-forward -n metrics service/iot-simulator 8000:8000
kubectl port-forward -n metrics service/grafana 3000:3000
```

Acesse `http://localhost:8000/metrics` e `http://localhost:9090/targets`.
Aguarde pelo menos 15 segundos: o job `iot-simulator` deve estar `UP`.
Na interface do Prometheus, execute:

```promql
up{job="iot-simulator"}
iot_temperature_celsius
iot_humidity_percent
sum by (sensor) (rate(iot_sensor_readings_total[5m]))
sum by (sensor) (rate(iot_sensor_errors_total[5m]))
histogram_quantile(0.95, sum by (sensor, le) (rate(iot_sensor_read_duration_seconds_bucket[5m])))
time() - iot_sensor_last_success_timestamp_seconds
```

`up` deve retornar `1`. Aguarde ao menos duas coletas para consultas com `rate`.
Os Services são internos; o acesso local ocorre pelo port-forward.
Em caso de falha:

```bash
kubectl describe pods -n metrics
kubectl logs -n metrics deployment/iot-simulator
kubectl logs -n metrics deployment/prometheus
```

## Armazenamento

Este laboratório usa `emptyDir` para funcionar sem StorageClass. O histórico
é perdido quando o Pod do Prometheus é removido ou substituído. A retenção
é limitada a 7 dias ou 1 GB; o volume tem limite de 2 GiB. Para preservar dados
entre recriações, substitua o `emptyDir` por um PVC adequado ao cluster.

Referências: [cliente Python](https://prometheus.github.io/client_python/)
e [configuração do Prometheus](https://prometheus.io/docs/prometheus/latest/configuration/configuration/).
