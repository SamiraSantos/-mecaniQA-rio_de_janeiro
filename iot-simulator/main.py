"""Simulador IoT com métricas Prometheus em :8000/metrics."""

import logging
import math
import os
import random
import signal
import threading
import time

from prometheus_client import Counter, Gauge, Histogram, start_http_server

TEMPERATURE = Gauge("iot_temperature_celsius", "Última temperatura medida", ["sensor"])
HUMIDITY = Gauge("iot_humidity_percent", "Última umidade relativa medida", ["sensor"])
READINGS = Counter("iot_sensor_readings_total", "Leituras concluídas", ["sensor"])
ERRORS = Counter("iot_sensor_errors_total", "Falhas de leitura simuladas", ["sensor"])
DURATION = Histogram(
    "iot_sensor_read_duration_seconds", "Duração de cada tentativa de leitura",
    ["sensor"], buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
)
LAST_SUCCESS = Gauge("iot_sensor_last_success_timestamp_seconds", "Instante da última leitura válida", ["sensor"])


def sample(sensor, error_rate):
    with DURATION.labels(sensor).time():
        time.sleep(random.uniform(0.005, 0.05))
        if random.random() < error_rate:
            ERRORS.labels(sensor).inc()
            logging.warning("Falha simulada no sensor %s", sensor)
            return
        TEMPERATURE.labels(sensor).set(random.uniform(18, 35))
        HUMIDITY.labels(sensor).set(random.uniform(30, 90))
        READINGS.labels(sensor).inc()
        LAST_SUCCESS.labels(sensor).set(time.time())


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    port = int(os.getenv("METRICS_PORT", "8000"))
    count = int(os.getenv("SENSOR_COUNT", "3"))
    interval = float(os.getenv("SAMPLE_INTERVAL_SECONDS", "2"))
    error_rate = float(os.getenv("SENSOR_ERROR_RATE", "0.05"))
    if not (1 <= port <= 65535 and 1 <= count <= 100):
        raise ValueError("METRICS_PORT deve ser 1..65535 e SENSOR_COUNT 1..100")
    if not math.isfinite(interval) or interval <= 0 or not 0 <= error_rate <= 1:
        raise ValueError("Intervalo deve ser positivo e finito; taxa de erro deve ser 0..1")
    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    sensors = [f"sensor-{i:02d}" for i in range(1, count + 1)]
    for sensor in sensors:
        for metric in (TEMPERATURE, HUMIDITY, READINGS, ERRORS, DURATION, LAST_SUCCESS):
            metric.labels(sensor)
    server, thread = start_http_server(port, addr="0.0.0.0")
    logging.info("Métricas disponíveis em :%s/metrics; sensores=%s", port, count)
    try:
        while not stopped.is_set():
            for sensor in sensors:
                if stopped.is_set():
                    break
                sample(sensor, error_rate)
            stopped.wait(interval)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
