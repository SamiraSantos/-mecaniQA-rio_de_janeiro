package com.mecaniqa.api;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class StatusController {

    private final JdbcTemplate jdbcTemplate;

    public StatusController(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @GetMapping
    public Map<String, Object> index() {
        return Map.of(
                "aplicacao", "MecaniQA API",
                "mensagem", "Container Java em execução",
                "timestamp", Instant.now().toString());
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> status() {
        Map<String, Object> resposta = new LinkedHashMap<>();
        resposta.put("aplicacao", "UP");
        resposta.put("timestamp", Instant.now().toString());

        try {
            Integer resultado = jdbcTemplate.queryForObject("SELECT 1", Integer.class);
            resposta.put("mysql", resultado != null && resultado == 1 ? "UP" : "DOWN");
            return ResponseEntity.ok(resposta);
        } catch (RuntimeException exception) {
            resposta.put("mysql", "DOWN");
            resposta.put("erro", "Não foi possível consultar o MySQL");
            return ResponseEntity.internalServerError().body(resposta);
        }
    }
}
