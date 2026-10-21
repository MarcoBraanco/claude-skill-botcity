# BotCity Maestro — receitas e pegadinhas

Comportamentos da API que não estão na spec (ou que a contradizem), já
conferidos em uso. Leia antes de montar um `call` fora dos atalhos.

## Autenticação e convenções

- Login: `POST /api/v2/workspace/login` com `{"login", "key"}`. Depois,
  toda chamada leva os headers `token` e `organization`. **Não** existe
  Bearer, refresh nem logout; em 401 refaça o login (o cliente já faz).
- O header `Authorization` que a spec marca como obrigatório é resíduo
  do springdoc. Ignore.
- `GET /api/v2/maestro/version` é o único endpoint sem autenticação.
- Paginação estilo Spring: `page` (base 0), `size` (o servidor corta em
  **400**), `sort=campo,asc|desc`. Resposta `{content, totalPages,
  totalElements, last, ...}`.
- Filtros que a spec mostra como objeto (`automationTaskDTO`,
  `pageable`, `filters`...) são, na prática, os **campos** desse objeto
  soltos na query: `?days=7&states=RUNNING&page=0`.
- Listas na query: repita o parâmetro (`-q states=RUNNING -q
  states=START`).
- `days` é janela retroativa a partir de hoje. O Maestro opera em
  **UTC**: considere isso em `minExecutionDate`, `startDate`, `endDate`.

## Filtros que funcionam (testados)

| Listagem | Filtro por automação | Outros |
|---|---|---|
| `GET /task` | `activityLabel` (exato) | `states`, `days`, `machineId`, `taskId` |
| `GET /activity/pagination` | `automation` (trecho) | — |
| `GET /scheduling` | `likeAutomationOrScheduleName` (trecho) | `status` |
| `GET /error` | `automations` (exato) | `days`, `taskId` |
| `GET /alerts` | `activityLabel` (exato) | `type`, `days`, `taskId` |
| `GET /artifact` | `automation` (exato) | `days`, `taskId` |
| `GET /bot/pagination` | `botId` | `repositories`, `technology` |

`GET /activity/pagination?search=` e `GET /scheduling?activityLabel=`
são **ignorados** pelo servidor (devolvem tudo).

## Bots

- `GET /api/v2/bot` devolve **um item por bot, só a versão em release**.
  Todas as versões: `GET /api/v2/bot/pagination?botId=<id>`.
- Download: `GET /api/v2/bot/{botId}/version/{v}/download?fileName=<botId>.zip`.
  Com `fileName=bot.zip` volta 404.
- Release/rollback: `POST /api/v2/bot/release` com `organization`,
  `botId`, `version`, `repositoryLabel` — a versão tem que já existir com
  pacote.
- `DELETE /api/v2/bot/{botId}/version/{v}` não consta na spec (legado);
  nunca apague a versão em release.

## Tarefas

- Criar: `POST /task` com `activityLabel`, `parameters` (dict cuja
  chave é o *label* do parâmetro da automação), `test`, `priority`,
  `minExecutionDate` opcional.
- Finalizar, reiniciar e interromper usam o mesmo `POST /task/{id}`; só
  muda o corpo: `{"state":"FINISHED","finishStatus":...}`,
  `{"state":"START"}`, `{"interrupted":true}`.
- Ao finalizar com contadores: `totalItems == processedItems +
  failedItems`. O servidor não valida, mas valor errado suja o Insights.
- Interrupção é cooperativa: só funciona se o bot consultar a flag. Se
  não parar, finalize.
- `DELETE /task/bulk` recebe `{"labels": [ids numéricos]}`.

## Automações e agendamentos

- Atualizar automação: `PATCH /activity/{label}` com só os campos a
  mudar. O `POST` equivalente está deprecated.
- Prioridade vai no path: `PUT /activity/{label}/priority/{n}` (0–10).
- Agendamento: cron de **6 campos** com segundos (`0 30 8 * * MON-FRI`).
  Valide com `POST /scheduling/validate-cron` `{"cronExpression":
  "..."}` (com a chave `cron` o servidor responde 400); a resposta é
  `true`/`false`. Aceita também a sintaxe Quartz com `?`.
  Atualizar = `POST /scheduling/{id}` com o objeto **inteiro**; para
  pausar, mande `active: false` (não precisa apagar). O campo
  `dayOfMouth` tem esse typo na própria API.

## Credenciais

- `GET /credential` e `GET /credential/{label}` devolvem os segredos em
  **texto puro**. Os atalhos mascaram; com `call`, não imprima a
  resposta inteira na conversa.
- `GET /credential/{label}/key/{key}` devolve o valor cru (texto, não
  JSON).
- `POST /credential/{label}/key` `{"key","value"}` cria ou atualiza uma
  chave.
- `POST /credential/{label}` **substitui a lista inteira** de `secrets`.
  Não existe remoção de chave individual: leia o cofre, tire a chave da
  lista e reenvie tudo — chave omitida é perdida.

## Datapool (fora da spec)

- Ativar/desativar: não há endpoint próprio. `GET /datapool/{label}`,
  troque `active` e reenvie o objeto **inteiro** em `POST
  /datapool/{label}`. O GET devolve `defaultActivity`, mas o POST espera
  `defaultAutomation` — traduza, senão a fila perde a automação.
- `GET /datapool/{label}/pull` responde **204** quando a fila está
  vazia (não é erro).
- Item: `POST /datapool/{label}/entry/{id}` com o objeto completo; no
  corpo o campo é `dataPoolLabel` (P maiúsculo). Concluir: `state:
  DONE`; falhar: `state: ERROR` + `errorType: SYSTEM|BUSINESS`.
- Transições válidas: `PENDING → PROCESSING|CANCELED`; `PROCESSING →
  DONE|ERROR|TIMEOUT`; `TIMEOUT → DONE|ERROR`. Cancelar (`PUT
  .../cancel`) só em `PENDING`. Excluir item só em `PENDING`, `CANCELED`,
  `DONE`, `ERROR`.

## Logs, erros e arquivos

- Logs de execução são tabelas: `GET /log` lista, `GET /log/{label}`
  traz as colunas, `GET /log/{label}/entry-list?days=N` traz as linhas
  (`columns` chaveado pelo *label* da coluna). `POST /log/event` e
  `/log/studio` são eventos de telemetria, não logs.
- Arquivo de resultado sobe em duas etapas: `POST /artifact` (registro,
  devolve `id`) e `POST /artifact/log/{id}` (binário multipart, campo
  `file`). O `log` no path é só o nome do endpoint.
- Screenshot de erro: `GET /error/{id}/screenshot`; anexos por índice:
  `GET /error/{id}/attachments/{n}`.
- Uploads em geral (ícone, screenshot, pacote): a spec diz JSON, mas o
  envio real é `multipart/form-data` com campo `file` → `call ...
  --arquivo file=<caminho>`.

## Enums

| Campo | Valores |
|---|---|
| `task.state` | `START` `RUNNING` `TIMEOUT` `FINISHED` `CANCELED` |
| `task.finishStatus` | `SUCCESS` `FAILED` `PARTIALLY_COMPLETED` |
| `alerts.type` | `INFO` `WARN` `ERROR` |
| `message.type` | `TEXT` `HTML` |
| `technology` | `JAVA` `PYTHON` `JAVASCRIPT` `COMMAND` |
| `activity.state` | `DRAFT` `COMPLETE` |
| `activity.parameters[].type` | `TEXT` `INTEGER` `DOUBLE` `DATE` `SINGLE_OPTION` `MULTI_OPTION` `FILE` `CREDENTIAL_SINGLE` `CREDENTIAL_MULTIPLE` |
| `machine.type` | `DESKTOP` `BACKGROUND` |
| `artifact.type` | `INPUT` `RESULT` |
| item de datapool `state` | `PENDING` `PROCESSING` `DONE` `ERROR` `TIMEOUT` `CANCELED` |
| `datapool.consumptionPolicy` | `FIFO` `LIFO` |
| `datapool.trigger` | `ALWAYS` `NEVER` `NO_TASK_ACTIVE` |

## Métricas do painel (API v3)

- Os endpoints `/api/v3/...` (`tasks/count-by-state`,
  `tasks/success-rate`, `tasks/count-consecutive-failures`,
  `tasks/count-failed-by-automation`, `errors/count-by-automation`,
  `runners/count-by-state` etc.) alimentam o painel do Maestro. O
  atalho `analisar` junta os principais.
- A janela vai em `startDate`/`endDate` (ISO 8601 UTC, ex.:
  `2026-01-01T00:00:00Z`); `automations` (repetível) e `repository`
  filtram. `days` não existe aqui.
- No `call`, escreva o caminho com a versão: `call GET
  api/v3/tasks/success-rate -q startDate=... -q endDate=...`. Sem
  prefixo, o script assume `/api/v2`.
- Workspaces antigos ou on-premise podem não ter a v3; `analisar` mostra
  a métrica como indisponível em vez de falhar.

## Fontes

- Documentação oficial: <https://documentation.botcity.dev/maestro/>
  (SDK Python em `.../maestro-sdk/python/`, API em
  `.../maestro-api/maestro-api/`).
- Spec OpenAPI oficial, embutida no Swagger da página da API:
  <https://developers.botcity.dev/v3/api-docs>. A cópia local em
  `openapi.json` é atualizada por `scripts/docs_oficiais.py atualizar`.
- `endpoints_extras.json`: operações fora da spec pública e notas
  curadas, mantidas à mão neste repositório.
