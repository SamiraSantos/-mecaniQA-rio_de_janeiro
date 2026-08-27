package com.mecaniqa.api;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class MecaniqaApiApplicationTests {

    @Test
    void aplicacaoPossuiNome() {
        assertThat("MecaniQA API").startsWith("MecaniQA");
    }
}
