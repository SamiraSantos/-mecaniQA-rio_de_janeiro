import http from 'k6/http';
import { check, sleep } from 'k6';

// Configuração do teste de estresse simulando sensores IoT
// Estágios:
// 1. Aquecimento (2 min com 10 VUs)
// 2. Pico de carga simulando horário das 08h/17h (5 min com 80 VUs -> Força CPU > 70% e aciona HPA de 2 para até 10 pods)
// 3. Desaceleração e Cooldown (5 min com 5 VUs -> Aguarda stabilization window e valida scale-down)
export const options = {
  stages: [
    { duration: '1m', target: 15 },   // Ramp-up inicial
    { duration: '4m', target: 70 },   // Pico de estresse dos sensores IoT
    { duration: '3m', target: 70 },   // Sustentação sob carga alta
    { duration: '1m', target: 5 },    // Corte de carga (início do cooldown)
    { duration: '5m', target: 2 },    // Janela de estabilização do scale-down
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'], // Taxa de erro aceitável < 5%
    http_req_duration: ['p(95)<1000'], // 95% das requisições abaixo de 1s
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8081'; // 8081 no kind ou 8080 local

export default function () {
  const sensorId = `SENSOR-${Math.floor(Math.random() * 500) + 100}`;
  const payload = JSON.stringify({
    sensorId: sensorId,
    temperatura: (Math.random() * 40 + 60).toFixed(2),
    pressao: (Math.random() * 2 + 1).toFixed(2),
    vibracao: (Math.random() * 0.5).toFixed(3),
    status: Math.random() < 0.02 ? 'error' : 'normal', // 2% de erros simulados
    timestamp: new Date().toISOString(),
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  // Envia leitura com stress_cpu ativado
  const res = http.post(`${BASE_URL}/api/sensores/telemetria?stress_cpu=true`, payload, params);

  check(res, {
    'status is 200 or 500': (r) => r.status === 200 || r.status === 500,
  });

  sleep(0.05); // Pequeno intervalo entre leituras do sensor
}

