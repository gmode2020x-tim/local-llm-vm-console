# Installation Guide

This guide covers the native package layout:

- All-in-one Windows workstation.
- All-in-one Linux machine or Linux VM.
- UI on one private machine with Ollama or GPU telemetry on another host.

## Prerequisites

- Git
- Python 3.11+
- Ollama
- NVIDIA driver and `nvidia-smi` only when GPU telemetry is needed

## Windows

```powershell
git clone https://github.com/gmode2020x-tim/local-llm-vm-console.git
cd local-llm-vm-console
.\deploy\windows\setup-native.ps1
ollama pull llama3.2:3b
.\deploy\windows\start-ui.ps1
.\deploy\windows\start-host-worker.ps1
curl.exe http://127.0.0.1:8068/healthz
```

Install logon autostart tasks:

```powershell
.\deploy\windows\install-ui-task.ps1
.\deploy\windows\install-host-worker-task.ps1
```

## Linux

```bash
git clone https://github.com/gmode2020x-tim/local-llm-vm-console.git
cd local-llm-vm-console
chmod +x deploy/linux/setup-native.sh
./deploy/linux/setup-native.sh
ollama pull llama3.2:3b
set -a
source .env
set +a
.venv/bin/gunicorn -w 2 -b 0.0.0.0:${PORT:-8068} app.app:app
curl -fsS http://127.0.0.1:8068/healthz
```

Install systemd autostart:

```bash
sudo APP_DIR=/opt/local-llm-vm-console ./deploy/linux/install-systemd.sh
sudo systemctl status local-llm-ui.service
```

## Split Host Layout

If the UI runs on one private machine and Ollama or GPU telemetry runs on another, edit `.env`:

```env
OLLAMA_BASE_URL=http://<host-ip>:11434
OPENAI_BASE_URL=http://<host-ip>:11434/v1
HOST_WORKER_STATUS_URL=http://<host-ip>:8090/gpu/status
```

Verify connectivity from the UI machine:

```bash
curl -fsS http://<host-ip>:11434/api/version
curl -fsS http://<host-ip>:8090/gpu/status
```

## Verification

```bash
curl -fsS http://127.0.0.1:8068/healthz
curl -fsS http://127.0.0.1:8068/api/status
curl -fsS http://127.0.0.1:11434/api/version
```
