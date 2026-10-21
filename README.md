<div align="center">

# BotCity Maestro Skill para Claude Code

**Dá ao Claude Code acesso direto ao BotCity Maestro: ele consulta tarefas, logs e erros por conta própria, publica robôs e gerencia filas, credenciais e agendamentos.**

[![Python](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-D97757)](https://claude.com/claude-code)
[![BotCity Maestro](https://img.shields.io/badge/BotCity-Maestro-1F6FEB)](https://documentation.botcity.dev/maestro/maestro-api/maestro-api/)
[![Code style: PEP 8](https://img.shields.io/badge/code%20style-PEP%208-informational)](https://peps.python.org/pep-0008/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Português | [English](README.en.md)

</div>

<!-- Dica: um GIF curto aqui (ex.: "por que a tarefa X falhou?" → resposta) vale mais que qualquer parágrafo. -->

---

## Visão geral

Uma [skill](https://claude.com/claude-code) que conecta o Claude Code à API do BotCity Maestro. Você descreve o que quer, e o Claude executa a sequência de chamadas, valida o resultado e pede confirmação antes de qualquer operação destrutiva.

```text
> sobe esse robô em homolog como minor
> por que a tarefa 123456 falhou?
> agenda o ROBO_NFE para 8h30 em dias úteis
```

Compatível com qualquer workspace, **cloud ou on-premise**.

## Destaques

- **Deploy reproduzível**: empacota o projeto, ignora caches e artefatos de build, mostra o manifesto do pacote antes de subir e publica a versão.
- **Diagnóstico em uma chamada**: agrega tarefa, erros, alertas, runner e histórico recente da automação numa resposta só.
- **Guardrails de segurança**: confirmação explícita em produção, secrets mascarados, dry-run do que será apagado.
- **Fallback para a API crua**: sem atalho pronto para o pedido, o Claude localiza o endpoint na API do Maestro e chama direto.
- **CLI independente**: todos os scripts rodam sem o Claude.

## Quick start

### Pré-requisitos

- [Claude Code](https://claude.com/claude-code)
- Python 3.8+
- Uma chave de acesso do BotCity Maestro (Maestro → **Ambiente do desenvolvedor**)

### Instalação (recomendada)

Cole no Claude Code:

```text
Instala a skill do BotCity pra mim no local padrão de skills do Claude
Code: clona o repositório
https://github.com/MarcoBraanco/claude-skill-botcity.git, instala o
pacote requests com pip e depois roda a configuração inicial da skill
(scripts/configurar.py), me perguntando o que precisar.
```

> Se o Claude não reconhecer pedidos de BotCity depois disso, reinicie o Claude Code para a skill ser carregada.

### Instalação manual

**Linux / macOS**

```bash
git clone https://github.com/MarcoBraanco/claude-skill-botcity.git ~/.claude/skills/botcity
pip install requests
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/MarcoBraanco/claude-skill-botcity.git "$env:USERPROFILE\.claude\skills\botcity"
pip install requests
```

Depois, peça no Claude Code: `configura a skill do BotCity`.

## Configuração

Na primeira execução, a skill coleta:

| Item | Exemplo |
|---|---|
| URL do Maestro | `https://seu-workspace.botcity.dev` |
| Workspace por ambiente | `PROD`, `QA` |
| Diretório de downloads e de projetos | `~/robos`, `~/projetos` |

Para pegar esses dados, entre no orquestrador (Maestro) e abra o menu **Ambiente do desenvolvedor**: lá estão o Workspace, o Login e a Chave de acesso. O Claude orienta isso antes de perguntar.

A configuração fica em `~/.botcity/config.json`, **fora** do diretório da skill. Atualizar a skill (`git pull`) não sobrescreve suas configurações.

### Chave de acesso

Prefira variável de ambiente em vez de colar a chave no chat:

```bash
export BOTCITY_KEY_PROD="sua-chave"     # Linux/macOS
setx BOTCITY_KEY_PROD "sua-chave"       # Windows
```

Alternativas:

- Editar `~/.botcity/config.json` e preencher o campo `chave`.
- Enviar a chave no chat para o Claude gravar. Funciona, mas a chave fica no histórico da conversa.

### Versionamento

Versões publicadas pela skill recebem o sufixo `c` (`1.0.3` → `1.0.4c`), o que permite distinguir no Maestro o que subiu via Claude e o que subiu manualmente. O sufixo pode ser removido ou trocado a pedido.

## O que dá pra fazer

Os pedidos podem ser feitos em português ou inglês.

| Área | Exemplo de pedido |
|---|---|
| Saúde das automações | `como estão os robôs essa semana?` · `quais automações estão falhando em sequência?` |
| Diagnóstico | `por que a tarefa 123456 falhou?` · `mostra os erros do ROBO_NFE de ontem com o screenshot` |
| Releases | `baixa o release do ROBO_NFE` (já descompactado) |
| Deploy | `sobe esse robô` · `publica uma minor em homolog` · `publica esse projeto como um bot novo chamado ROBO_BOLETOS` |
| Rollback | `volta o ROBO_NFE para a versão anterior` |
| Datapools | `cria um datapool NOTAS com os campos chave e valor` · `quantos itens pendentes tem a fila?` |
| Credenciais | `cria uma credencial SAP com usuário e senha` · `troca a senha do cofre SAP` |
| Agendamentos | `agenda o ROBO_NFE para 8h30 em dias úteis` · `pausa esse agendamento` |
| Tarefas | `dispara o ROBO_NFE com data=2026-01-31` · `interrompe a tarefa 123` |
| Runners | `quais runners estão offline?` |

## CLI

Os scripts funcionam direto no terminal, sem o Claude:

```bash
BC="python ~/.claude/skills/botcity/scripts/botcity.py"

$BC analisar --dias 7            # saúde das automações nos últimos 7 dias
$BC diagnosticar 123456          # diagnóstico completo de uma tarefa
$BC tarefas --estado RUNNING     # tarefas em execução
$BC baixar ROBO_NFE              # baixa e extrai o release
```

| Comando | Alias em inglês |
|---|---|
| `analisar` | `insights` |
| `diagnosticar` | `diagnose` |
| `tarefas` | `tasks` |
| `baixar` | `download` |

Lista completa: `python botcity.py --help`.

## Segurança

| Operação | Comportamento |
|---|---|
| Exclusões | Mostra o impacto antes ("apaga a fila NOTAS e os 1.250 itens dela, 30 ainda pendentes") e só executa após confirmação |
| Release, rollback, credenciais, agendamentos e filas | Exigem confirmação explícita |
| Senhas e chaves | Sempre mascaradas, exceto se o valor for pedido |
| Deploy | Lista os arquivos do pacote antes do upload; arquivos sensíveis (ex.: `.env`) são citados pelo nome |
| Nomes ambíguos | Bots com nomes parecidos geram pergunta, nunca palpite |

A skill opera estritamente dentro das permissões da sua chave de acesso no Maestro.

## Motivação

Trabalho com RPA e usava o Claude para analisar as automações. O que tomava tempo era a preparação: baixar logs e tarefas, juntar tudo e só então levar para o Claude analisar.

A skill dá ao Claude acesso direto ao Maestro. Ele mesmo busca o que precisa (tarefas, logs, erros, alertas, histórico) e chega à resposta, sem que eu tenha que montar esse material antes. Nada que apague dados ou mexa em produção acontece sem confirmação.

## Limitações

- O deploy foi pensado para projetos **Python**. Projetos Java ou JavaScript funcionam, mas exigem mais revisão manual dos arquivos do pacote.
- A análise de saúde depende da **API v3** do Maestro, que pode não existir em instalações on-premise mais antigas.
- O escopo de ação é limitado pelas permissões da chave de acesso configurada.

## Licença

Distribuído sob a licença [MIT](LICENSE).

Projeto pessoal, sem vínculo oficial com a BotCity.
