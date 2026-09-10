# MecaniQA Tech — laboratório de containers

Este projeto executa três serviços isolados:

- API Java 17 na porta `8080`;
- MySQL 8.4 em uma rede interna;
- Redis 7.4 em uma rede interna.

Somente a API é publicada no computador. MySQL e Redis são acessados pela API
por meio dos nomes internos `mysql` e `redis`.

O arquivo `docker-compose.yml` conecta os três serviços à rede bridge
`mecaniqa-network`. O DNS interno do Docker resolve automaticamente os nomes dos
serviços, portanto a API acessa o banco por `mysql:3306` e o cache por
`redis:6379`, sem IPs fixos.

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

## Persistência

Os volumes nomeados `mysql_data` e `redis_data` são armazenados fora da camada
gravável dos containers. Assim, recriar ou reiniciar os containers não remove os
dados. O MySQL grava em `/var/lib/mysql` e o Redis em `/data`.

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

## Kubernetes

Os manifestos do cluster estão em `k8s/`. Eles criam:

- `Deployment` com duas réplicas para a API e auto-recuperação de Pods;
- `Deployment` de uma réplica para MySQL e Redis;
- `Service` interno (`ClusterIP`) para MySQL e Redis;
- `Service` externo (`LoadBalancer`) para a API;
- `PersistentVolumeClaim` para os dados de MySQL e Redis.

Antes do deploy em nuvem, publique a imagem da API em um registry e substitua
`ghcr.io/SEU-USUARIO/mecaniqa-api:1.0.0` em `k8s/base/api.yaml` pelo endereço real.

Depois de configurar o contexto do cluster, aplique tudo com:

```bash
kubectl apply -k k8s
kubectl get pods,services,pvc -n mecaniqa
```

Para identificar um Pod em falha:

```bash
kubectl get pods -n mecaniqa
kubectl describe pod NOME_DO_POD -n mecaniqa
kubectl logs NOME_DO_POD -n mecaniqa
```

### Cluster local com kind

Se a equipe ainda não tiver um cluster em nuvem, use `kind` para executar um
cluster Kubernetes local dentro do Docker. Essa alternativa é adequada para o
laboratório, mas não substitui um cluster em nuvem em produção.

Instale o `kind` no Ubuntu/WSL (arquitetura x86_64):

```bash
mkdir -p "$HOME/.local/bin"
curl -Lo "$HOME/.local/bin/kind" https://kind.sigs.k8s.io/dl/v0.33.0/kind-linux-amd64
chmod +x "$HOME/.local/bin/kind"
"$HOME/.local/bin/kind" --version
```

Os comandos abaixo usam `sudo docker`, que funciona sem alterar as permissões do
usuário. Se preferir remover o `sudo` futuramente, adicione seu usuário ao grupo
`docker` e reabra o Ubuntu (isso concede ao usuário controle administrativo do
Docker):

```bash
sudo usermod -aG docker $USER
```

Na raiz do projeto, crie o cluster, carregue a imagem local e aplique a
sobreposição específica do kind:

```bash
sudo docker build -t mecaniqa-api:1.0 .
sudo "$HOME/.local/bin/kind" create cluster --name mecaniqa --config k8s/overlays/kind/kind-cluster.yaml --kubeconfig "$HOME/.kube/config" --wait 5m
sudo chown "$USER":"$USER" "$HOME/.kube/config"
sudo "$HOME/.local/bin/kind" load docker-image mecaniqa-api:1.0 --name mecaniqa
kubectl apply -k k8s/overlays/kind
kubectl get pods,services,pvc -n mecaniqa
```

No kind, a API usa `NodePort` e fica disponível em:

```bash
curl http://localhost:8081/actuator/health
```

O manifesto-base em `k8s/` continua usando `LoadBalancer` para o futuro deploy
em nuvem. A sobreposição `k8s/overlays/kind/` não precisa de Docker Hub porque
carrega a imagem diretamente nos nós locais do cluster.
