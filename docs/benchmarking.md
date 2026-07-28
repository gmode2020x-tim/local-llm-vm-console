# Benchmarking

The benchmark script records a public-safe snapshot of the local setup and basic runtime performance. It intentionally avoids hostnames, usernames, local document paths, customer names, business identifiers, credentials, prompts from real work, and generated job data.

## Run

Windows:

```powershell
.\.venv\Scripts\python.exe tools\benchmark.py --output runtime\benchmarks\latest.json
```

Linux:

```bash
.venv/bin/python tools/benchmark.py --output runtime/benchmarks/latest.json
```

Use a specific model:

```bash
python tools/benchmark.py --model qwen2.5:1.5b
```

## What It Measures

- UI health latency for `/healthz` and `/api/status`.
- Ollama latency for `/api/version` and `/api/tags`.
- Optional host worker status latency.
- One short Ollama generation test with token throughput when Ollama reports token timing.
- Sanitized system profile:
  - operating system family and release;
  - Python version;
  - CPU model and core counts;
  - total RAM;
  - GPU model, VRAM, and driver;
  - Ollama version;
  - deployment style.

## Current Reference Setup

The current sanitized reference profile is recorded in [Current Benchmark Setup](benchmarks/current-setup.md).

Reference results are examples, not guarantees. Model speed changes with background load, power mode, thermals, model size, quantization, and whether the GPU is being used.

## Public Repo Rules

Keep committed benchmark files sanitized:

- OK: CPU class, RAM size, GPU model, driver version, Python version, Ollama version, endpoint latency against `127.0.0.1`.
- Not OK: hostnames, usernames, private IPs, customer/project names, local cloud-sync paths, uploaded documents, real prompts, credentials, access tokens, or proprietary outputs.

Runtime benchmark output should normally stay under `runtime/benchmarks/`, which is ignored by Git. Commit only curated examples or sanitized reference summaries.
