# BotCity Maestro — API v2, operações de bot

Base: `https://<workspace>.botcity.dev`

## Autenticação

```
POST /api/v2/workspace/login
Content-Type: application/json

{"login": "<workspace>", "key": "<chave>"}
```

Resposta: `{"accessToken": "...", "organizationLabel": "..."}`

Todas as chamadas seguintes levam os headers:

```
token: <accessToken>
organization: <organizationLabel>
```

`Content-Type: application/json` nas chamadas JSON. **No upload
multipart não envie Content-Type** — o cliente HTTP precisa definir o
boundary sozinho, senão a API devolve 400.

## Sequência de deploy

### 1. Listar bots — `GET /api/v2/bot`

Query opcional: `botId`, `repositories` (repetível).
Resposta: `DeployDTO[]` — **um item por bot, só com a versão em
release**. Para ver todas as versões cadastradas de um bot use
`GET /api/v2/bot/pagination?botId=<id>` (o `plan_deploy.py` faz isso
para não reaproveitar um número de versão antigo).

### 2. Versão publicada — `GET /api/v2/bot/{botId}?repository=DEFAULT`

Resposta: `DeployDTO` da versão que os runners executam hoje.
`404` quando o bot nunca teve release naquele repositório.

### 3. Criar a versão — `POST /api/v2/bot`

```json
{
  "organization": "<organizationLabel>",
  "botId": "<botId>",
  "version": "1.0.4c",
  "technology": "PYTHON",
  "command": "python main.py",
  "repositoryLabel": "DEFAULT"
}
```

`technology`: `JAVA`, `PYTHON`, `JAVASCRIPT` ou `COMMAND`.
`command` aceita `null`. `fileHash` e `assets` existem no schema mas
não são necessários — o Maestro preenche no upload.

### 4. Enviar o pacote — `POST /api/v2/bot/upload/{botId}/version/{version}`

`multipart/form-data`, campo `file`, com o `.zip` (também aceita
`.jar` e `.tar.gz`). Sobrescreve o pacote da versão se já houver um.

### 5. Publicar — `POST /api/v2/bot/release`

```json
{
  "organization": "<organizationLabel>",
  "botId": "<botId>",
  "version": "1.0.4c",
  "repositoryLabel": "DEFAULT"
}
```

A partir daí as novas tarefas executam essa versão.

## Outras operações

| Operação | Chamada |
|---|---|
| Metadados de uma versão | `GET /api/v2/bot/{botId}/version/{botVersion}` |
| Listar paginado | `GET /api/v2/bot/pagination?page=0&size=50&sort=dateCreation,desc` |
| Baixar pacote | `GET /api/v2/bot/{botId}/version/{version}/download?fileName={botId}.zip` (com `bot.zip` volta 404) |
| Apagar versão | `DELETE /api/v2/bot/{botId}/version/{botVersion}` |
| Atualizar metadados | `POST /api/v2/bot/update` (corpo `DeployDTO`) |

## DeployDTO

| Campo | Tipo |
|---|---|
| `id` | ObjectId |
| `version` | string |
| `botId` | string |
| `file` | string |
| `organization` | string |
| `technology` | enum JAVA/PYTHON/JAVASCRIPT/COMMAND |
| `lastUpdate` | date-time |
| `command` | string |
| `repositoryLabel` | string |
| `fileHash` | string |
| `releaseVersion` | string |
| `assets` | string[] |

## Erros

| Status | Significado prático |
|---|---|
| 400 | Payload inválido — normalmente `technology` fora do enum ou versão duplicada |
| 401/403 | Token expirado, chave errada ou ambiente trocado |
| 404 | `botId` inexistente ou sem release no repositório informado |
| 413 | Pacote acima do limite aceito |

## Fontes

- Demais operações da API: `references/receitas.md`, `references/endpoints.md`
  e `scripts/botcity.py endpoints|describe`.
- [Documentação oficial da Maestro API](https://documentation.botcity.dev/maestro/maestro-api/maestro-api/)
  e a spec OpenAPI que ela embute: <https://developers.botcity.dev/v3/api-docs>.
- [Documentação BotCity — Bots](https://documentation.botcity.dev/maestro/features/bots/)
- [botcity-dev/botcity-action-bots](https://github.com/botcity-dev/botcity-action-bots)
