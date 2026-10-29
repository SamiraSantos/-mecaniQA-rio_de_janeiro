#!/usr/bin/env python3
"""
Simulador de Carga de Sensores IoT para o MecaniQA Tech
Executa requisições concorrentes com payload de telemetria IoT para estressar a API,
provocar consumo de CPU/Memória, acionar o HPA e testar os alertas do Grafana.
"""

import sys
import time
import json
import random
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

API_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8081"
ENDPOINT = f"{API_URL}/api/sensores/telemetria?stress_cpu=true"
CONCURRENCY = int(sys.argv[2]) if len(sys.argv) > 2 else 40
DURATION_SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 360

print(f"================================================================")
print(f"🔥 INICIANDO TESTE DE ESTRESSE - SENSORES IOT MECANIQA TECH 🔥")
print(f"Target Endpoint: {ENDPOINT}")
print(f"Sensores Concorrentes: {CONCURRENCY}")
print(f"Duração planejada: {DURATION_SECONDS} segundos")
print(f"Acompanhe o scale-up em outro terminal: kubectl get hpa -n mecaniqa -w")
print(f"================================================================")

stats = {"total": 0, "sucesso": 0, "falha": 0}

def send_telemetry():
    sensor_id = f"SENSOR-IOT-{random.randint(100, 999)}"
    payload = {
        "sensorId": sensor_id,
        "temperatura": round(random.uniform(65.0, 105.0), 2),
        "pressao": round(random.uniform(1.0, 3.5), 2),
        "vibracao": round(random.uniform(0.05, 0.45), 3),
        "status": "error" if random.random() < 0.03 else "normal",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                stats["sucesso"] += 1
            else:
                stats["falha"] += 1
    except urllib.error.HTTPError as e:
        stats["falha"] += 1
    except Exception:
        stats["falha"] += 1
    finally:
        stats["total"] += 1

start_time = time.time()
with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
    while time.time() - start_time < DURATION_SECONDS:
        futures = [executor.submit(send_telemetry) for _ in range(CONCURRENCY)]
        for f in futures:
            f.result()
        elapsed = int(time.time() - start_time)
        print(f"[{elapsed}s / {DURATION_SECONDS}s] Enviadas: {stats['total']} | Sucesso: {stats['sucesso']} | Falhas: {stats['falha']}")
        time.sleep(0.1)

print("\n================================================================")
print(f"✅ Teste de carga finalizado! Total enviado: {stats['total']}")
print("Aguarde a janela de 5 minutos para validar o Scale-Down no HPA.")
print("================================================================")

