# Configuration Reference

Configuration is loaded from environment variables first and then from the editable UI state file.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8068` | Flask development server port. Gunicorn uses `8068` in Docker. |
| `APP_VERSION` | `0.1.0` | Version shown by `/version` and `/healthz`. |
| `LLM_UI_DATA_DIR` | `runtime/ui-data` locally, `/data` in Docker | Persistent UI state, logs, conversations, jobs, and uploaded datasets. |
| `LLM_UI_DEFAULT_MODEL` | `llama3.2:3b` | Default model selected by the UI. |
| `LLM_UI_TIMEOUT` | `300` | Request timeout for model operations. |
| `LLM_UI_MAX_CHAT_CHARS` | `48000` | Input guardrail for prompts and history. |
| `LLM_UI_ALLOW_SHELL_JOBS` | `0` | Reserved switch for future local job execution. Keep disabled unless you trust the UI users. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` locally, `http://ollama:11434` in Compose | Ollama API URL. |
| `OPENAI_BASE_URL` | `$OLLAMA_BASE_URL/v1` | OpenAI-compatible endpoint URL. |
| `HOST_WORKER_STATUS_URL` | empty | Optional host worker GPU status endpoint. |
| `HOST_WORKER_BIND` | `0.0.0.0` | Host worker bind address. |
| `HOST_WORKER_PORT` | `8090` | Host worker port. |

## Editable UI Settings

The Settings page allows safe edits for:

- Ollama URL
- OpenAI-compatible URL
- Host worker status URL
- Default model
- Refresh interval
- Process filters
- Sampling profiles

These values are saved in `state.json` under `LLM_UI_DATA_DIR`.

## Network Notes

When the UI runs inside Docker and Ollama runs in the same Compose stack, use:

```env
OLLAMA_BASE_URL=http://ollama:11434
OPENAI_BASE_URL=http://ollama:11434/v1
```

When Ollama runs on the host and the UI runs in a VM, use the host IP that the VM can reach:

```env
OLLAMA_BASE_URL=http://192.168.56.1:11434
OPENAI_BASE_URL=http://192.168.56.1:11434/v1
HOST_WORKER_STATUS_URL=http://192.168.56.1:8090/gpu/status
```

Avoid exposing Ollama directly to untrusted networks.
