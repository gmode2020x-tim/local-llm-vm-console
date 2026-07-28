# Operations Guide

## Start and Stop

Windows UI:

```powershell
.\deploy\windows\start-ui.ps1
Get-NetTCPConnection -LocalPort 8068 -State Listen
```

Windows host worker:

```powershell
.\deploy\windows\start-host-worker.ps1
curl.exe http://127.0.0.1:8090/healthz
```

Linux UI:

```bash
set -a
source .env
set +a
.venv/bin/gunicorn -w 2 -b 0.0.0.0:${PORT:-8068} app.app:app
```

Linux systemd:

```bash
sudo systemctl status local-llm-ui.service
sudo systemctl restart local-llm-ui.service
sudo journalctl -u local-llm-ui.service -n 100 --no-pager
```

## Health Checks

```bash
curl -fsS http://127.0.0.1:8068/healthz
curl -fsS http://127.0.0.1:8068/api/status
curl -fsS http://127.0.0.1:11434/api/tags
curl -fsS http://127.0.0.1:8090/gpu/status
```

## Backup Policy

Back up source with Git:

```bash
git status --short
git add README.md app worker deploy docs examples references requirements.txt .env.example .gitignore LICENSE
git diff --cached --check
git commit -m "Update local LLM console"
git push
```

Back up runtime data separately only when needed:

```bash
tar -czf runtime-backup-$(date +%Y%m%d-%H%M%S).tar.gz runtime/
```

Do not commit `runtime/`, `.env`, model weights, logs, conversations, or uploaded datasets.

## Troubleshooting

| Symptom | Checks |
| --- | --- |
| UI does not start | Confirm `.venv` exists, install `requirements.txt`, and check `runtime/ui-data/logs/ui.err.log`. |
| UI loads but models are missing | Confirm `OLLAMA_BASE_URL`, run `curl /api/tags`, pull a model. |
| Chat fails | Confirm `OPENAI_BASE_URL`, model name, and Ollama version. |
| GPU is not visible | Run `nvidia-smi` on the machine that owns the GPU; start host worker if needed. |
| Remote host is unreachable | Check firewall rules, bind address, host IP, and trusted network routing. |
| Settings disappear | Confirm `LLM_UI_DATA_DIR` is writable. |
