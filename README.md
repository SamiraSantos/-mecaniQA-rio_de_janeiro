# MecaniQA Tech — laboratório de containers

Este projeto executa três serviços isolados:

- API Java 17 na porta `8080`;
- MySQL 8.4 em uma rede interna;
- Redis 7.4 em uma rede interna.

Somente a API é publicada no computador. MySQL e Redis são acessados pela API
por meio dos nomes internos `mysql` e `redis`.

## Pré-requisitos

- Docker Engine iniciado no Ubuntu/WSL;
- Docker Compose v2.

No Ubuntu, acesse o projeto salvo no Windows:

```bash
cd /mnt/c/Users/User/lab-banco
```

Se `docker version` retornar erro de permissão, use `sudo docker` nos comandos
ou adicione seu usuário ao grupo do Docker e abra uma nova sessão:

```bash
sudo usermod -aG docker $USER
```

## Construção e execução

Crie a imagem da API:

```bash
docker build -t mecaniqa-api:1.0 .
```

Inicie todo o ambiente:

```bash
docker compose up --build -d
```

Confira os containers:

```bash
docker compose ps
docker stats --no-stream
```

Teste a API e a integração com o MySQL:

```bash
curl http://localhost:8080/api
curl http://localhost:8080/api/status
curl http://localhost:8080/actuator/health
```

Teste o Redis diretamente dentro de sua rede isolada:

```bash
docker compose exec redis redis-cli ping
```

O resultado esperado é `PONG`.

## Logs e ciclo de vida

```bash
docker compose logs -f api
docker compose stop
docker compose start
docker compose restart api
docker compose down
```

O comando `docker compose down` preserva os volumes. O uso de
`docker compose down -v` também apaga os dados persistidos do MySQL e Redis.

## Segurança

O arquivo `.env` contém credenciais apenas para o laboratório e não é enviado ao
Git. Antes de produção, use senhas fortes e um gerenciador de segredos.
