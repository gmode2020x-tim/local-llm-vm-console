from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil
import requests


DEFAULT_PROMPT = "Reply with exactly three words: local benchmark ok"


def now_stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def round_float(value: float | None, places: int = 3) -> float | None:
    return round(value, places) if value is not None else None


def command_output(command: list[str], timeout: int = 8) -> tuple[int, str]:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError:
        return 127, "not found"
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    output = (completed.stdout or completed.stderr or "").strip()
    return completed.returncode, output


def endpoint_get(url: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = requests.get(url, timeout=timeout)
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "latency_ms": round_float(elapsed_ms),
            "content_type": response.headers.get("content-type", ""),
        }
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {"ok": False, "status_code": None, "latency_ms": round_float(elapsed_ms), "error": str(exc)}


def endpoint_series(name: str, url: str, samples: int, timeout: float) -> dict[str, Any]:
    measurements = [endpoint_get(url, timeout) for _ in range(samples)]
    latencies = [item["latency_ms"] for item in measurements if item.get("ok") and item.get("latency_ms") is not None]
    return {
        "name": name,
        "url": url,
        "samples": samples,
        "ok_count": sum(1 for item in measurements if item.get("ok")),
        "latency_ms_min": round_float(min(latencies)) if latencies else None,
        "latency_ms_median": round_float(statistics.median(latencies)) if latencies else None,
        "latency_ms_max": round_float(max(latencies)) if latencies else None,
        "last": measurements[-1] if measurements else {},
    }


def ollama_tags(ollama_url: str, timeout: float) -> list[dict[str, Any]]:
    try:
        response = requests.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=timeout)
        response.raise_for_status()
        models = response.json().get("models", [])
        return models if isinstance(models, list) else []
    except Exception:
        return []


def choose_model(models: list[dict[str, Any]], requested: str | None) -> str | None:
    if requested:
        return requested
    for item in models:
        capabilities = item.get("capabilities") or []
        if "completion" in capabilities:
            return item.get("name") or item.get("model")
    for item in models:
        name = item.get("name") or item.get("model")
        if name:
            return name
    return None


def generation_benchmark(ollama_url: str, model: str | None, prompt: str, timeout: float) -> dict[str, Any]:
    if not model:
        return {"ok": False, "skipped": True, "reason": "no completion model found"}
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 96, "temperature": 0},
    }
    started = time.perf_counter()
    try:
        response = requests.post(f"{ollama_url.rstrip('/')}/api/generate", json=payload, timeout=timeout)
        elapsed_s = time.perf_counter() - started
        response.raise_for_status()
        body = response.json()
        eval_count = body.get("eval_count")
        eval_duration = body.get("eval_duration")
        total_duration = body.get("total_duration")
        tokens_per_second = None
        if isinstance(eval_count, (int, float)) and isinstance(eval_duration, (int, float)) and eval_duration > 0:
            tokens_per_second = float(eval_count) / (float(eval_duration) / 1_000_000_000)
        return {
            "ok": True,
            "model": model,
            "elapsed_s": round_float(elapsed_s),
            "eval_count": eval_count,
            "eval_duration_s": round_float(float(eval_duration) / 1_000_000_000) if isinstance(eval_duration, (int, float)) else None,
            "total_duration_s": round_float(float(total_duration) / 1_000_000_000) if isinstance(total_duration, (int, float)) else None,
            "tokens_per_second": round_float(tokens_per_second),
            "response_chars": len(body.get("response") or ""),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "model": model, "elapsed_s": round_float(time.perf_counter() - started), "error": str(exc)}


def gpu_profile() -> list[dict[str, Any]]:
    query = "name,memory.total,driver_version"
    code, output = command_output(["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"])
    if code != 0:
        return []
    gpus = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        gpus.append({"name": parts[0], "memory_total_mb": int(float(parts[1])), "driver_version": parts[2]})
    return gpus


def cpu_name() -> str:
    if platform.system() == "Windows":
        code, output = command_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)"],
            timeout=8,
        )
        if code == 0 and output:
            return output
    return platform.processor() or "unknown"


def system_profile() -> dict[str, Any]:
    ollama_code, ollama_version = command_output(["ollama", "--version"])
    return {
        "os": {"system": platform.system(), "release": platform.release()},
        "python": platform.python_version(),
        "cpu": {
            "name": cpu_name(),
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_processors": psutil.cpu_count(logical=True),
        },
        "memory_gb": round_float(psutil.virtual_memory().total / (1024**3), 1),
        "gpu": gpu_profile(),
        "ollama_version": ollama_version if ollama_code == 0 else None,
        "deployment": "native .venv + host Ollama",
        "privacy": "sanitized: no hostnames, usernames, local document paths, customer names, or business identifiers",
    }


def write_result(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a sanitized local LLM console benchmark.")
    parser.add_argument("--ui-url", default=os.getenv("BENCH_UI_URL", "http://127.0.0.1:8068"))
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--worker-url", default=os.getenv("HOST_WORKER_STATUS_URL", "http://127.0.0.1:8090/gpu/status"))
    parser.add_argument("--model", default=os.getenv("BENCH_MODEL"))
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=8)
    parser.add_argument("--generate-timeout", type=float, default=120)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--output", default="runtime/benchmarks/latest.json")
    args = parser.parse_args()

    models = ollama_tags(args.ollama_url, args.timeout)
    selected_model = choose_model(models, args.model)
    result = {
        "schema_version": 1,
        "recorded_at": now_stamp(),
        "profile": system_profile(),
        "endpoints": [
            endpoint_series("ui_health", f"{args.ui_url.rstrip('/')}/healthz", args.samples, args.timeout),
            endpoint_series("ui_status", f"{args.ui_url.rstrip('/')}/api/status", args.samples, args.timeout),
            endpoint_series("ollama_version", f"{args.ollama_url.rstrip('/')}/api/version", args.samples, args.timeout),
            endpoint_series("ollama_tags", f"{args.ollama_url.rstrip('/')}/api/tags", args.samples, args.timeout),
            endpoint_series("host_worker_status", args.worker_url, args.samples, args.timeout),
        ],
        "models": [
            {
                "name": item.get("name") or item.get("model"),
                "family": (item.get("details") or {}).get("family"),
                "parameter_size": (item.get("details") or {}).get("parameter_size"),
                "quantization": (item.get("details") or {}).get("quantization_level"),
                "capabilities": item.get("capabilities") or [],
            }
            for item in models
        ],
        "generation": generation_benchmark(args.ollama_url, selected_model, args.prompt, args.generate_timeout),
    }
    output_path = Path(args.output)
    write_result(output_path, result)
    print(json.dumps(result, indent=2))
    print(f"\nWrote benchmark result to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
