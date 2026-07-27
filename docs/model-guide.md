# Model Guide

## Recommended Starter Models

| Use | Example | Notes |
| --- | --- | --- |
| Small CPU test | `llama3.2:1b` | Quick smoke test for low-resource VMs. |
| General local assistant | `llama3.2:3b` | Good default for a small private console. |
| Coding | `qwen2.5-coder:7b` | Needs more memory and may benefit from GPU acceleration. |
| Larger general model | `llama3.1:8b` | Better quality, higher memory use. |

Pull a model:

```bash
ollama pull llama3.2:3b
```

Create a model from a Modelfile:

```bash
ollama create local-assistant -f examples/modelfiles/Modelfile.example
ollama run local-assistant
```

## Prompt Profiles

The UI ships with four profiles:

- `fast`: low temperature and short output.
- `balanced`: general default.
- `coding`: lower randomness and larger token budget.
- `creative`: higher randomness.

Profiles can be edited in the Settings page.

## Dataset Format

The sample JSONL dataset uses a simple chat-message structure:

```json
{"messages":[{"role":"user","content":"Question"},{"role":"assistant","content":"Answer"}]}
```

The current app validates and stores datasets. Training execution is intentionally disabled by default.
