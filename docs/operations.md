# Operations Guide

## Start and Stop

Docker:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 llm-ui
docker compose down
```

Windows host worker:

```powershell
.\deploy\windows\start-host-worker.ps1
curl.exe http://127.0.0.1:8090/healthz
```

Linux systemd:

```bash
sudo systemctl status local-llm-ui.service
sudo systemctl restart local-llm-ui.service
sudo journalctl -u local-llm-ui.service -n 100 --no-pager
```

## Health Checks

```bash
curl -fsS http://localhost:8068/healthz
curl -fsS http://localhost:8068/api/status
curl -fsS http://localhost:11434/api/tags
```

Host worker:

```bash
curl -fsS http://localhost:8090/gpu/status
```

## Backup Policy

Back up source with Git:

```bash
git status --short
git add README.md app worker deploy docs examples references compose.yml Dockerfile requirements.txt .env.example .gitignore
git diff --cached --check
git commit -m "Update local LLM VM console"
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
| UI loads but models are missing | Confirm `OLLAMA_BASE_URL`, run `curl /api/tags`, pull a model. |
| Chat fails | Confirm `OPENAI_BASE_URL`, model name, and Ollama version. |
| GPU is not visible | Run `nvidia-smi` on the machine that owns the GPU; start host worker if needed. |
| Docker cannot use GPU | Install NVIDIA Container Toolkit and enable GPU support in Compose. |
| VM cannot reach Windows host | Check VM network mode, firewall, and the host IP reachable from the VM. |
| Settings disappear | Confirm `LLM_UI_DATA_DIR` volume is mounted and writable. |
