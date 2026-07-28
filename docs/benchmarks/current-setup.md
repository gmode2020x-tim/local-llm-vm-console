# Current Benchmark Setup

Last reviewed: 2026-07-27

This profile records the current native test environment without personal, customer, project, local-path, or business-specific details.

## Sanitized Hardware And Runtime

| Area | Value |
| --- | --- |
| Deployment | Native Python virtual environment with host Ollama |
| Operating system | Windows 11 class workstation |
| CPU | Intel Core Ultra 7 165H |
| CPU topology | 16 physical cores, 22 logical processors |
| Memory | 31.4 GiB installed |
| GPU | NVIDIA RTX 500 Ada Generation Laptop GPU |
| GPU memory | 4094 MiB |
| GPU driver | 581.15 |
| Python | 3.13.0 |
| Ollama | 0.30.10 |

## Local Services Observed During Benchmark

| Service | Endpoint | Status at review |
| --- | --- | --- |
| Local LLM UI | `http://127.0.0.1:8068/healthz` | Reachable |
| Local LLM UI status | `http://127.0.0.1:8068/api/status` | Reachable |
| Ollama | `http://127.0.0.1:11434/api/tags` | Reachable |
| Host GPU worker | `http://127.0.0.1:8090/gpu/status` | Reachable |

## Benchmark Result Summary

Command:

```powershell
.\.venv\Scripts\python.exe tools\benchmark.py --output runtime\benchmarks\current-native-windows.json
```

| Check | Samples | Median latency | Notes |
| --- | ---: | ---: | --- |
| UI `/healthz` | 5 | 24.309 ms | Health endpoint available |
| UI `/api/status` | 5 | 1703.321 ms | Includes model, metrics, jobs, and dataset inventory |
| Ollama `/api/version` | 5 | 2.263 ms | Local Ollama reachable |
| Ollama `/api/tags` | 5 | 6.435 ms | Model inventory reachable |
| Host worker `/gpu/status` | 5 | 119.523 ms | GPU status worker reachable |

Generation test:

| Model | Elapsed | Eval tokens | Token throughput |
| --- | ---: | ---: | ---: |
| `qwen2.5:1.5b` | 6.364 s | 7 | 84.145 tokens/s |

## Installed Public Models Observed

| Model | Family | Parameters | Quantization | Capability |
| --- | --- | --- | --- | --- |
| `qwen2.5:1.5b` | qwen2 | 1.5B | Q4_K_M | completion, tools |
| `nomic-embed-text:latest` | nomic-bert | 137M | F16 | embedding |

## Notes

- The benchmark harness records endpoint availability instead of assuming every local service is running.
- Runtime output should normally be written to `runtime/benchmarks/` and left out of Git.
- Commit only curated summaries that have been reviewed for public-safe content.
- Throughput is a small smoke benchmark, not a full model-quality or sustained-load test.
- The recorded generation elapsed time may include model wake-up or load time; rerun the benchmark when comparing warm steady-state performance.
