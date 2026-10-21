<div align="center">

# BotCity Maestro Skill for Claude Code

**Gives Claude Code direct access to BotCity Maestro: it looks up tasks, logs and errors on its own, deploys bots and manages queues, credentials and schedules.**

[![Python](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-D97757)](https://claude.com/claude-code)
[![BotCity Maestro](https://img.shields.io/badge/BotCity-Maestro-1F6FEB)](https://documentation.botcity.dev/maestro/maestro-api/maestro-api/)
[![Code style: PEP 8](https://img.shields.io/badge/code%20style-PEP%208-informational)](https://peps.python.org/pep-0008/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[Português](README.md) | English

</div>

---

## Overview

A [skill](https://claude.com/claude-code) that connects Claude Code to the BotCity Maestro API. You describe what you want, and Claude runs the sequence of calls, checks the result and asks for confirmation before any destructive operation.

```text
> deploy this bot to QA as a minor version
> why did task 123456 fail?
> schedule ROBO_NFE at 8:30 on weekdays
```

Works with any workspace, **cloud or on-premise**.

## Highlights

- **Reproducible deploys**: packages the project, skips caches and build artifacts, shows the package manifest before uploading and releases the version.
- **One-call diagnosis**: pulls the task, errors, alerts, runner and recent automation history into a single answer.
- **Safety guardrails**: explicit confirmation in production, masked secrets, a dry run of whatever is about to be deleted.
- **Raw API fallback**: when there's no ready-made shortcut for a request, Claude finds the endpoint in the Maestro API and calls it directly.
- **Standalone CLI**: every script runs without Claude.

## Quick start

### Prerequisites

- [Claude Code](https://claude.com/claude-code)
- Python 3.8+
- A BotCity Maestro access key (Maestro → **Dev. Environment**)

### Installation (recommended)

Paste into Claude Code:

```text
Install the BotCity skill for me in Claude Code's default skills
location: clone https://github.com/MarcoBraanco/claude-skill-botcity.git,
install the requests package with pip and then run the skill's
first-time setup (scripts/configurar.py), asking me for whatever you
need.
```

> If Claude doesn't pick up BotCity requests afterwards, restart Claude Code so the skill gets loaded.

### Manual installation

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

Then ask Claude Code: `set up BotCity`.

## Setup

On first run, the skill asks for:

| Item | Example |
|---|---|
| Maestro URL | `https://your-workspace.botcity.dev` |
| Workspace per environment | `PROD`, `QA` |
| Downloads and projects folders | `~/bots`, `~/projects` |

To find these, open the orchestrator (Maestro) and go to **Dev. Environment** ("Ambiente do desenvolvedor" in Portuguese): it shows the Workspace, the Login and the access Key. Claude points you there before asking.

The configuration lives in `~/.botcity/config.json`, **outside** the skill folder. Updating the skill (`git pull`) doesn't overwrite your settings.

### Access key

Prefer an environment variable over pasting the key into the chat:

```bash
export BOTCITY_KEY_PROD="your-key"     # Linux/macOS
setx BOTCITY_KEY_PROD "your-key"       # Windows
```

Alternatives:

- Edit `~/.botcity/config.json` and fill in the `chave` field.
- Send the key in the chat for Claude to save. It works, but the key stays in the conversation history.

### Versioning

Versions published by the skill get the `c` suffix (`1.0.3` → `1.0.4c`), so you can tell in Maestro what went up through Claude and what went up by hand. The suffix can be removed or changed on request.

## What you can do

Requests can be made in English or Portuguese.

| Area | Example request |
|---|---|
| Automation health | `how are the bots doing this week?` · `which automations keep failing in a row?` |
| Diagnosis | `why did task 123456 fail?` · `show yesterday's ROBO_NFE errors with the screenshot` |
| Releases | `download the ROBO_NFE release` (already unzipped) |
| Deploy | `deploy this bot` · `publish a minor version to QA` · `publish this project as a new bot called ROBO_BOLETOS` |
| Rollback | `roll ROBO_NFE back to the previous version` |
| Datapools | `create a datapool INVOICES with the fields key and amount` · `how many pending items are in the queue?` |
| Credentials | `create an SAP credential with user and password` · `change the password in the SAP vault` |
| Schedules | `schedule ROBO_NFE at 8:30 on weekdays` · `pause that schedule` |
| Tasks | `run ROBO_NFE with date=2026-01-31` · `interrupt task 123` |
| Runners | `which runners are offline?` |

## CLI

The scripts work straight from the terminal, without Claude:

```bash
BC="python ~/.claude/skills/botcity/scripts/botcity.py"

$BC insights --days 7            # automation health over the last 7 days
$BC diagnose 123456              # full diagnosis of a task
$BC tasks --state RUNNING        # running tasks
$BC download ROBO_NFE            # downloads and extracts the release
```

| Command | Portuguese name |
|---|---|
| `insights` | `analisar` |
| `diagnose` | `diagnosticar` |
| `tasks` | `tarefas` |
| `download` | `baixar` |

Full list: `python botcity.py --help`. Script messages are in Portuguese; Claude replies in whatever language you write in.

## Safety

| Operation | Behavior |
|---|---|
| Deletions | Shows the impact first ("deletes the INVOICES datapool and its 1,250 items, 30 still pending") and only runs after confirmation |
| Release, rollback, credentials, schedules and datapools | Require explicit confirmation |
| Passwords and keys | Always masked unless the value is requested |
| Deploy | Lists the package files before uploading; sensitive files (e.g. `.env`) are named explicitly |
| Ambiguous names | Bots with similar names trigger a question, never a guess |

The skill operates strictly within the permissions of your Maestro access key.

## Motivation

I work with RPA and used Claude to analyze my automations. What took time was the preparation: downloading logs and tasks, putting everything together and only then bringing it to Claude for analysis.

The skill gives Claude direct access to Maestro. It fetches what it needs on its own (tasks, logs, errors, alerts, history) and gets to the answer, without me having to assemble that material first. Nothing that deletes data or touches production happens without confirmation.

## Limitations

- Deploys were designed for **Python** projects. Java or JavaScript projects work, but need more manual review of the package files.
- The health overview depends on Maestro's **v3 API**, which may not exist on older on-premise installs.
- What the skill can do is limited by the permissions of the configured access key.

## License

Distributed under the [MIT](LICENSE) license.

Personal project, not officially affiliated with BotCity.
