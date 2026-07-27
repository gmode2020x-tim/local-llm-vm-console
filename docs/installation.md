# Installation Guide

This guide covers three supported layouts:

- Linux VM with Docker and Ollama in Compose.
- Linux VM UI with Ollama or GPU services running on a Windows host.
- All-in-one Windows workstation.

## Prerequisites

- Git
- Docker Engine or Docker Desktop
- Docker Compose v2
- Python 3.11+ for the optional host worker
- Ollama, either in Compose or installed on the host
- NVIDIA driver and `nvidia-smi` only when GPU telemetry is needed

## Linux VM

```bash
git clone https://github.com/YOUR-USER/local-llm-vm-console.git
cd local-llm-vm-console
cp .env.example .env
docker compose up -d --build
docker compose exec ollama ollama pull llama3.2:3b
curl -fsS http://localhost:8068/healthz
```

## Windows Host plus Linux VM

On Windows, install Ollama and verify:

```powershell
ollama pull llama3.2:3b
curl.exe http://127.0.0.1:11434/api/version
```

Start the optional GPU status worker:

```powershell
.\deploy\windows\start-host-worker.ps1
curl.exe http://127.0.0.1:8090/gpu/status
```

Inside the VM, edit `.env`:

```env
OLLAMA_BASE_URL=http://<host-ip-from-vm>:11434
OPENAI_BASE_URL=http://<host-ip-from-vm>:11434/v1
HOST_WORKER_STATUS_URL=http://<host-ip-from-vm>:8090/gpu/status
```

Then run:

```bash
docker compose up -d --build llm-ui caddy
```

## Autostart

Linux systemd:

```bash
chmod +x deploy/linux/install-systemd.sh
sudo APP_DIR=/opt/local-llm-vm-console ./deploy/linux/install-systemd.sh
```

Windows host worker scheduled task:

```powershell
.\deploy\windows\install-host-worker-task.ps1
```

## Verification

```bash
curl -fsS http://localhost:8068/healthz
curl -fsS http://localhost:11434/api/version
curl -fsS http://localhost:8080/llm/healthz
```

If the UI is in a VM and the worker is on the host:

```bash
curl -fsS http://<host-ip-from-vm>:8090/gpu/status
```
