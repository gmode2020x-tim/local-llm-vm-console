from __future__ import annotations

import csv
import json
import os
import subprocess
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any

import psutil
import requests
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename


APP_ID = "local-llm-ui"
APP_NAME = "Local LLM UI"
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("LLM_UI_DATA_DIR", BASE_DIR.parent / "runtime" / "ui-data"))
DATASET_DIR = DATA_DIR / "datasets"
JOB_DIR = DATA_DIR / "jobs"
LOG_DIR = DATA_DIR / "logs"
STATE_PATH = DATA_DIR / "state.json"
CONVERSATION_LOG = DATA_DIR / "conversations.jsonl"
APP_LOG = LOG_DIR / "app.log"

DEFAULT_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", f"{DEFAULT_OLLAMA_BASE_URL}/v1").rstrip("/")
DEFAULT_HOST_WORKER_STATUS_URL = os.getenv("HOST_WORKER_STATUS_URL", "").rstrip("/")
DEFAULT_MODEL = os.getenv("LLM_UI_DEFAULT_MODEL", os.getenv("MODEL", "llama3.2:3b"))
REQUEST_TIMEOUT = int(os.getenv("LLM_UI_TIMEOUT", "300"))
MODEL_LIST_TIMEOUT = float(os.getenv("LLM_UI_MODEL_LIST_TIMEOUT", "3"))
MAX_CHAT_CHARS = int(os.getenv("LLM_UI_MAX_CHAT_CHARS", "48000"))
ALLOW_SHELL_JOBS = os.getenv("LLM_UI_ALLOW_SHELL_JOBS", "0").lower() in {"1", "true", "yes"}

app = Flask(__name__)
state_lock = threading.Lock()


def ensure_dirs() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def now_stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def text(value: Any) -> str:
    return str(value or "").strip()


def number_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def json_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def default_state() -> dict[str, Any]:
    return {
        "ollama_base_url": DEFAULT_OLLAMA_BASE_URL,
        "openai_base_url": DEFAULT_OPENAI_BASE_URL,
        "host_worker_status_url": DEFAULT_HOST_WORKER_STATUS_URL,
        "default_model": DEFAULT_MODEL,
        "active_profile": "balanced",
        "profiles": {
            "fast": {"temperature": 0.1, "top_p": 0.8, "max_tokens": 384},
            "balanced": {"temperature": 0.25, "top_p": 0.9, "max_tokens": 700},
            "coding": {"temperature": 0.15, "top_p": 0.85, "max_tokens": 1200},
            "creative": {"temperature": 0.75, "top_p": 0.95, "max_tokens": 900},
        },
        "monitoring": {
            "process_filters": ["ollama", "python", "gunicorn", "llama", "vllm"],
            "refresh_seconds": 5,
        },
    }


def deep_update(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def read_state() -> dict[str, Any]:
    ensure_dirs()
    with state_lock:
        if not STATE_PATH.exists():
            state = default_state()
            STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
            return state
        try:
            loaded = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded = {}
        return deep_update(default_state(), loaded)


def write_state(state: dict[str, Any]) -> None:
    ensure_dirs()
    with state_lock:
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def write_log(level: str, message: str, details: dict[str, Any] | None = None) -> None:
    ensure_dirs()
    payload = {"time": now_stamp(), "level": level, "message": message, "details": details or {}}
    with APP_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    ensure_dirs()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def api_error(message: str, status: int = 400, **details: Any):
    write_log("error", message, details)
    return jsonify({"ok": False, "error": message, **details}), status


def configured_urls() -> tuple[str, str, str]:
    state = read_state()
    return (
        text(state.get("ollama_base_url")).rstrip("/"),
        text(state.get("openai_base_url")).rstrip("/"),
        text(state.get("host_worker_status_url")).rstrip("/"),
    )


def list_models() -> tuple[bool, list[dict[str, Any]], str]:
    ollama_base_url, openai_base_url, _host_worker_url = configured_urls()
    errors: list[str] = []
    models: dict[str, dict[str, Any]] = {}

    try:
        response = requests.get(f"{ollama_base_url}/api/tags", timeout=MODEL_LIST_TIMEOUT)
        response.raise_for_status()
        for item in response.json().get("models", []):
            name = item.get("name") or item.get("model")
            if not name:
                continue
            details = item.get("details") or {}
            models[name] = {
                "name": name,
                "source": "ollama",
                "size": item.get("size"),
                "modified_at": item.get("modified_at"),
                "family": details.get("family", ""),
                "parameter_size": details.get("parameter_size", ""),
                "quantization": details.get("quantization_level", ""),
            }
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Ollama tags: {exc}")

    try:
        response = requests.get(f"{openai_base_url}/models", timeout=MODEL_LIST_TIMEOUT)
        response.raise_for_status()
        for item in response.json().get("data", []):
            name = item.get("id")
            if name:
                models.setdefault(name, {"name": name, "source": "openai-compatible"})
    except Exception as exc:  # noqa: BLE001
        errors.append(f"OpenAI models: {exc}")

    return bool(models), sorted(models.values(), key=lambda item: item["name"].lower()), " | ".join(errors)


def clamp_chat(value: Any) -> str:
    raw = text(value)
    if len(raw) <= MAX_CHAT_CHARS:
        return raw
    return raw[:MAX_CHAT_CHARS] + "\n\n[Input truncated by Local LLM UI.]"


def chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    state = read_state()
    profile_name = text(payload.get("profile")) or text(state.get("active_profile")) or "balanced"
    profile = state.get("profiles", {}).get(profile_name, {})
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")

    clean_messages: list[dict[str, str]] = []
    system_prompt = clamp_chat(payload.get("system_prompt"))
    if system_prompt:
        clean_messages.append({"role": "system", "content": system_prompt})
    for item in messages:
        if not isinstance(item, dict):
            raise ValueError("each message must be an object")
        role = text(item.get("role")) or "user"
        if role not in {"system", "user", "assistant", "tool"}:
            role = "user"
        content = clamp_chat(item.get("content"))
        if content:
            clean_messages.append({"role": role, "content": content})

    model = text(payload.get("model")) or text(state.get("default_model")) or DEFAULT_MODEL
    request_body = {
        "model": model,
        "messages": clean_messages,
        "stream": False,
        "temperature": float(payload.get("temperature", profile.get("temperature", 0.25))),
        "top_p": float(payload.get("top_p", profile.get("top_p", 0.9))),
        "max_tokens": int(payload.get("max_tokens", profile.get("max_tokens", 700))),
    }

    _ollama_base_url, openai_base_url, _host_worker_url = configured_urls()
    started = time.perf_counter()
    response = requests.post(f"{openai_base_url}/chat/completions", json=request_body, timeout=REQUEST_TIMEOUT)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    response.raise_for_status()
    data = response.json()
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    result = {
        "ok": True,
        "model": data.get("model", model),
        "profile": profile_name,
        "response": text(message.get("content")),
        "finish_reason": choice.get("finish_reason", ""),
        "usage": data.get("usage", {}),
        "elapsed_ms": elapsed_ms,
    }
    append_jsonl(CONVERSATION_LOG, {**result, "time": now_stamp(), "messages": clean_messages})
    return result


def bytes_to_gib(value: int | float | None) -> float | None:
    return None if value is None else round(float(value) / (1024**3), 2)


def local_gpu_metrics() -> list[dict[str, Any]]:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw,power.limit",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=8,
        )
    except Exception:
        return []
    rows = []
    for index, line in enumerate(output.splitlines()):
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 9:
            continue
        rows.append(
            {
                "index": index,
                "name": parts[0],
                "driver_version": parts[1],
                "memory_total_mb": number_or_none(parts[2]),
                "memory_used_mb": number_or_none(parts[3]),
                "memory_free_mb": number_or_none(parts[4]),
                "utilization_percent": number_or_none(parts[5]),
                "temperature_c": number_or_none(parts[6]),
                "power_w": number_or_none(parts[7]),
                "power_limit_w": number_or_none(parts[8]),
                "source": "local nvidia-smi",
            }
        )
    return rows


def host_gpu_metrics(status_url: str) -> list[dict[str, Any]]:
    if not status_url:
        return []
    try:
        response = requests.get(status_url, timeout=5)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []
    rows = []
    for index, gpu in enumerate(payload.get("gpus", [])):
        if not isinstance(gpu, dict):
            continue
        rows.append(
            {
                "index": gpu.get("index", index),
                "name": text(gpu.get("name")) or "Host GPU",
                "driver_version": text(gpu.get("driver_version")),
                "memory_total_mb": number_or_none(gpu.get("memory_total_mb")),
                "memory_used_mb": number_or_none(gpu.get("memory_used_mb")),
                "memory_free_mb": number_or_none(gpu.get("memory_free_mb")),
                "utilization_percent": number_or_none(gpu.get("utilization_gpu_percent")),
                "temperature_c": number_or_none(gpu.get("temperature_c")),
                "power_w": number_or_none(gpu.get("power_draw_w")),
                "power_limit_w": number_or_none(gpu.get("power_limit_w")),
                "source": text(payload.get("worker")) or "host worker",
            }
        )
    return rows


def gpu_metrics() -> list[dict[str, Any]]:
    local = local_gpu_metrics()
    if local:
        return local
    _ollama_base_url, _openai_base_url, host_worker_url = configured_urls()
    return host_gpu_metrics(host_worker_url)


def process_metrics() -> list[dict[str, Any]]:
    state = read_state()
    filters = [item.lower() for item in state.get("monitoring", {}).get("process_filters", [])]
    processes = []
    deadline = time.perf_counter() + 1.5
    for proc in psutil.process_iter(["pid", "name", "status", "memory_info"]):
        if time.perf_counter() > deadline:
            break
        try:
            info = proc.info
            name = text(info.get("name"))
            haystack = name.lower()
            if filters and not any(item in haystack for item in filters):
                continue
            rss = info.get("memory_info").rss if info.get("memory_info") else 0
            processes.append(
                {
                    "pid": info.get("pid"),
                    "name": name,
                    "status": info.get("status"),
                    "cpu_percent": proc.cpu_percent(interval=None),
                    "memory_mb": round(rss / (1024**2), 1),
                }
            )
        except (psutil.Error, OSError):
            continue
    return sorted(processes, key=lambda item: item.get("memory_mb") or 0, reverse=True)[:24]


def system_metrics() -> dict[str, Any]:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(DATA_DIR.anchor or DATA_DIR.drive or "/"))
    return {
        "time": now_stamp(),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "cpu_count": psutil.cpu_count(),
        "memory": {
            "percent": memory.percent,
            "used_gib": bytes_to_gib(memory.used),
            "total_gib": bytes_to_gib(memory.total),
            "available_gib": bytes_to_gib(memory.available),
        },
        "disk": {
            "percent": disk.percent,
            "used_gib": bytes_to_gib(disk.used),
            "total_gib": bytes_to_gib(disk.total),
            "free_gib": bytes_to_gib(disk.free),
        },
        "gpu": gpu_metrics(),
        "processes": process_metrics(),
    }


def dataset_path(name: str) -> Path:
    safe = secure_filename(name)
    path = (DATASET_DIR / safe).resolve()
    if DATASET_DIR.resolve() not in path.parents and path != DATASET_DIR.resolve():
        raise ValueError("invalid dataset path")
    return path


def validate_dataset(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    size = path.stat().st_size
    if suffix == ".jsonl":
        rows = 0
        keys: set[str] = set()
        errors = []
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                rows += 1
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        keys.update(item.keys())
                except json.JSONDecodeError as exc:
                    errors.append(f"line {line_number}: {exc.msg}")
                    if len(errors) >= 5:
                        break
        return {"format": "jsonl", "ok": not errors and rows > 0, "rows": rows, "size": size, "columns": sorted(keys), "errors": errors}
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
            reader = csv.DictReader(handle, dialect=dialect)
            rows = sum(1 for _row in reader)
            columns = reader.fieldnames or []
        return {"format": "csv", "ok": rows > 0 and bool(columns), "rows": rows, "size": size, "columns": columns, "errors": []}
    if suffix in {".txt", ".md"}:
        lines = sum(1 for line in path.open("r", encoding="utf-8", errors="replace") if line.strip())
        return {"format": suffix.lstrip("."), "ok": lines > 0, "rows": lines, "size": size, "columns": [], "errors": []}
    return {"format": suffix.lstrip(".") or "unknown", "ok": False, "rows": 0, "size": size, "columns": [], "errors": ["Use .jsonl, .csv, .txt, or .md"]}


def list_datasets() -> list[dict[str, Any]]:
    ensure_dirs()
    rows = []
    for path in sorted(DATASET_DIR.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if path.is_file():
            rows.append({"name": path.name, "modified_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(path.stat().st_mtime)), **validate_dataset(path)})
    return rows


def create_job(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_dirs()
    job = {"id": uuid.uuid4().hex[:12], "kind": kind, "status": "queued", "created_at": now_stamp(), "updated_at": now_stamp(), "payload": payload, "message": ""}
    (JOB_DIR / f"{job['id']}.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job


def list_jobs() -> list[dict[str, Any]]:
    ensure_dirs()
    jobs = []
    for path in sorted(JOB_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            jobs.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return jobs[:50]


def tail_file(path: Path, lines: int = 160) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return list(deque(handle, maxlen=max(1, min(lines, 1000))))


@app.get("/")
def index():
    return render_template("index.html", app_name=APP_NAME, version=APP_VERSION)


@app.get("/healthz")
def healthz():
    models_ok, models, detail = list_models()
    return jsonify({"ok": True, "app": APP_ID, "version": APP_VERSION, "llm_ok": models_ok, "models": [item["name"] for item in models], "detail": detail})


@app.get("/version")
def version():
    return jsonify({"app": APP_ID, "version": APP_VERSION})


@app.get("/api/status")
def api_status():
    models_ok, models, detail = list_models()
    return jsonify({"ok": True, "app": APP_ID, "version": APP_VERSION, "state": read_state(), "models_ok": models_ok, "models": models, "model_error": detail, "metrics": system_metrics(), "jobs": list_jobs(), "datasets": list_datasets(), "allow_shell_jobs": ALLOW_SHELL_JOBS})


@app.get("/api/models")
def api_models():
    ok, models, detail = list_models()
    return jsonify({"ok": ok, "models": models, "detail": detail})


@app.post("/api/chat")
def api_chat():
    try:
        return jsonify(chat_completion(json_payload()))
    except Exception as exc:  # noqa: BLE001
        return api_error("chat completion failed", 502, detail=str(exc))


@app.get("/api/metrics")
def api_metrics():
    return jsonify({"ok": True, "metrics": system_metrics()})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "GET":
        return jsonify({"ok": True, "state": read_state(), "allow_shell_jobs": ALLOW_SHELL_JOBS})
    payload = json_payload()
    state = read_state()
    for key in ["ollama_base_url", "openai_base_url", "host_worker_status_url", "default_model", "active_profile"]:
        if key in payload:
            state[key] = text(payload.get(key))
    if isinstance(payload.get("profiles"), dict):
        state["profiles"] = payload["profiles"]
    if isinstance(payload.get("monitoring"), dict):
        state["monitoring"] = payload["monitoring"]
    write_state(state)
    write_log("info", "Configuration updated", {"keys": sorted(payload.keys())})
    return jsonify({"ok": True, "state": state})


@app.get("/api/datasets")
def api_datasets():
    return jsonify({"ok": True, "datasets": list_datasets()})


@app.post("/api/datasets")
def api_upload_dataset():
    if "dataset" not in request.files:
        return api_error("dataset file is required")
    uploaded = request.files["dataset"]
    filename = secure_filename(uploaded.filename or "")
    if not filename:
        return api_error("dataset filename is required")
    path = dataset_path(filename)
    uploaded.save(path)
    validation = validate_dataset(path)
    write_log("info", "Dataset uploaded", {"name": path.name, "validation": validation})
    return jsonify({"ok": validation["ok"], "dataset": {"name": path.name, **validation}})


@app.post("/api/models/pull")
def api_pull_model():
    payload = json_payload()
    model = text(payload.get("model"))
    if not model:
        return api_error("model is required")
    job = create_job("model-pull", {"model": model})
    try:
        ollama_base_url, _openai_base_url, _host_worker_url = configured_urls()
        response = requests.post(f"{ollama_base_url}/api/pull", json={"name": model, "stream": False}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        job["status"] = "completed"
        job["message"] = f"Pulled {model}"
    except Exception as exc:  # noqa: BLE001
        job["status"] = "failed"
        job["message"] = str(exc)
    (JOB_DIR / f"{job['id']}.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    return jsonify({"ok": job["status"] == "completed", "job": job})


@app.get("/api/jobs")
def api_jobs():
    return jsonify({"ok": True, "jobs": list_jobs()})


@app.get("/api/logs")
def api_logs():
    ensure_dirs()
    logs = sorted(path.name for path in LOG_DIR.glob("*.log"))
    return jsonify({"ok": True, "logs": logs})


@app.get("/api/logs/<path:name>")
def api_log_tail(name: str):
    safe = secure_filename(name)
    path = (LOG_DIR / safe).resolve()
    if LOG_DIR.resolve() not in path.parents and path != LOG_DIR.resolve():
        return api_error("invalid log path")
    return jsonify({"ok": True, "name": safe, "lines": tail_file(path, int(request.args.get("lines", "180")))})


if __name__ == "__main__":
    ensure_dirs()
    write_log("info", "Local LLM UI starting", {"version": APP_VERSION})
    debug = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8068")), debug=debug)
