# Security and Public Repo Policy

This project is intended to be safe for a public repository.

## Never Commit

- Passwords
- API keys
- SSH private keys
- Tokens
- `.env`
- Runtime data
- Conversation logs
- Uploaded files
- Model weights
- Customer or private project documents

## Network Exposure

Local LLM endpoints often have no authentication when used on localhost. Keep Ollama and the host worker on a trusted network.

Recommended defaults:

- Bind public UI only behind a reverse proxy you control.
- Keep Ollama on localhost or a private VM/host-only network.
- Do not expose `11434` or `8090` to the public internet.
- Add authentication at the reverse proxy before using this outside a trusted LAN.

## Git Hygiene

Before every public push:

```bash
git diff --cached --check
git ls-files --cached | grep -Ei '(^|/)(runtime|data|jobs|logs|uploads|outputs|cache|tmp|temp|models)/|\\.(sqlite|db|log|jsonl|pdf|zip|tar|gz|key|pem|pfx|ppk)$' && exit 1 || true
git grep --cached -n -I -E 'password|secret|token|api[_-]?key|BEGIN (RSA|OPENSSH|PRIVATE) KEY' || true
```

Review every match. Variable names and placeholders are normal; real secret values are not.
