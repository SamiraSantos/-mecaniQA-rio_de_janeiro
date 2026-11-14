"""Verifica leituras, falhas e exposição HTTP real sem depender de Kubernetes."""

import unittest
from unittest.mock import patch
from urllib.request import urlopen

from prometheus_client import REGISTRY, start_http_server

import main


class MetricsTest(unittest.TestCase):
    def test_success_and_failure_exposed_over_http(self):
        sensor = "test-sensor"
        with patch.object(main.time, "sleep"):
            main.sample(sensor, 0)
            temperature = REGISTRY.get_sample_value("iot_temperature_celsius", {"sensor": sensor})
            self.assertTrue(18 <= temperature <= 35)
            humidity = REGISTRY.get_sample_value("iot_humidity_percent", {"sensor": sensor})
            self.assertTrue(30 <= humidity <= 90)
            self.assertGreater(REGISTRY.get_sample_value("iot_sensor_last_success_timestamp_seconds", {"sensor": sensor}), 0)
            main.sample(sensor, 1)
            self.assertEqual(REGISTRY.get_sample_value("iot_temperature_celsius", {"sensor": sensor}), temperature)
        server, thread = start_http_server(0, addr="127.0.0.1")
        try:
            with urlopen(f"http://127.0.0.1:{server.server_port}/metrics", timeout=5) as response:
                body = response.read().decode()
                self.assertIn('iot_sensor_readings_total{sensor="test-sensor"} 1.0', body)
                self.assertIn('iot_sensor_errors_total{sensor="test-sensor"} 1.0', body)
                self.assertIn('iot_sensor_read_duration_seconds_count{sensor="test-sensor"} 2.0', body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
