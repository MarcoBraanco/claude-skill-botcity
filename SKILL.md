---
name: botcity
description: Opera o BotCity Maestro de qualquer workspace pela API — publica versão nova de robô (deploy com .zip, upload e release), baixa release descompactado, faz rollback, analisa a saúde das automações, diagnostica tarefas, consulta e edita automações, tarefas, runners, agendamentos, credenciais, datapools, logs, erros, alertas e arquivos de resultado, cria credencial, fila e agendamento e chama qualquer endpoint. Use sempre que a pessoa citar BotCity, Maestro, botId, runner, datapool, release ou versão de robô, em português ou inglês — "sobe esse robô"/"deploy this bot", "baixa o release"/"download the bot", "volta a versão"/"rollback", "tarefas com erro"/"failed tasks", "por que a tarefa falhou"/"why did task X fail", "cria uma credencial"/"create a credential", "cria um datapool"/"create a datapool", "agenda a automação"/"schedule it", "configura a skill do BotCity"/"set up BotCity" ou "/botcity <pedido>".
---

# BotCity Maestro

Tudo passa por scripts desta pasta (Python 3 + `requests`):

| Script | Para quê |
|---|---|
| `scripts/botcity.py` | Atalhos do dia a dia e acesso a toda a API |
| `scripts/plan_deploy.py` + `scripts/run_deploy.py` | Publicar versão a partir do código local (com confirmação; ver **Deploy**) |
| `scripts/docs_oficiais.py` | Conferir/atualizar a skill com a documentação oficial |
| `scripts/configurar.py` | Setup de primeiro uso |

A skill pode estar em qualquer pasta (ex.: `~/.claude/skills/botcity`
ou `~/.claude/skills/claude-skill-botcity`). Use sempre a pasta onde
está este `SKILL.md`, que o Claude Code informa ao carregar a skill
("Base directory for this skill"). Não assuma um caminho fixo.

```bash
SK="<pasta desta skill>/scripts"
BC="python $SK/botcity.py"
$BC bots --busca NFE
```

PowerShell: `python "<pasta desta skill>\scripts\botcity.py" bots`.

**Comandos e opções aceitam português ou inglês** (`tarefas`/`tasks`,
`baixar`/`download`, `--dias`/`--days`, `--busca`/`--search`...). Responda
sempre no idioma em que a pessoa escreveu; as mensagens dos scripts são
em português.

O ambiente padrão é o `ambiente_padrao` do config. Para outro:
`$BC --ambiente QA ...`. `--json` em qualquer comando devolve o JSON cru.

## Primeiro uso

Se qualquer script responder com `CONFIG_AUSENTE`, ou se a pessoa pedir
para configurar, conduza o setup, sem tentar adivinhar dados:

1. `python $SK/configurar.py status` para ver o que já existe.
2. **Antes de pedir os dados, diga onde pegá-los**: no orquestrador
   (Maestro), menu **Ambiente do desenvolvedor** (em inglês, *Dev.
   Environment*). Lá aparecem o **Workspace**, o **Login** e a **Chave**.
   Depois pergunte o que faltar: a **URL do servidor** (o endereço do
   Maestro: `https://<workspace>.botcity.dev` na nuvem, ou o endereço
   on-premise), o **Login** (vai em `--workspace`) e se há mais de um
   ambiente (ex.: PROD e QA; cada um tem o seu Ambiente do
   desenvolvedor). Pergunte também a pasta para baixar releases e as
   pastas onde ficam os projetos.
3. Grave: `python $SK/configurar.py criar --servidor URL --workspace W
   --ambiente PROD [--pasta-downloads P] [--raiz-projetos R]`. Repita com `--ambiente QA --workspace W2` para outro ambiente.
4. **Chave de acesso** (o campo **Chave** do Ambiente do desenvolvedor):
   o caminho recomendado é a chave **não passar pela conversa**. Ofereça duas opções: definir a variável de ambiente
   `BOTCITY_KEY_<AMBIENTE>` (ex.: `BOTCITY_KEY_PROD`), ou editar o
   `~/.botcity/config.json` e trocar o texto `DEFINA_BOTCITY_KEY...` pela
   chave. Diga também que, se a pessoa preferir, pode colar a chave no
   chat e você grava com `criar ... --chave` (ela fica no histórico da
   conversa). Nunca mostre a chave depois de gravada.
5. **Avise sobre o sufixo de versão**: os deploys feitos pela skill
   recebem o sufixo `c` (de **C**laude, ex.: `1.0.3 → 1.0.4c`), que
   distingue no Maestro o que subiu pela skill do que subiu à mão. Ele é
   configurável: `configurar.py criar --sufixo ""` (sem sufixo) ou outro
   texto.
6. `python $SK/configurar.py testar` para confirmar o login.

Config antigo dentro da pasta da skill ainda funciona; `configurar.py
migrar` move para `~/.botcity/`.

## Como agir

O pedido chega livre (`/botcity baixa o NFE`, `/botcity why did task 123
fail?`). Roteie assim:

1. **Publicar código local** ("sobe", "publica", "deploy", "gera o
   zip") → seção **Deploy**.
2. **Saúde geral** ("como estão os robôs", "o que está falhando",
   "insights") → `$BC analisar [--dias 7] [--automacao L]`.
3. **Uma tarefa específica** ("por que a 123 falhou") → `$BC
   diagnosticar 123`; para o stack trace, `$BC erro <id>
   [--screenshot arq.png]`.
4. **Baixar um release** → `baixar` (descompacta sozinho).
5. **Algo coberto pelos atalhos** (tabela abaixo) → use o atalho.
6. **O resto** → `$BC endpoints <palavras>` para achar a operação,
   `$BC describe METODO caminho` para ver parâmetros, corpo, exemplo e
   pegadinhas, e `$BC call METODO caminho ...` para executar. Leia
   `references/receitas.md` antes de montar corpo de escrita.

O nome do bot pode ser só um trecho ("NFE"): o script acha o botId exato
e, se houver mais de um plausível (famílias `ROBO_NFE_1`/`ROBO_NFE_2`),
**para e lista os candidatos**. Pergunte qual é; não escolha sozinho.

## Atalhos (PT / EN)

| Área | Comandos |
|---|---|
| Bots | `bots [--busca T]` · `bot BOT` (versões, marca a que está em release) |
| Release | `baixar\|download BOT [--versao V] [--destino P] [--sem-extrair] [--manter-zip] [--sobrescrever]` · `release BOT VERSAO --yes` · `atualizar-bot\|update-bot BOT VERSAO [--comando C] [--tecnologia T]` · `apagar-versao\|delete-version BOT VERSAO --yes` |
| Automações | `automacoes\|automations [--busca T]` · `automacao\|automation LABEL` · `criar-automacao\|create-automation LABEL [--nome] [--tecnologia] [--runner R] [--param-automacao label:TIPO[:obrigatorio]] [--body @arq]` · `editar-automacao\|edit-automation LABEL --set campo=valor` · `prioridade\|priority LABEL N` · `exportar-automacao\|export-automation LABEL` |
| Tarefas | `tarefas\|tasks [--estado RUNNING] [--automacao L] [--runner R] [--dias 7] [--limite 50]` · `tarefa\|task ID` · `criar-tarefa\|create-task LABEL [-p chave=valor] [--teste] [--prioridade N] [--min-execucao ISO]` · `finalizar-tarefa\|finish-task ID --status SUCCESS\|FAILED\|PARTIALLY_COMPLETED [--mensagem] [--itens total,ok,falha]` · `reiniciar-tarefa\|restart-task ID` · `interromper-tarefa\|interrupt-task ID` · `duplicar-tarefa\|duplicate-task ID` |
| Análise | `analisar\|insights [--dias 7] [--automacao L ...] [--top 10]` · `diagnosticar\|diagnose ID [--dias 30]` |
| Runners | `runners` · `runner ID [--screenshot ARQ] [--log ARQ]` |
| Agendamentos | `agendamentos\|schedules [--busca T]` · `agendamento\|schedule ID` · `criar-agendamento\|create-schedule LABEL --cron "0 30 8 * * MON-FRI" [-p k=v] [--inativo] --yes` · `ativar-agendamento\|enable-schedule ID` · `desativar-agendamento\|disable-schedule ID` · `apagar-agendamento\|delete-schedule ID --yes` |
| Credenciais | `credenciais\|credentials [--busca T]` · `credencial\|credential LABEL [--mostrar]` · `criar-credencial\|create-credential LABEL -s chave=valor ... --yes` · `credencial-chave\|credential-key LABEL CHAVE VALOR` · `remover-chave\|remove-key LABEL CHAVE --yes` · `apagar-credencial\|delete-credential LABEL --yes` |
| Datapool | `datapools [--busca T]` · `datapool LABEL` · `criar-datapool\|create-datapool LABEL --campo nome:TIPO[:id][:exibir] ... [--automacao A] [--politica FIFO] [--gatilho NEVER] [--max-tentativas N] [--tempo-item MIN] --yes` · `datapool-push LABEL -v campo=valor [--prioridade N]` · `ativar-datapool\|enable-datapool LABEL` · `desativar-datapool\|disable-datapool LABEL` · `apagar-datapool\|delete-datapool LABEL --yes` |
| Diagnóstico | `erros\|errors [--automacao L] [--tarefa ID] [--dias N]` · `erro\|error ID [--screenshot ARQ]` · `alertas\|alerts [--automacao L] [--tipo ERROR] [--dias N]` · `logs [LABEL] [--dias N]` · `artefatos\|artifacts [--tarefa ID] [--automacao L]` · `baixar-artefato\|download-artifact ID [--destino P]` |
| Genérico | `endpoints termos [--metodo GET]` · `describe METODO caminho [--resposta]` · `call METODO caminho [-q k=v] [--body JSON\|@arq\|@-] [--arquivo file=CAMINHO] [--saida ARQ] [--todas] [--dry-run] [--yes]` · `indice\|index` |

Os comandos de escrita (criar-*, editar, atualizar, ativar/desativar,
datapool-push, remover-chave, `call`) aceitam `--dry-run` para mostrar
o corpo sem enviar.

Em `call`, escreva o caminho **sem barra inicial** (`task/123`,
`api/v2/task/123` ou `api/v3/tasks/success-rate`); sem a versão, o
script assume `/api/v2`. No Git Bash o script também desfaz a conversão
automática de caminho. Filtros que a spec mostra como objeto
(`automationTaskDTO`, `pageable`, `dateRange`) vão como campos soltos:
`-q days=7 -q states=RUNNING -q size=50`.

### Baixar release

`$BC baixar NFE` baixa a versão **em release** e descompacta em
`<pasta_downloads>/<botId>_<versao>/`. `--versao` pega outra versão e
`--destino` muda a pasta. Se a pasta já tiver arquivos, o script recusa
sem baixar; só use `--sobrescrever` (extrai por cima, nada é apagado) se
a pessoa pedir. Responda com a pasta e a versão baixada.

## Cautela

- **Leituras** (listar, detalhar, analisar, diagnosticar, baixar,
  describe): execute direto.
- **Escritas pedidas explicitamente** (criar tarefa, finalizar,
  reiniciar ou interromper uma tarefa que a pessoa indicou, editar campo
  de automação, criar automação, mudar prioridade, inserir item em fila):
  execute direto e reporte o resultado.
- **Confirme antes** de: qualquer `DELETE` ou exclusão em lote (o script
  exige `--yes`), `release`/rollback (exige `--yes`), criar ou editar
  credencial, criar/editar/(des)ativar agendamento ou datapool,
  editar/remover runner, ações em várias tarefas de uma vez e qualquer
  escrita em produção que a pessoa não pediu literalmente. Na dúvida,
  rode com `--dry-run` e mostre o corpo.
- Só passe `--yes` depois do "pode" da pessoa, nunca por conta própria.
- **Toda exclusão segue dois passos, sem exceção** (apagar versão,
  credencial, chave de cofre, fila, agendamento, tarefa, runner, item de
  fila, log, ou qualquer `call DELETE`/`task/bulk`):
  1. Rode o comando **sem `--yes`**. Ele lê o objeto no Maestro e
     responde `CONFIRMACAO_NECESSARIA` com a seção "O que vai mudar": o
     que será apagado (nome, conteúdo, quantos itens, chaves do cofre
     etc.) e o que continua (ex.: versão em release, chaves restantes).
     Se o objeto não existir, ele avisa e nada acontece.
  2. **Mostre essa prévia à pessoa**, com o ambiente (PROD/QA) em
     destaque, e pergunte se pode apagar. Só depois de um "sim" explícito
     para *essa* exclusão rode o mesmo comando com `--yes`, e confirme
     o resultado. Um "pode" anterior não vale para outra exclusão, e um
     pedido de várias exclusões tem uma prévia para cada uma.
  Nunca apague por um caminho que pule a prévia, por exemplo um script
  próprio ou `requests` direto.
- **Credenciais:** a API devolve os segredos em texto puro. Os atalhos
  mascaram; use `credencial --mostrar` só se a pessoa pedir o valor, e
  nunca imprima na conversa a resposta crua de `call GET credential...`.
- Antes de mexer em versão, release ou agendamento, confira que é o
  bot/automação certo. Famílias de nomes parecidos (`ROBO_NFE_1` /
  `ROBO_NFE_2`) são o erro clássico.

Erros vêm como `HTTP <status>: <corpo>`. 401/403 = chave errada ou
ambiente trocado no config; 404 = label/ID inexistente; 400 = corpo
inválido (rode `describe`).

## Deploy

Publicar um robô em produção é uma ação difícil de desfazer: se o
pacote subir errado, os runners passam a executar código quebrado na
próxima tarefa agendada. Por isso o fluxo é dividido em duas metades,
uma que só lê e propõe e outra que escreve, com uma confirmação humana
no meio. Nunca pule a confirmação.

### 1. Descobrir o projeto e o ambiente

Você precisa de três coisas antes de rodar qualquer script:

- **A pasta do projeto.** Normalmente é a raiz em que a conversa está
  acontecendo. Se a pessoa citou um caminho, use. Se citou só o nome do
  robô ("sobe o NFE"), procure a pasta nas `raizes_projetos` do config.
  Se achar mais de uma, pergunte qual.
- **O ambiente.** O padrão é o `ambiente_padrao` do config. Só use outro
  se a pessoa pedir (ex.: "sobe em homolog" → `QA`).
- **O incremento de versão.** O padrão é `patch` (1.0.3 → 1.0.4c). Se a
  pessoa disser "sobe uma minor", "muda a versão maior" ou algo
  equivalente, passe `--bump minor` ou `--bump major`.

### 2. Gerar o plano (não escreve nada no Maestro)

```bash
python $SK/plan_deploy.py --projeto "C:/Projetos/MeuRobo" [--ambiente PROD] [--bump patch]
```

O script faz login, lista os bots do workspace, casa o nome do projeto
com o `botId`, lê a versão em release e todas as versões cadastradas,
calcula a próxima e classifica os arquivos do projeto. Ele grava um
`.botcity_plano.json` na raiz do projeto e imprime o mesmo conteúdo.

**Bot que ainda não existe no Maestro**: o script avisa que não há
release. Confirme o botId com a pessoa e rode com `--novo --nome
"<botId>" [--tecnologia PYTHON] [--comando "python bot.py"]`. A primeira
versão sai como `1.0.0<sufixo>`. Depois do deploy, ofereça criar a
automação (`criar-automacao`).

Campos que importam no plano:

- `bot_id`, `confianca_match`, `outros_candidatos`: quem ele achou que
  é o robô e com que segurança.
- `precisa_confirmar_bot` / `motivo_confirmacao`: se vier `true`, o
  script não teve segurança para decidir sozinho.
- `versao_atual` → `versao_nova`.
- `arquivos`: o que vai no .zip.
- `revisar`: arquivos que ele não conseguiu decidir sozinho.
- `excluidos_resumo`: o que ficou de fora e por quê.

### 3. Resolver a lista `revisar`

A regra é: **só entra no pacote o que o robô precisa para rodar**.
Código `.py`, `requirements.txt` e recursos que o código realmente usa
entram. Ambiente virtual, `__pycache__`, `.git`, logs, planilhas e CSVs
gerados por execuções antigas, documentação, testes, `.botproj` e
pastas de IDE ficam de fora; o script já resolve esses casos sozinho.

O que sobra em `revisar` é o meio-termo. Para cada item, olhe o código
antes de decidir:

- **Imagens `.png`/`.jpg`**: em robôs de desktop costumam ser templates
  de reconhecimento de tela. Se o código faz `find`, `find_text`,
  `click_on` ou monta caminho para a pasta de recursos, são
  obrigatórias. Na dúvida, inclua: uma imagem a mais custa alguns KB, uma
  a menos quebra o robô.
- **Planilhas e `.csv`**: se for entrada/gabarito que o robô lê, entra.
  Se for saída de execução anterior, fica fora.
- **`config.json`, `.ini`, `.yaml`**: se o robô lê o arquivo em
  runtime, ele precisa ir junto, senão a execução falha no primeiro
  passo. Inclua, mas avise a pessoa que o arquivo está indo no pacote.
- **`.env`, certificados e afins**: mesma regra. Se o robô usa, sobem
  junto, senão a execução quebra em produção. O script detecta o `.env`
  pelo uso de `load_dotenv`/`os.environ`, já que o código quase nunca
  cita o nome do arquivo. Esses caminhos aparecem em
  `sensiveis_incluidos`, e você deve **citá-los pelo nome na
  confirmação** para a pessoa saber que segredo está indo no pacote.
- **`.exe`, `.dll`, executáveis auxiliares**: se o código chama, vão
  junto; confira o tamanho, porque estouram o pacote rápido.
- **`.bat`, `.ps1`, `.sh`**: depende do papel. Script que instala
  dependência ou abre o robô na sua máquina fica de fora. Mas se a
  `tecnologia` do bot for `COMMAND`, o `comando` do plano aponta para um
  desses; aí ele é o ponto de entrada e **tem** que ir.

O classificador trata `.py` como código e o resto pela regra acima. Se o
projeto for JavaScript ou Java, o código-fonte inteiro cai em `revisar`:
é sinal de que o projeto não é Python, não de que os arquivos são
dispensáveis.

Se a lista `revisar` vier com dezenas de itens, não triture item a item.
Quase sempre é uma pasta inteira de runtime vazando (perfil de navegador
do Selenium, cache de driver, downloads); o script avisa quando isso
acontece. Olhe as pastas de topo e trate a causa.

O campo `referenciado_no_codigo` é uma pista automática, não um
veredito: ele acha o nome do arquivo no código, mas erra quando o
caminho é montado dinamicamente. Confirme lendo o trecho relevante.

Para incluir um item, mova o caminho de `revisar` para `arquivos` no
`.botcity_plano.json` e salve. O `run_deploy.py` ignora `revisar`: o
pacote publicado é exatamente a lista `arquivos` que a pessoa aprovou.

### 4. Confirmar com a pessoa

Antes de publicar, mostre um resumo curto e espere o "pode subir":

```
Bot:        ROBO_NFE  (casou com a pasta "robo-nfe")
Ambiente:   PROD (workspace meu-workspace)
Versão:     1.0.3 → 1.0.4c
Pacote:     14 arquivos, 82 KB
Incluídos:  bot.py, orchestrator.py, requirements.txt, config.json, recursos/*.png
Fora:       .venv, __pycache__, logs/, relatorio_*.csv, README.md
```

Dê atenção especial a dois casos:

- **`precisa_confirmar_bot: true`.** Não publique. Mostre o
  `motivo_confirmacao` e os `outros_candidatos`, pergunte qual é o bot e
  refaça o plano com `--nome "<botId exato>"`. Isso acontece quando a
  pasta tem só um prefixo (`NFE`) e o Maestro tem a família inteira
  (`ROBO_NFE_1`, `ROBO_NFE_2`); publicar no irmão errado derruba a
  automação de outra pessoa.
- **`sensiveis_incluidos` não vazio.** Cite cada caminho pelo nome. O
  arquivo vai subir porque o robô precisa dele, mas a pessoa tem que
  ver qual segredo está entrando no pacote antes de aprovar.

Para conferir o pacote antes de subir, gere só o .zip:

```bash
python $SK/run_deploy.py "<projeto>/.botcity_plano.json" --somente-zip
```

### 5. Publicar

```bash
python $SK/run_deploy.py "<projeto>/.botcity_plano.json"
```

O script monta o .zip, cria a versão (`POST /api/v2/bot`), envia o
pacote (`POST /api/v2/bot/upload/...`) e publica (`POST
/api/v2/bot/release`), nessa ordem.

### 6. Responder

Quando der certo, responda **apenas** a mensagem de sucesso, em uma
linha. Quem pediu o deploy quer saber que subiu, não como subiu:

> Robô ROBO_NFE publicado no BotCity (PROD) na versão 1.0.4c.

Sem resumo do que você fez, sem lista de arquivos, sem próximos passos.
Se a pessoa quiser detalhe, ela pergunta.

### Quando o deploy falha

As três chamadas de escrita acontecem em sequência e cada uma pode falhar
sozinha, deixando o Maestro num estado intermediário. O script já
distingue os casos e diz o que ficou pendente. Repasse isso à pessoa em
vez de refazer o deploy por conta própria:

- **Falhou no deploy**: nada mudou, pode tentar de novo.
- **Falhou no upload**: a versão existe, mas está vazia. A versão em
  release continua sendo a anterior. Reenvie ou apague a versão.
- **Falhou no release**: o pacote está lá, só falta publicar:
  `$BC release <bot> <versao> --yes` (depois do ok da pessoa) ou pelo
  Maestro.

Outros erros comuns:

- **401/403 no login**: chave errada ou ambiente errado no config
  (`configurar.py status` / `testar`).
- **413 Content Too Large**: o pacote passou do limite. Quase sempre é
  uma pasta pesada que escapou da classificação; olhe
  `tamanho_estimado_bytes` e o que está em `arquivos`.

### Versionamento

A versão nova nasce da versão **em release**, não da última cadastrada.
Letras no final são descartadas antes do incremento, então `1.0.3` e
`1.0.3c` produzem o mesmo `1.0.4c`. Se a versão calculada já existir no
Maestro, o script continua incrementando o patch até achar uma livre;
reaproveitar um número sobrescreveria um pacote antigo.

Nem toda versão é numérica: há bots com versão tipo `1.0EXECUNICA`.
Nesses casos o incremento descarta o texto (`1.0EXECUNICA` → `1.0.1c`) e
o plano marca `versao_atual_fora_do_padrao: true`. Mostre a proposta e
confirme, já que o nome pode carregar informação que a pessoa quer
preservar.

O sufixo (`sufixo_versao` no config, padrão `c` de Claude) marca o que
subiu pela skill. Não mude sem a pessoa pedir; `--sufixo` sobrescreve
numa execução.

## Referências

- `references/receitas.md`: pegadinhas da API (filtros que funcionam,
  credencial que substitui a lista inteira, datapool que reenvia o
  objeto, 204 no pull, contadores da tarefa, métricas v3, enums). Leia
  antes de escrever via `call`.
- `references/maestro_sdk.md`: referência do Maestro SDK Python gerada
  da doc oficial (assinaturas, parâmetros e trechos dos guias).
- `references/endpoints.md`: índice de todas as operações da API.
- `references/api.md`: detalhes da sequência de deploy.
- `references/openapi.json` + `references/endpoints_extras.json`: o que
  `endpoints`/`describe` consultam (spec oficial + operações fora dela).
- `references/fontes_docs.json` / `docs_snapshot.json`: URLs oficiais e
  o último retrato da documentação.

## Configuração e manutenção

Config em `~/.botcity/config.json` (ou `BOTCITY_CONFIG`): `servidor`,
`ambiente_padrao`, `repositorio_padrao`, `sufixo_versao`,
`pasta_downloads`, `raizes_projetos` e
`ambientes.<NOME>.{workspace,chave}`. A chave pode vir de
`BOTCITY_KEY_<NOME>`. O modelo está em `config.example.json`. Nunca
mostre chaves na conversa.

Manutenção da API: `python $SK/docs_oficiais.py atualizar` baixa a spec
oficial, regenera `references/endpoints.md` e `maestro_sdk.md` e
atualiza o snapshot. Operações que o Maestro aceita mas a spec não
publica ficam em `references/endpoints_extras.json` (edite à mão e rode
`$BC indice`).

Para só conferir a documentação: `python $SK/docs_oficiais.py
verificar` (0 = igual, 10 = mudou, 2 = falha de rede). Se uma URL
oficial mudar, o script reencontra a página pelo sitemap e corrige
`references/fontes_docs.json`.
