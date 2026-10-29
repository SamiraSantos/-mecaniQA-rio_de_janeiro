#!/bin/bash
# Script de disparo rápido de carga em bash usando curl em loop background
API_URL="${1:-http://localhost:8081}"
CONCURRENCY="${2:-30}"
DURATION="${3:-300}"

echo "=========================================================="
echo "🚀 DISPARANDO CARGA SIMULADA DE SENSORES IOT VIA BASH/CURL"
echo "Endpoint: $API_URL/api/sensores/telemetria"
echo "Concorrência: $CONCURRENCY threads | Duração: $DURATION s"
echo "=========================================================="

start_time=$(date +%s)
end_time=$((start_time + DURATION))

send_worker() {
  while [ $(date +%s) -lt $end_time ]; do
    curl -s -X POST "$API_URL/api/sensores/telemetria?stress_cpu=true" \
      -H "Content-Type: application/json" \
      -d '{"sensorId":"SENSOR-BASH","temperatura":82.5,"pressao":2.1}' > /dev/null
    sleep 0.05
  done
}

pids=()
for i in $(seq 1 $CONCURRENCY); do
  send_worker &
  pids+=($!)
done

trap "kill ${pids[@]} 2>/dev/null; exit" SIGINT SIGTERM

echo "Injeção em andamento... Acompanhe com 'kubectl get hpa -n mecaniqa -w'"
for pid in "${pids[@]}"; do
  wait $pid 2>/dev/null
done

echo "✅ Teste concluído."

