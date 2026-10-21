# BotCity Maestro - indice de endpoints

Gerado por `botcity.py indice` a partir de `openapi.json` + `endpoints_extras.json`. Detalhes de cada um: `botcity.py describe METODO caminho`.

## 00 - Setup & Auth

| Metodo | Caminho | Resumo |
|---|---|---|
| POST | `/api/v2/workspace/login` | Login - Workspace *(fora da spec)* |

## Automations

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/activity` | Automation - List *(fora da spec)* |

## Bots

| Metodo | Caminho | Resumo |
|---|---|---|
| DELETE | `/api/v2/bot/{botId}/version/{botVersion}` | Bot - Delete Version *(fora da spec)* |

## Datapool

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/datapool` | Datapool - List *(fora da spec)* |
| POST | `/api/v2/datapool` | Datapool - Create *(fora da spec)* |
| DELETE | `/api/v2/datapool/{datapoolLabel}` | Datapool - Delete *(fora da spec)* |
| GET | `/api/v2/datapool/{datapoolLabel}` | Datapool - Get *(fora da spec)* |
| POST | `/api/v2/datapool/{datapoolLabel}` | Datapool - Activate / Datapool - Deactivate *(fora da spec)* |
| DELETE | `/api/v2/datapool/{datapoolLabel}/entry/{entryId}` | Datapool - Delete Entry *(fora da spec)* |
| GET | `/api/v2/datapool/{datapoolLabel}/entry/{entryId}` | Datapool - Get Entry *(fora da spec)* |
| POST | `/api/v2/datapool/{datapoolLabel}/entry/{entryId}` | Datapool - Update Entry (Report Done/Error) *(fora da spec)* |
| PUT | `/api/v2/datapool/{datapoolLabel}/entry/{entryId}/cancel` | Datapool - Cancel Entry *(fora da spec)* |
| GET | `/api/v2/datapool/{datapoolLabel}/pull` | Datapool - Pull Next Item *(fora da spec)* |
| POST | `/api/v2/datapool/{datapoolLabel}/push` | Datapool - Add Item *(fora da spec)* |
| GET | `/api/v2/datapool/{datapoolLabel}/summary` | Datapool - Summary *(fora da spec)* |
| GET | `/api/v2/datapool/{datapoolLabel}/view` | Datapool - View *(fora da spec)* |

## Logs

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/log` | Log - List *(fora da spec)* |
| POST | `/api/v2/log` | Log - Create *(fora da spec)* |
| DELETE | `/api/v2/log/{logLabel}` | Log - Delete *(fora da spec)* |
| GET | `/api/v2/log/{logLabel}` | Log - Fetch Header *(fora da spec)* |
| POST | `/api/v2/log/{logLabel}/entry` | Log - Create Entry *(fora da spec)* |
| GET | `/api/v2/log/{logLabel}/entry-list` | Log - Fetch Entries *(fora da spec)* |
| GET | `/api/v2/log/{logLabel}/export` | Log - Export *(fora da spec)* |

## agent-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/agent` | Agent - List |
| GET | `/api/v2/agent/{botId}` | Agent - Get |

## alert-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/alerts` | Alert - List / Alert - Get Warnings |
| POST | `/api/v2/alerts` | Alert - Create |
| GET | `/api/v2/alerts/analytics/count` | Alert - Analytics Count |
| GET | `/api/v2/alerts/count` | Alert - Count |
| GET | `/api/v2/alerts/occurrences` | countOccurrences |
| GET | `/api/v2/alerts/{id}` | Alert - Get |

## alert-v-3-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v3/alerts/count-by-automation` | countByAutomation |

## artifact-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/artifact` | Result File - List |
| POST | `/api/v2/artifact` | Result File - Create Register |
| POST | `/api/v2/artifact/log/{artifactId}` | Result File - Upload File |
| GET | `/api/v2/artifact/{artifactId}` | Result File - Get Register |
| GET | `/api/v2/artifact/{artifactId}/file` | Result File - Get File |

## audit-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/audit` | Audit - List |
| POST | `/api/v2/audit` | Audit - Register |
| GET | `/api/v2/audit/{type}` | Audit - Get By Type |

## automation-activity-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| POST | `/api/v2/activity` | Automation - Create |
| GET | `/api/v2/activity/count` | Automation - Count |
| POST | `/api/v2/activity/import` | Automation - Import |
| GET | `/api/v2/activity/pagination` | Automation - List (Paginated) |
| GET | `/api/v2/activity/{activityLabel}` | Automation - Get |
| POST | `/api/v2/activity/{activityLabel}` | Automation - Update (DEPRECATED) **(deprecated)** |
| GET | `/api/v2/activity/{activityLabel}/icon` | Automation - Get Icon |
| POST | `/api/v2/activity/{activityLabel}/icon` | Automation - Upload Icon |
| PATCH | `/api/v2/activity/{automationLabel}` | Automation - Update (PATCH) |
| PUT | `/api/v2/activity/{automationLabel}/priority/{priority}` | Automation - Change Priority |
| GET | `/api/v2/activity/{label}/export` | Automation - Export |

## automation-task-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/task` | Task - List |
| POST | `/api/v2/task` | Task - Create |
| GET | `/api/v2/task/analytics/error-count` | Analytics - Error Count |
| GET | `/api/v2/task/analytics/state-count` | Analytics - State Count |
| DELETE | `/api/v2/task/bulk` | Task - Bulk Delete |
| GET | `/api/v2/task/check-task-finished` | Task - Check Finished |
| GET | `/api/v2/task/check-task-finished-success` | Task - Check Finished With Success |
| GET | `/api/v2/task/historical-overview/count` | Overview - Count |
| GET | `/api/v2/task/historical-overview/count-by-state` | Overview - Count By State |
| GET | `/api/v2/task/historical-overview/count-failed-by-automation` | Overview - Failed By Automation |
| GET | `/api/v2/task/live-operation/count` | Live Operation - Automations Count |
| GET | `/api/v2/task/live-operation/scheduling/count` | Live Operation - Schedulings Count |
| GET | `/api/v2/task/report` | Task - Report |
| DELETE | `/api/v2/task/{taskId}` | Task - Delete |
| GET | `/api/v2/task/{taskId}` | Task - Get |
| POST | `/api/v2/task/{taskId}` | Task - Finish / Task - Restart / Task - Interrupt |
| POST | `/api/v2/task/{taskId}/duplicate` | Task - Duplicate |

## automation-v-3-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v3/automations/count` | countActivities |

## bot-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/bot` | Bot - List |
| POST | `/api/v2/bot` | Bot - Deploy |
| GET | `/api/v2/bot/pagination` | Bot - List (Paginated) |
| POST | `/api/v2/bot/release` | Bot - Release |
| POST | `/api/v2/bot/update` | Bot - Update |
| POST | `/api/v2/bot/upload/{botId}/version/{botVersion}` | Bot - Upload Package |
| GET | `/api/v2/bot/{botId}` | Bot - Get Released |
| GET | `/api/v2/bot/{botId}/version/{botVersion}` | Bot - Get Version |
| GET | `/api/v2/bot/{idDeploy}/version/{version}/download` | Bot - Download Package |

## credential-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/credential` | Credential - List |
| POST | `/api/v2/credential` | Credential - Create |
| GET | `/api/v2/credential/hs` | Credential - List (Front) |
| GET | `/api/v2/credential/pagination` | Credential - List (Paginated) |
| DELETE | `/api/v2/credential/{label}` | Credential - Delete Vault |
| GET | `/api/v2/credential/{label}` | Credential - Get Vault |
| POST | `/api/v2/credential/{label}` | Credential - Edit Vault |
| GET | `/api/v2/credential/{label}/hs` | Credential - Get Vault (Front) |
| POST | `/api/v2/credential/{label}/key` | Credential - Add/Update Key |
| GET | `/api/v2/credential/{label}/key/{key}` | Credential - Get Key |

## download-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/download/{item}/latest` | Download - Get Latest |

## error-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/error` | Error - List / Error - Get Automation Errors |
| POST | `/api/v2/error` | Error - Create |
| GET | `/api/v2/error/{id}` | Error - Get |
| POST | `/api/v2/error/{id}/attachments` | Error - Upload Attachment |
| GET | `/api/v2/error/{id}/attachments/{attachmentIndex}` | Error - Get Attachment |
| GET | `/api/v2/error/{id}/screenshot` | Error - Get Screenshot |
| POST | `/api/v2/error/{id}/screenshot` | Error - Upload Screenshot |

## error-v-3-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v3/errors/count` | countErrors |
| GET | `/api/v3/errors/count-by-automation` | countErrorsByAutomation |

## event-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| POST | `/api/v2/event` | Event - Register |
| GET | `/api/v2/event/list` | Event - List By Organization |
| GET | `/api/v2/event/{type}` | Event - Get By Type |
| POST | `/api/v2/log/event` | Event - Register Log (DEPRECATED) **(deprecated)** |
| POST | `/api/v2/log/studio` | Event - Register Studio (DEPRECATED) **(deprecated)** |

## machine-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| POST | `/api/v2/machine` | Runner - Register |
| GET | `/api/v2/machine/` | Runner - List |
| GET | `/api/v2/machine/analytics/status-count` | Runner - Analytics Status Count |
| GET | `/api/v2/machine/analytics/tasks-by-runner` | Runner - Analytics Tasks By Runner |
| GET | `/api/v2/machine/log/{machineId}` | Runner - Get Log |
| POST | `/api/v2/machine/log/{machineId}` | Runner - Upload Log |
| GET | `/api/v2/machine/pagination` | Runner - List (Paginated) |
| GET | `/api/v2/machine/screenshot/{machineId}` | Runner - Get Screenshot |
| POST | `/api/v2/machine/screenshot/{machineId}` | Runner - Upload Screenshot |
| DELETE | `/api/v2/machine/{machineId}` | Runner - Delete |
| GET | `/api/v2/machine/{machineId}` | Runner - Get Info |
| POST | `/api/v2/machine/{machineId}` | Runner - Edit |
| GET | `/api/v2/machine/{machineId}/tasks-summary` | Runner - Get Tasks Summary |

## maestro-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/maestro/location` | Maestro - User Location |
| GET | `/api/v2/maestro/version` | Maestro - Version |

## message-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| POST | `/api/v2/message` | Message - Send |

## private-audit-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| POST | `/private/audit` | Audit - Register (Private) |

## runner-v-3-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v3/runners/count` | count |
| GET | `/api/v3/runners/count-by-state` | countRunnersByState |

## scheduling-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v2/scheduling` | Schedule - List |
| POST | `/api/v2/scheduling` | Schedule - Create |
| GET | `/api/v2/scheduling/analytics/active/count` | Schedule - Analytics Active Count |
| GET | `/api/v2/scheduling/count` | Schedule - Count |
| GET | `/api/v2/scheduling/occurrences` | Schedule - Occurrences |
| GET | `/api/v2/scheduling/occurrences/peak-scheduling-days` | Schedule - Peak Scheduling Days |
| GET | `/api/v2/scheduling/occurrences/top-automations` | Schedule - Top Automations |
| GET | `/api/v2/scheduling/occurrences/top-runners` | Schedule - Top Runners |
| POST | `/api/v2/scheduling/validate-cron` | Schedule - Validate Cron |
| DELETE | `/api/v2/scheduling/{schedulingId}` | Schedule - Delete |
| GET | `/api/v2/scheduling/{schedulingId}` | Schedule - Get |
| POST | `/api/v2/scheduling/{schedulingId}` | Schedule - Update |

## task-v-3-controller

| Metodo | Caminho | Resumo |
|---|---|---|
| GET | `/api/v3/tasks/count-by-automation` | countTasksByAutomation |
| GET | `/api/v3/tasks/count-by-repository` | countByRepository |
| GET | `/api/v3/tasks/count-by-runner` | countByRunner |
| GET | `/api/v3/tasks/count-by-state` | getTaskCountByState |
| GET | `/api/v3/tasks/count-completed-by-state` | countCompletedByState |
| GET | `/api/v3/tasks/count-consecutive-failures` | countConsecutiveFailures |
| GET | `/api/v3/tasks/count-executions` | countExecutions |
| GET | `/api/v3/tasks/count-failed-by-automation` | countFailedByAutomation |
| GET | `/api/v3/tasks/count-item-success` | countItemSuccess |
| GET | `/api/v3/tasks/count-scheduled-executions` | countScheduledExecutions |
| GET | `/api/v3/tasks/count-scheduling` | getSchedulingCount |
| GET | `/api/v3/tasks/evolution-over-time` | evolutionOverTime |
| GET | `/api/v3/tasks/success-rate` | getSuccessRate |
