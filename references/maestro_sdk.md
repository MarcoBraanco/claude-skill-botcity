# BotCity Maestro SDK (Python) - referencia

Gerado por `scripts/docs_oficiais.py atualizar` a partir da documentacao oficial em 2026-10-21T04:07:52Z. Nao edite a mao.

- Pacote: `botcity-maestro-sdk` (PyPI: 0.9.1)
- Fonte: https://documentation.botcity.dev/maestro/maestro-sdk/python/

## `botcity.maestro.sdk.BotMaestroSDK`

- propriedade `access_token`: The access token

- propriedade `is_online`: Whether or not the object is connected to the BotCity Orchestrator portal

- propriedade `organization`: The organization label

- propriedade `server`: The server address

- propriedade `task_id`: The Current Task ID

- propriedade `timeout`: The timeout for the requests

- propriedade `version`: The BotCity Maestro Backend version

### `__init__(self, server=None, login=None, key=None)`

Main class to interact with the BotMaestro web portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `server` | Optional[str] | None | The server IP or name |
| `login` | Optional[str] | None | The username provided via server configuration. Available under Dev. Environment |
| `key` | Optional[str] | None | The access key provided via server configuration. Available under Dev. Environment |

### `alert(self, task_id, title, message, alert_type)`

Register an alert message on the BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `task_id` | str | required | The activity label |
| `title` | str | required | A title associated with the alert message |
| `message` | str | required | The alert message |
| `alert_type` | AlertType | required | The alert type to be used. See AlertType |

Retorna: `ServerMessage`

### `create_credential(self, label, key, value)`

Create credential in a credentials set

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `label` | str | required | Credential set name |
| `key` | str | required | Key name within the credential set |
| `value` |  | required | Credential value |

### `create_datapool(self, pool)`

Create a new datapool on the BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `pool` | DataPool | required | The DataPool DataPool instance. |

Retorna: `DataPool`

### `create_task(self, activity_label, parameters, test=False, priority=0, min_execution_date=None)`

Creates a task to be executed on the BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `activity_label` | str | required | The activity unique identified. |
| `parameters` | Dict[str, object] | required | Dictionary with parameters and values for this task. |
| `test` | bool | False | Whether or not the task is a test. |
| `priority` | int | 0 | (Optional[int], optional) An integer from 0 to 10 to refer to execution priority. |
| `min_execution_date` | Optional[datetime.datetime] | None | Minimum execution date for the task. |

Retorna: `AutomationTask`

### `delete_log(self, activity_label)`

Fetch log information.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `activity_label` | str | required | The activity unique identifier. |

Retorna: `ServerMessage`

### `error(self, task_id, exception, screenshot=None, attachments=None, tags=None)`

Create a new Error entry.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `task_id` | int | required | The task unique identifier. |
| `exception` | Exception | required | The exception object. |
| `screenshot` | Optional[str] | None | File path for a screenshot to be attached to the error. Defaults to None. |
| `attachments` | Optional[List[str]] | None | Additional files to be sent along with the error entry. Defaults to None. |
| `tags` | Optional[Dict[str, str]] | None | Dictionary with tags to be associated with the error entry. Defaults to None. |

### `finish_task(self, task_id, status, message='', total_items=None, processed_items=None, failed_items=None)`

Finishes a given task.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `task_id` | str | required | The task unique identifier. |
| `status` | AutomationTaskFinishStatus | required | The condition in which the task must be finished. See AutomationTaskFinishStatus |
| `message` | str | '' | A message to be associated with this action. |
| `total_items` | int | None | Total number of items processed by the task. |
| `processed_items` | int | None | Number items processed successfully by the task. |
| `failed_items` | int | None | Number items failed to be processed by the task. |

Retorna: `ServerMessage`

### `get_artifact(self, artifact_id)`

Retrieve an artifact from the BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `artifact_id` | int | required | The artifact unique identifier. |

Retorna: `Tuple[str, bytes]`

### `get_credential(self, label, key)`

Get value in key inside credentials

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `label` | str | required | Credential set name |
| `key` | str | required | Key name within the credential set |

Retorna: `str`

### `get_datapool(self, label)`

Get datapool on the BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `label` | str | required | Label DataPool. |

Retorna: `DataPool`

### `get_execution(self, task_id=None)`

Fetch the BotExecution object for a given task.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `task_id` | Optional[str] | None | The task ID. Defaults to None. |

Retorna: `model.BotExecution`

### `get_log(self, activity_label, date='')`

Fetch log information.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `activity_label` | str | required | The activity unique identifier. |
| `date` | Optional[str] | '' | Initial date for log information in the format DD/MM/YYYY. If empty all information is retrieved. |

Retorna: `List[Dict[str, object]]`

### `get_task(self, task_id)`

Return details about a given task.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `task_id` | str | required | The task unique identifier. |

Retorna: `AutomationTask`

### `interrupt_task(self, task_id)`

Request the interruption of a given task.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `task_id` | str | required | The task unique identifier. |

Retorna: `ServerMessage`

### `list_artifacts(self, days=7)`

List all artifacts available for the organization.

Retorna: `List[botcity.maestro.model.Artifact]`

### `login(self, server=None, login=None, key=None)`

Obtain an access token with the configured BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `server` | Optional[str] | None | The server IP or name |
| `login` | Optional[str] | None | The username provided via server configuration. Available under Dev. Environment |
| `key` | Optional[str] | None | The access key provided via server configuration. Available under Dev. Environment |

### `logoff(self)`

Revoke the access token used to communicate with the BotMaestro portal.

### `message(self, email, users, subject, body, msg_type, group=None)`

Send an email message to the list of email and users given.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `email` | List[str] | required | List of emails to receive the message. |
| `users` | List[str] | required | List of usernames registered on the BotMaestro portal to receive the message. |
| `subject` | str | required | The message subject. |
| `body` | str | required | The message body. |
| `msg_type` | MessageType | required | The message body type. See MessageType |
| `group` | Optional[str] | None | The message group information. |

Retorna: `ServerMessage`

### `new_log(self, activity_label, columns)`

Create a new log on the BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `activity_label` | str | required | The activity unique identifier. |
| `columns` | List[botcity.maestro.model.Column] | required | A list of Columns |

Retorna: `ServerMessage`

### `new_log_entry(self, activity_label, values)`

Creates a new log entry.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `activity_label` | str | required | The activity unique identifier. |
| `values` | Dict[str, object] | required | Dictionary in which the key is the column label and value is the entry value. |

Retorna: `ServerMessage`

### `post_artifact(self, task_id, artifact_name, filepath)`

Upload a new artifact into the BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `task_id` | int | required | The task unique identifier. |
| `artifact_name` | str | required | The name of the artifact to be displayed on the portal. |
| `filepath` | str | required | The file to be uploaded. |

Retorna: `ServerMessage`

### `remove_credential(self, label, key)`

Removes a credential from the set

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `label` | str | required | Credential set name |
| `key` | str | required | Key name within the credential set |

### `restart_task(self, task_id)`

Restarts a given task.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `task_id` | str | required | The task unique identifier. |

Retorna: `ServerMessage`

### `update_credential(self, label, key, new_value)`

Update a credential with a new value

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `label` | str | required | Credential set name |
| `key` | str | required | Key name within the credential set |
| `new_value` |  | required | Credential new value |

## `botcity.maestro.model.AlertType (str, Enum)`

Type of alerts to be emitted.

## `botcity.maestro.model.MessageType (str, Enum)`

Type of message body.

## `botcity.maestro.model.AutomationTaskState (str, Enum)`

State of a Task.

## `botcity.maestro.model.AutomationTaskFinishStatus (str, Enum)`

Finish status of a task.

## `botcity.maestro.model.ServerMessageType (str, Enum)`

The server message type.

## `botcity.maestro.model.ServerMessage`

Server response message.

### `from_json(payload)`

Instantiate a ServerMessage object from a JSON payload obtained from the BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `payload` | str | required | A JSON string containing message and type. |

Retorna: `ServerMessage`

### `to_json(self)`

Returns:

Retorna: `str`

## `botcity.maestro.model.AutomationTask`

Automation Task.

### `from_json(payload)`

Instantiate a AutomationTask object from a JSON payload obtained from the BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `payload` | str | required | A JSON string containing the required metadata. |

Retorna: `AutomationTask`

### `is_interrupted(self)`

Whether or not this task received an interrupt request.

Retorna: `bool`

### `to_json(self)`

Returns:

Retorna: `str`

## `botcity.maestro.model.Artifact`

Artifact.

### `from_dict(data)`

Instantiate a Artifact object from a dict payload obtained from the BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `data` | Dict[str, Any] | required | A dictionary containing the required metadata. |

Retorna: `Artifact`

### `from_json(payload)`

Instantiate a Artifact object from a JSON payload obtained from the BotMaestro portal.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `payload` | str | required | A JSON string containing the required metadata. |

Retorna: `Artifact`

### `to_json(self)`

Returns:

Retorna: `str`

## `botcity.maestro.model.Column`

Representation of a Log column.

## `botcity.maestro.model.BotExecution`

Bot execution parameters.

## `botcity.maestro.datapool.datapool.DataPool`

DataPool(label: str, name: str = None, default_automation: str = None, consumption_policy: str = , trigger: str = , schema: List[botcity.maestro.datapool.datapool.SchemaField] = , auto_retry: bool = True, max_auto_retry: int = 0, abort_on_error: bool = True, max_errors_before_inactive: int = 0, enable_processing_time: bool = True, item_max_processing_time: int = 0, datapool_id: str = None, maestro: 'BotMaestroSDK' = None, active: bool = True, repository_label: str = 'DEFAULT')

### `activate(self)`

Enables the DataPool in Maestro. Returns: None

### `cancel_entry(self, entry_id, finish_message='')`

Cancel an entry in the DataPool by its ID.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `entry_id` | str | required | The ID of the entry to cancel. |
| `finish_message` | Optional, str | '' | A message to be associated with this action. |

Retorna: `DataPoolEntry`

### `create_entry(self, entry)`

Create an entry by DataPool

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `entry` | DataPoolEntry | required | Instance of DataPoolEntry |

Retorna: `DataPoolEntry`

### `deactivate(self)`

Disable DataPool in Maestro. Returns: None

### `delete_entry(self, entry_id)`

Delete an entry in the DataPool by its ID.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `entry_id` | str | required | The ID of the entry to delete. |

### `from_json(payload, maestro)`

Instantiate class by payload to request maestro.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `payload` | bytes | required | Response to maestro. |
| `maestro` | BotMaestroSDK | required | Instance maestro class. |

Retorna: `DataPool`

### `get_entry(self, entry_id)`

Fetch an entry from the DataPool by its ID.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `entry_id` | str | required | The ID of the entry to fetch. |

Retorna: `DataPoolEntry`

### `has_next(self)`

Checks if there are pending items in the DataPool.

Retorna: `bool`

### `is_active(self)`

Check if the DataPool is active. Returns: bool

### `is_empty(self)`

Checks if the DataPool is empty.

Retorna: `bool`

### `next(self, task_id)`

Fetch the next pending entry.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `task_id` | Optional[str] | required | TaskId to be associated with this entry. |

Retorna: `DataPoolEntry or None`

### `summary(self)`

Get the DataPool counters. Returns: dict

### `to_dict(self)`

Get all properties class in dict.

## `botcity.maestro.datapool.entry.DataPoolEntry`

DataPoolEntry(priority: int = 0, values: dict = , datapool_label: str = None, state: str = None, entry_id: str = None, unique_key: str = None, display_value: str = None, message: str = None, error_type: str = None, retry_index: int = 0, runner: str = None, task_id: int = None, parent: str = None, child: str = None, date_register: str = None, date_processing: str = None, date_finished: str = None, maestro: 'BotMaestroSDK' = None)

### `get_value(self, key, default=None)`

Get value by key.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `key` | str | required | Key to get value. |
| `default` | Optional[str] | None | Default value if key not exists. |

### `json_to_update(self)`

Create Json by properties to update.

### `report_done(self, finish_message='')`

Report state DONE to DataPool Entry.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `finish_message` | Optional, str | '' | A message to be associated with this action. |

### `report_error(self, error_type=<ErrorType.SYSTEM: 'SYSTEM'>, finish_message='')`

Report state ERROR to DataPool Entry.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `error_type` | Optional, ErrorType | <ErrorType.SYSTEM: 'SYSTEM'> | The type of error. Defaults to 'SYSTEM' error. |
| `finish_message` | Optional, str | '' | A message to be associated with this action. |

### `save(self)`

Update Entry in DataPool.

### `to_json(self)`

Get properties class in dict.

### `update_from_json(self, payload)`

Update properties by response endpoint Maestro.

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `payload` | bytes | required | Response to endpoint Maestro. |

---

# Guias oficiais (trechos Python)

## setup

Fonte: https://documentation.botcity.dev/maestro/maestro-sdk/setup/

**Import the SDK**

```python
# Importing the package
from botcity.maestro import *
```

**Create a new Maestro client**

```python
# Instantiating a Maestro SDK client
maestro = BotMaestroSDK()
```

**Local execution**

```python
maestro.login(
    server="<SERVER>", 
    login="<LOGIN>", 
    key="<KEY>"
)
```

**Execution via Runner**

```python
# Getting the arguments passed by the Runner
maestro = BotMaestroSDK.from_sys_args()
```

**Get the current execution reference**

```python
# Maestro SDK instance
maestro = BotMaestroSDK.from_sys_args()
# Fetching the details of the current task being executed
execution = maestro.get_execution()

# Information about the task being executed
print(f"Task ID is: {execution.task_id}")
print(f"Task Parameters are: {execution.parameters}")
```

## tarefas

Fonte: https://documentation.botcity.dev/maestro/maestro-sdk/task/

**Create a task**

```python
from datetime import datetime

date = datetime.strptime("09/03/2026 00:00", "%d/%m/%Y %H:%M")
params = {}
task = maestro.create_task(
    activity_label="automationLabel",
    parameters=params,
    test=False,
    priority=5,
    min_execution_date= date
)
```

**Interrupt a task**

```python
maestro.interrupt_task(task_id=<TASK_ID>)
```

**Implementation suggestion**

```python
while not maestro.get_task(task_id=<TASK_ID>).is_interrupted():
    # Continuing to process items
    print("Processing items")
    ...
print("An interruption was requested")
```

**Define data**

```python
maestro.finish_task(
    task_id=<TASK_ID>,
    status=AutomationTaskFinishStatus.SUCCESS,
    message="Task was completed successfully.",
    total_items=100,
    processed_items=90,
    failed_items=10
)
```

**Use the ID of a specific task**

```python
task = maestro.get_task("<TASK_ID>")
```

**Get the current task ID**

```python
# Fetching the details of the task currently being executed
execution = maestro.get_execution()

# Information about the task being executed
print(f"Task ID is: {execution.task_id}")
print(f"Task Parameters are: {execution.parameters}")
```

**Access the parameters of a task**

```python
# Instantiating the Maestro SDK
maestro = BotMaestroSDK.from_sys_args()
# Fetching the details of the task currently being executed
execution = maestro.get_execution()

# Getting parameter by label
parameter1 = execution.parameters.get("<PARAMETER_LABEL1>")
parameter2 = execution.parameters.get("<PARAMETER_LABEL2>")
```

## logs

Fonte: https://documentation.botcity.dev/maestro/maestro-sdk/log/

**Create a log**

```python
# Create a list of columns
columns = [
    Column(name="# Records", label="records"),
    Column(name="Status", label="status"),
]

# Create a new log
maestro.new_log(
    activity_label="logLabel",
    columns=columns
)
```

**Create Log entries**

```python
maestro.new_log_entry(
    activity_label="logLabel",
    values = {
        "records": "10",
        "status": "SUCCESS"
    }
)
```

**Fetch Log data**

```python
# Get the start date as 30 days ago
instant = (datetime.datetime.now() - datetime.timedelta(days=30))
date = instant.strftime("%d/%m/%Y")

# Get the log data
data = maestro.get_log(activity_label="logLabel", date=date)
```

**Download as CSV**

```python
# Not yet implemented
```

**Delete an entire Log**

```python
maestro.delete_log(activity_label="logLabel")
```

## alertas

Fonte: https://documentation.botcity.dev/maestro/maestro-sdk/alerts-and-messages/

**Emit an Alert**

```python
maestro.alert(
    task_id=<TASK_ID>,
    title="Information alert",
    message="This is an information alert",
    alert_type=AlertType.INFO
)
```

**Emit a Message**

```python
# List of emails, if not using, pass an empty list
emails = ["your_email@your_email.com"]
# List of users, if not using, pass an empty list
users = ["orchestrator_user1", "orchestrator_user2"]

# Email subject and body
subject = "Message subject"
email_body = "This is the message content."

maestro.message(
    email=emails, 
    users=users, 
    subject=subject, 
    body=email_body, 
    msg_type=MessageType.TEXT,
    )
```

## credenciais

Fonte: https://documentation.botcity.dev/maestro/maestro-sdk/credential/

**Create credential vaults**

```python
maestro.create_credential(label="vault", key="key1", value="key_value_1")
maestro.create_credential(label="vault", key="key2", value="key_value_2")
```

**Get credential from the Orchestrator**

```python
key1 = maestro.get_credential(label="vault", key="key1")
```

**Update values**

```python
maestro.update_credential(label="vault", key="key1", new_value="new_key_value_1")
```

**Remove a credential key from the Orchestrator**

```python
maestro.remove_credential(label="vault", key="key1")
```

## datapool

Fonte: https://documentation.botcity.dev/maestro/maestro-sdk/datapool/

**Create a Datapool**

```python
# Schema example with fields: 'id', 'name' and 'price'

product_id = SchemaField(
    label="id",
    type=FieldType.TEXT,
    unique_id=True,
    display_value=True
)

product_name = SchemaField(
    label="name",
    type=FieldType.TEXT,
    unique_id=False,
    display_value=True
)

product_price = SchemaField(
    label="price",
    type=FieldType.DOUBLE,
    unique_id=False,
    display_value=False
)

# List with the fields
schema = [product_id, product_name, product_price]

# Creating the Datapool object
datapool = DataPool(
    label="ProductsData",
    name="ProductsData",
    max_auto_retry=2,
    max_errors_before_inactive=5,
    item_max_processing_time=3,
    schema=schema
)

# Creating the Datapool structure in the Orchestrator
maestro.create_datapool(datapool)
```

**Datapool operations**

```python
# Getting the Datapool reference
datapool = maestro.get_datapool("ProductsData")

# Checking if the Datapool is active
print(datapool.is_active())

# Checking if the Datapool has no pending items
print(datapool.is_empty())

# Checking if there is a next pending item
print(datapool.has_next())

# Marking the Datapool as active
datapool.activate()

# Marking the Datapool as inactive
datapool.deactivate()
```

**Add new items**

```python
# Instantiating a new Datapool item based on the defined Schema
new_item = DataPoolEntry(
    values={
        "id": "Electronic#001"
        "name": "Smartphone",
        "price": "2000"
    }
)

# Getting the Datapool reference
datapool = maestro.get_datapool("ProductsData")

# Adding a new item
datapool.create_entry(new_item)
```

**Cancel items**

```python
# Getting the Datapool reference
datapool = maestro.get_datapool("ProductsData")

# Cancelling an item that is pending in the queue
datapool.cancel_entry(
    entry_id="<ENTRY_ID>",
    finish_message="Item with missing data"
)
```

**Delete items**

```python
# Getting the Datapool reference
datapool = maestro.get_datapool("ProductsData")

# Removing an item from the queue
datapool.delete_entry(entry_id="<ENTRY_ID>")
```

**Get items**

```python
# Getting the Datapool reference
datapool = maestro.get_datapool("ProductsData")

# Gets the next item from the Datapool
item_1 = datapool.next(task_id=<TASK_ID>)

# Using the get_entry() method we can also get an item by its ID
item_2 = datapool.get_entry(entry_id="<ENTRY_ID>")
```

**Access item values**

```python
# Getting the value of a specific field from the item
item_data = item["data-label"]

# Using the get_value() method will have the same effect
item_data = item.get_value("data-label")
```

**Report the completion state**

```python
# Gets the next available item from the Datapool
item = datapool.next(task_id=<TASK_ID>)

# Finalizing as 'COMPLETED' after processing
item.report_done(finish_message="Processed successfully!")

# Finalizing item processing indicating a system error
item.report_error(error_type=ErrorType.SYSTEM, finish_message="System unavailable.")

# Finalizing item processing indicating a business error
item.report_error(error_type=ErrorType.BUSINESS, finish_message="Invalid data.")
```

**Suggested Datapool consumption structure**

```python
# Consuming the next available item and reporting the completion state at the end
datapool = maestro.get_datapool(label="Items-To-Process")

while datapool.has_next():
    # Gets the next item from the Datapool
    item = datapool.next(task_id=<TASK_ID>)
    if item is None:
        # The item could be 'None' if another process consumed it first
        break

    try:
        # Processing the item...

        # Finalizing as 'COMPLETED' after processing
        item.report_done(finish_message="Processed successfully!")

    except Exception:
        # Finalizing item processing as 'ERROR'
        item.report_error(finish_message="Processing failed.")
```

## erros

Fonte: https://documentation.botcity.dev/maestro/maestro-sdk/error/

**Create a simple error**

```python
try:
    div = 0 / 0
except Exception as error:
    maestro.error(
        task_id=<TASK_ID>, 
        exception=error
    )
```

**Screenshot**

```python
try:
    div = 0 / 0
except Exception as error:
    file_path = '/home/test/screenshot.png'
    maestro.error(
        task_id=<TASK_ID>, 
        exception=error, 
        screenshot=file_path
    )
```

**Customizable tags**

```python
try:
    div = 0 / 0
except Exception as error:
    tags = {
        "key_1": "value_1",
        "key_2": "value_2",
        "key_3": "value_3",
    }

    maestro.error(
        task_id=<TASK_ID>, 
        exception=error, 
        tags=tags
    )
```

**File attachments**

```python
try:
    div = 0 / 0
except Exception as error:
    attachments = [
        '/home/test/error.png',
        '/home/test/process.log',
        '/home/test/test.txt'
    ]
    maestro.error(
        task_id=<TASK_ID>, 
        exception=error, 
        attachments=attachments
    )
```

## artefatos

Fonte: https://documentation.botcity.dev/maestro/maestro-sdk/result-files/

**Send an artifact**

```python
maestro.post_artifact(
    task_id=<TASK_ID>,
    artifact_name="My artifact.txt",
    filepath="resources/artifact.txt"
)
```

**Listing all artifacts**

```python
artifact = maestro.list_artifacts()
```

**Download an artifact**

```python
# Define artifact ID
artifact_id = "<ARTIFACT_ID>"

# Get artifact name and content
name, content = maestro.get_artifact(artifact_id=artifact_id)

# Write to disk
with open(name, "wb") as file:
    file.write(content)
```
