from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


HOST = os.getenv("HOST_WORKER_BIND", "0.0.0.0")
PORT = int(os.getenv("HOST_WORKER_PORT", "8090"))
APP_VERSION = os.getenv("HOST_WORKER_VERSION", "0.1.0")


def run_command(command: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", exc.stderr or "command timed out"
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def number(value: str) -> float | int | None:
    try:
        parsed = float(value)
    except ValueError:
        return None
    return int(parsed) if parsed.is_integer() else parsed


def nvidia_status() -> dict:
    query = (
        "name,driver_version,memory.total,memory.used,memory.free,"
        "utilization.gpu,temperature.gpu,power.draw,power.limit"
    )
    code, stdout, stderr = run_command(
        ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
        timeout=8,
    )
    if code != 0:
        return {"available": False, "error": stderr or stdout or "nvidia-smi failed", "gpus": []}

    gpus = []
    for index, line in enumerate(stdout.splitlines()):
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 9:
            continue
        gpus.append(
            {
                "index": index,
                "name": parts[0],
                "driver_version": parts[1],
                "memory_total_mb": number(parts[2]),
                "memory_used_mb": number(parts[3]),
                "memory_free_mb": number(parts[4]),
                "utilization_gpu_percent": number(parts[5]),
                "temperature_c": number(parts[6]),
                "power_draw_w": number(parts[7]),
                "power_limit_w": number(parts[8]),
            }
        )
    return {"available": bool(gpus), "gpus": gpus}


def base_payload(body: dict, status: int = 200) -> tuple[int, bytes]:
    body.setdefault("worker", "local-llm-host-worker")
    body.setdefault("version", APP_VERSION)
    body.setdefault("updated_at", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    body.setdefault("host", {"system": platform.system(), "release": platform.release(), "machine": platform.machine()})
    return status, json.dumps(body, indent=2).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalLlmHostWorker/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in {"/", "/healthz"}:
            status = nvidia_status()
            self.send_json(
                *base_payload(
                    {
                        "ok": status.get("available", False),
                        "gpu_available": status.get("available", False),
                        "gpu_count": len(status.get("gpus", [])),
                        "status_url": "/gpu/status",
                        "capabilities_url": "/gpu/capabilities",
                    },
                    200 if status.get("available") else 503,
                )
            )
            return
        if path in {"/gpu/status", "/status"}:
            self.send_json(*base_payload({"ok": True, **nvidia_status()}))
            return
        if path in {"/gpu/capabilities", "/capabilities"}:
            self.send_json(
                *base_payload(
                    {
                        "ok": True,
                        "mode": "status_worker",
                        "accepts": ["GET /healthz", "GET /gpu/status", "GET /gpu/capabilities"],
                        "future_job_contract": {
                            "POST /gpu/jobs": {
                                "app_id": "calling application id",
                                "job_type": "task name",
                                "input": "JSON payload or shared path reference",
                            }
                        },
                    }
                )
            )
            return
        self.send_json(*base_payload({"ok": False, "error": "not found"}, 404))

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/gpu/jobs":
            self.send_json(
                *base_payload(
                    {
                        "ok": False,
                        "error": "No generic GPU job runner is installed.",
                        "message": "Use this endpoint as the extension point for app-specific GPU jobs.",
                    },
                    501,
                )
            )
            return
        self.send_json(*base_payload({"ok": False, "error": "not found"}, 404))

    def send_json(self, status: int, data: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"local-llm-host-worker listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
