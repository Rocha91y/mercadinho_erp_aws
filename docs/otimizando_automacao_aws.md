# Otimizando a automação: disparo do pipeline pela AWS

## O problema

O pipeline do meu projeto (`pipeline_lakehouse_mercadinho.yaml`) era agendado pelo `schedule` (cron) do GitHub Actions, configurado para rodar de 3 em 3 horas. Na prática, as execuções atrasavam muito. Cheguei a ver cerca de 6 horas de atraso.

**Por quê?** O cron do GitHub Actions funciona em "melhor esforço". Ele concorre com milhões de workflows em uma fila compartilhada, e o atraso piora nos horários de pico, principalmente na hora cheia. Eu já tinha mudado o minuto (`33 */3 * * *`), o que ajudou um pouco, mas não resolveu.

## A solução

Troquei quem dá a "ordem de partida". Em vez de esperar o GitHub se lembrar de rodar o workflow, configurei um agendador da AWS (o **Amazon EventBridge**) para chamar a API do GitHub no horário certo. O GitHub apenas executa o workflow.

```
EventBridge (regra agendada)
        │  a cada 3 horas
        ▼
Destino de API (POST na API do GitHub)
        │  workflow_dispatch
        ▼
GitHub Actions (CI + CD do pipeline)
        │
        ▼
AWS (S3 + Athena: raw → trusted → curated)
```

O EventBridge é um serviço feito só para agendar, por isso é bem mais pontual que o cron do GitHub.

## O que eu fiz, passo a passo

### 1. Gatilho manual no workflow

Meu YAML já tinha o `workflow_dispatch`, que cria o botão "Run workflow" e também permite o disparo por API. Não precisei alterar nada.

### 2. Token do GitHub (fine-grained)

Em Settings → Developer settings → Personal access tokens → Fine-grained tokens, criei um token com:

- **Nome:** `eventbridge-pipeline`
- **Validade:** 90 dias
- **Acesso:** apenas o repositório `mercadinho_erp_aws`
- **Permissões:** Actions (Read and write) e Metadata (Read-only, obrigatória)

Escolhi o fine-grained em vez do classic porque ele fica restrito a um repositório e só tem a permissão necessária.

### 3. Teste do token fora da AWS

Antes de levar o token para a AWS, testei o disparo com um script local em PowerShell (`disparar.ps1`), que chama o endpoint:

```
POST https://api.github.com/repos/Rocha91y/mercadinho_erp_aws/actions/workflows/pipeline_lakehouse_mercadinho.yaml/dispatches
Corpo: {"ref":"main"}
```

O script pede o token na hora de rodar, então ele não fica escrito no arquivo. Uma resposta vazia significa sucesso (HTTP 204), e uma nova execução aparece na aba Actions.

Duas coisas que aprendi nesse teste:

- A URL usa só o **nome do arquivo** do workflow, não o `name:` de dentro do YAML.
- No PowerShell, o JSON precisa de cuidado com as aspas. Por isso usei aspas simples no corpo.

### 4. Conexão no EventBridge

Em EventBridge → Conexões, criei:

- **Nome:** `github-connection`
- **Tipo de API:** pública
- **Autorização:** chave de API
  - Nome da chave: `Authorization`
  - Valor: `Bearer <token>`
- **Criptografia:** chave de propriedade da AWS

A AWS guarda o valor no Secrets Manager. A conexão ficou **Autorizada**.

### 5. Destino de API

Em EventBridge → Destinos de API, criei:

- **Nome:** `github-dispatch`
- **Endpoint:** a URL de `dispatches` do workflow
- **Método:** POST
- **Conexão:** `github-connection`

### 6. Regra agendada

Em EventBridge → Regras → Regra com agendamento (barramento `default`), criei:

- **Nome:** `dispara-pipeline-mercadinho`
- **Destino:** destino de API `github-dispatch`
- **Entrada:** texto JSON constante `{"ref":"main"}`
- **Cabeçalhos HTTP:**
  - `Accept: application/vnd.github+json`
  - `User-Agent: eventbridge` (o GitHub recusa chamadas sem esse cabeçalho)
- **Perfil de execução:** criado automaticamente pelo console

Para testar, a regra começou com `rate(5 minutes)`. Depois de confirmar o disparo, defini o horário final, de 3 em 3 horas:

```
cron(33 0/3 * * ? *)
```

O cron da AWS é em **UTC** (Brasília = UTC-3). Usei o minuto 33 para fugir da hora cheia, como já fazia no YAML.

### 7. Remoção do agendamento antigo do YAML

Com o EventBridge configurado, removi o bloco `schedule` (cron) do workflow. Agora o EventBridge é o único agendador, e o `on:` ficou assim:

```yaml
on:
  push:
    branches: [ main ]
  workflow_dispatch:
```

As execuções disparadas pelo EventBridge aparecem na aba Actions como "Manually run", porque para o GitHub todo disparo por API (`workflow_dispatch`) é manual. O que mostra que é o agendador da AWS é o horário fixo, de 3 em 3 horas, sem eu mexer em nada.

## Cuidados que tomei

- **Execuções simultâneas:** como o workflow também roda a cada push na `main`, um push e um disparo do EventBridge podem coincidir. O bloco `concurrency` (`cancel-in-progress: false`) faz a segunda execução esperar a primeira, o que protege as pastas do S3, já que o CTAS apaga e recria o destino.
- **Token:** não coloquei o token em nenhum arquivo do repositório, que é público. Anotei a data de validade, porque o disparo para de funcionar quando o token vence.
- **Custos:** em repositório público, os minutos do GitHub Actions são gratuitos, e o EventBridge custa centavos por mês nesse volume. O custo real está no Athena (dados lidos), por isso não deixei a regra rodando a cada 5 minutos.
- **Push na `main`:** o workflow também roda a cada push na `main`. Por isso, mudanças no YAML devo fazer em uma branch e só depois mesclar.

## Ponto de melhoria identificado

Hoje o workflow usa as chaves `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` guardadas em Secrets. A alternativa mais segura é o **OIDC**: o GitHub assume uma role da AWS com credenciais temporárias, sem chave fixa. É uma melhoria de segurança e não muda o funcionamento do pipeline.

## Resultado

O disparo agora é feito por um agendador dedicado (EventBridge), sem depender da fila do cron do GitHub, e o pipeline roda de forma previsível, de 3 em 3 horas, sem nenhum push manual.