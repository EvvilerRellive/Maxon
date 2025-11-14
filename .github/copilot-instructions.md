# Maxon - AI Coding Agent Instructions

## Project Overview
Maxon is a new project (MIT License, 2025). This is a foundation document for AI agents to use when contributing to this codebase as it grows.

## Architecture & Structure
- **Status**: Project initialization phase
- **Technology Stack**: To be defined
- **Main Components**: To be documented
 - **Technology Stack**: Python, requests, python-dateutil (MVP)
 - **Main Components**: `bot.py` (long-polling + handlers), `storage.py` (file-based JSON store), `config.json` (token & settings)

*Update this section as the project architecture emerges. Document major service boundaries, data flows, and component relationships.*

## Project Conventions
- **Language**: To be determined
- **Build System**: To be determined
- **Testing Framework**: To be determined
 - **Language**: Python 3.10+
 - **Build System**: none (venv + pip)
 - **Testing Framework**: none yet (add pytest later)

*As you establish patterns in the codebase, document them here instead of assuming common practices.*

## Critical Developer Workflows
### Build & Test
Use a virtual environment and pip. Example (PowerShell):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

### Running the Project

**Development (long-polling, local):**
```powershell
$env:MAX_ACCESS_TOKEN = "your_token"
python bot.py
```

**Production (WebHook, deployed):**
- Build Docker: `docker build -t maxon-bot .`
- Deploy to cloud (Render, Railway, Fly) or VPS with systemd
- Subscribe to WebHook: `.\examples\subscribe.ps1` (or use `subscribe.sh`)
- See `DEPLOY.md` for detailed instructions

### WebHook Subscription
1. Deploy bot to public HTTPS endpoint (e.g., Render, VPS with nginx+certbot)
2. Set `MAX_ACCESS_TOKEN` and `WEBHOOK_SECRET` env vars on deployed server
3. Run: `.\examples\subscribe.ps1` (update webhook URL first)
4. Verify: `GET /subscriptions?access_token=TOKEN` shows your URL


## Key Files & Integration Points
| File/Directory | Purpose |
|---|---|
| `LICENSE` | MIT License |
| `README.md` | Project documentation |
| `DEPLOY.md` | Deployment & WebHook setup guide |
| `bot.py` | Core bot logic (message parsing, reminders, long-polling) |
| `webhook.py` | FastAPI WebHook server for production |
| `storage.py` | File-based JSON reminder storage (data/reminders.json) |
| `config.json` | Configuration (token, timezone, limits, secrets) |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Docker image for containerized deployment |
| `examples/` | Subscription scripts (PowerShell, bash) |


*Add key files here as the project structure develops.*

## Common Patterns & Anti-Patterns
- To be documented as patterns emerge

## External Dependencies & APIs
- None yet

---
**Last Updated**: November 12, 2025  
**Note**: Update this file as the project architecture and conventions solidify.
