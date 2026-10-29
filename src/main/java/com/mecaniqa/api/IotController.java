package com.mecaniqa.api;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/sensores")
public class IotController {

    @GetMapping
    public Map<String, Object> status() {
        return Map.of(
                "servico", "Ingestão de Sensores IoT MecaniQA",
                "status", "ONLINE",
                "timestamp", Instant.now().toString()
        );
    }

    @PostMapping("/telemetria")
    public ResponseEntity<Map<String, Object>> receberLeitura(
            @RequestBody(required = false) Map<String, Object> leitura,
            @RequestParam(name = "stress_cpu", defaultValue = "false") boolean stressCpu,
            @RequestParam(name = "simular_erro", defaultValue = "false") boolean simularErro,
            @RequestParam(name = "delay_ms", defaultValue = "0") long delayMs) {

        // Simulação configurável de latência (para validação do alarme P95 > 1s)
        if (delayMs > 0) {
            try {
                Thread.sleep(delayMs);
            } catch (InterruptedException ignored) {
                Thread.currentThread().interrupt();
            }
        }

        // Simulação configurável de falha (para validação do alarme de erros > 5%)
        if (simularErro || (leitura != null && "error".equalsIgnoreCase(String.valueOf(leitura.get("status"))))) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of(
                    "status", "ERROR",
                    "mensagem", "Falha de processamento no sensor IoT",
                    "timestamp", Instant.now().toString()
            ));
        }

        // Carga de cálculo para consumir ciclos de CPU dos pods e acionar o HPA
        long iteracoes = stressCpu ? 1_500_000L : 75_000L;
        double dummy = 0;
        for (long i = 0; i < iteracoes; i++) {
            dummy += Math.sin(i) * Math.cos(i);
        }

        return ResponseEntity.ok(Map.of(
                "status", "PROCESSADO",
                "sensorId", leitura != null && leitura.containsKey("sensorId") ? leitura.get("sensorId") : "SENSOR-" + ThreadLocalRandom.current().nextInt(1000, 9999),
                "timestamp", Instant.now().toString(),
                "checksum", dummy
        ));
    }
}

