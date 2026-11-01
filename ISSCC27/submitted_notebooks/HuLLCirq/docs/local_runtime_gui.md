# Start the local LLM from the GUI — updated 2026-10-20

**Local LLM server** was added to the LLM provider section of Global Settings in
response to the request to manage startup through the GUI. On a prepared host,
the browser can start the server, inspect its status and stop it without a
separate model terminal.

1. Open a project and an editable system, then save a Local connection profile.
2. Select **Start local LLM**. Status updates automatically from Starting to Running.
3. Select **Test Connection** to check access to the model list through the saved profile.
4. Select **Stop local LLM** when finished. For a status-only check, use **Refresh server status**.

Start and Stop run asynchronously and return status to the GUI while startup is
in progress. The startup controller does not perform the state-saving Test
Connection action, inference, RTL generation, EDA or stage verification. It uses
only the bounded metadata GET requests `GET /api/version` and `GET /v1/models`.
Test Connection also retrieves the model list; it does not verify generation
capability or circuit behavior. However, Test Connection saves its probe result
and timestamp to the current system's generation store. During a migration check
that must preserve byte identity, read the service's two GET endpoints directly
and do not run Test Connection.

Initial GPU discovery on the new multi-GPU host took more than 30 seconds, so
the metadata-only startup wait is 120 seconds. This is not the model-generation
timeout. It bounds only asynchronous server startup and the version/model-list
checks.

## Supported environment at this checkpoint

The startup target saved for the current eleven-node NPU is the isolated Windows
Ollama **0.32.15**, isolated model **qwen2.5-coder:7b**, and
`http://<ADDRESS>:11435/v1` (the profile may also use the localhost spelling).
If the parent GUI process has no `OLLAMA_CONTEXT_LENGTH`, it passes the saved
profile's 32,768 value to the child process; an existing parent value takes
precedence. Inspect `context_length_source` in the status to see the actual
source. Models are stored in `.work/m2/ollama-models`. The controller checks
manifest SHA-256
`dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`
and the existence and sizes of its referenced blobs; it does not download a
model automatically. The older `qwen3:8b` is also supported with its pinned
historical manifest. It remains a separate model, without rewriting earlier
records.

On a migrated host with restored design data and a pinned model cache, follow
the public setup procedure (historical development reference; not included in
this curated archive), extract the official pinned archive into
`.work/m2/ollama-0.32.15/`, and pass its executable to the GUI service with
`--ollama-path`. Do not stop or replace a normal Ollama installation, such as
0.40.4 running on port 11434. Specify the managed port 11435 when checking the
executable's version. There is no API for sending arbitrary executable paths or
shell commands from the browser. Network profiles, other models and profiles
using other ports retain the existing connection-test and generation routes;
they are not startup targets of this fixed runtime.

For the current profile's manual fallback, specify all pinned values explicitly
from the HuLLCirq directory. This is a foreground service; stop it with Ctrl+C.

```powershell
$LocalRuntime = Get-Content .work/m2/local_runtime.json -Raw | ConvertFrom-Json
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_local_llm.ps1 `
  -OllamaPath $LocalRuntime.executable `
  -Model qwen2.5-coder:7b `
  -ContextLength 32768
```

## Ownership and persistence

The controller is shared by the GUI service and does not exit when projects
change. It can stop only a live process handle that the same controller started
and retained. A server started by another method is shown as Running / externally
started, with Stop disabled. Ownership of an existing process is not inferred
from its PID alone.

LocalRuntimeController binds only to loopback, starts the process hidden without
a shell, and sets `OLLAMA_HOST`, `OLLAMA_MODELS`, `OLLAMA_NO_CLOUD=1` and related
values only in the child process. It does not change user-wide environment
variables. Logs are saved under `.work/local_runtime/`. Normal GUI service
shutdown stops the owned server. Cleanup of model-runner child processes after
inference was not demonstrated by this metadata-only check.

The new API uses the workspace session and existing Origin restrictions.
Read-only snapshots cannot start or stop the runtime, and their GUI hides the
management controls. Startup and shutdown are rejected while a generation or
EDA worker is running. These operations do not change design inputs, RTL
candidates, verification history or adoption records.

## Observed verification scope

In the older Qwen3 environment on 2026-10-13, the actual GUI showed Stop disabled
for an externally started server, Stopped -> Starting -> Running, Connected
after Test Connection, and Stopped after GUI Stop. Running / Connected was also
confirmed after restart. The older environment's focused software and GUI
records are historical development references not included in this curated
archive.

In the migration environment on 2026-10-20, the current Qwen2.5 profile with
context 32,768 completed the GUI-managed Stopped -> Starting -> Running / owned
-> Stop -> Stopped sequence. `/api/version` reported 0.32.15 and `/v1/models`
listed `qwen2.5-coder:7b`. Multi-GPU discovery took about 32 seconds, prompting
the startup wait increase to 120 seconds. This check used read-only metadata
endpoints, and all 11 current store hashes matched the S07 saved collection
(historical development reference; not included in this curated archive).
The migration verification record (historical development reference; not
included in this curated archive) retains versions, hashes, failures,
corrections and the stopped state. No circuit flow, LLM inference, RTL generation
or EDA was executed. The manual fallback `start_local_llm.ps1` accepts explicit
model and context settings and retains the older Qwen3 defaults for historical
reproduction.
