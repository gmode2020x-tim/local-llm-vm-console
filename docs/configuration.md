# Configuration Reference

Configuration is loaded from environment variables first and then from the editable UI state file.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8068` | UI port. |
| `APP_VERSION` | `0.1.0` | Version shown by `/version` and `/healthz`. |
| `LLM_UI_DATA_DIR` | `runtime/ui-data` | Persistent UI state, logs, conversations, jobs, and uploaded datasets. |
| `LLM_UI_DEFAULT_MODEL` | `llama3.2:3b` | Default model selected by the UI. |
| `LLM_UI_TIMEOUT` | `300` | Request timeout for model operations. |
| `LLM_UI_MODEL_LIST_TIMEOUT` | `3` | Short timeout for health/model inventory checks so the UI stays responsive when an endpoint is down. |
| `LLM_UI_MAX_CHAT_CHARS` | `48000` | Input guardrail for prompts and history. |
| `LLM_UI_ALLOW_SHELL_JOBS` | `0` | Reserved switch for future local job execution. Keep disabled unless you trust the UI users. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama API URL. |
| `OPENAI_BASE_URL` | `$OLLAMA_BASE_URL/v1` | OpenAI-compatible endpoint URL. |
| `HOST_WORKER_STATUS_URL` | `http://127.0.0.1:8090/gpu/status` | Optional host worker GPU status endpoint. |
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

When Ollama runs on another private host, use the host IP that the UI machine can reach:

```env
OLLAMA_BASE_URL=http://<host-ip>:11434
OPENAI_BASE_URL=http://<host-ip>:11434/v1
HOST_WORKER_STATUS_URL=http://<host-ip>:8090/gpu/status
```

Avoid exposing Ollama directly to untrusted networks.
