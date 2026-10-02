# Auto-Flow AI

An autonomous browser agent for everyday web tasks, with **human-in-the-loop approval**.
You pick a task, the agent drives a real browser to do it, and risky tasks pause
until a human approves.

Built by Gayathri K (team THESILENTVOICE) for AI Build Challenge 2026 - PS-01:
Autonomous Agents for Everyday Apps.

## What it does

- Takes a goal in plain English and completes it in a real browser ([browser-use](https://github.com/browser-use/browser-use) + Playwright)
- Returns **structured JSON** (Pydantic models), not free text
- **Human-in-the-loop:** tasks marked `needs_approval` stop at `pending_approval`; nothing runs until a person calls approve (or reject)
- **Resilient:** automatic fallback to a second Gemini model on 429/503 errors, plus whole-run retries
- **Built-in safety rules:** agents are told never to log in, buy anything, or submit forms

## Built-in tasks

| ID | Task | Needs approval |
|----|------|----------------|
| 1 | Compare product prices (3 cheapest results) | No |
| 2 | Find jobs / internships | Yes |
| 3 | Summarize a web page | No |

New tasks are ~10 lines each in `workflows.py`.

## Project structure

| File | Purpose |
|------|---------|
| `agent_core.py` | Core engine: runs a goal in the browser, handles retries and fallback model |
| `workflows.py` | Task menu (goal templates + output models + approval flag); also a terminal menu |
| `main.py` | FastAPI server exposing the tasks and the approval flow |
| `mcp_server.py` | FastMCP connector tools (summarize, email). Email is simulated; not yet wired into the agent |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
pip install -r requirements.txt
```

Create a `.env` file (never commit it):

```
GOOGLE_API_KEY=your_google_ai_studio_key
PRIMARY_MODEL=gemini-3.8-flash

# Optional fallback: a key from a SECOND Google AI Studio project
GOOGLE_API_KEY_2=your_second_key
FALLBACK_MODEL=gemini-3.5-flash-lite
```

If the browser does not launch, run `playwright install chromium`.

## Run

Terminal menu:

```bash
python workflows.py
```

API server:

```bash
python main.py
```

Then open http://127.0.0.1:8000/docs

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/workflows` | List tasks and their inputs |
| POST | `/api/v1/tasks` | Start a task (`{"workflow": "3", "inputs": {"url": "https://example.com"}}`) |
| POST | `/api/v1/tasks/{id}/approve` | Approve a pending task and run it |
| POST | `/api/v1/tasks/{id}/reject` | Reject a pending task (nothing runs) |
| GET | `/api/v1/tasks/{id}` | Check task status/result |
| POST | `/api/v1/execute` | Free-form goal in plain English |

Example flow for an approval-required task:

1. `POST /api/v1/tasks` with workflow `2` returns `status: pending_approval` and the exact goal the agent intends to run
2. A human calls `/approve` (agent runs) or `/reject` (nothing happens)

## Known limitations

- Free-tier Gemini quotas are small (about 20 requests/day per model), so heavy use needs billing or more keys
- Large retail sites may block automated browsers; tested end to end on practice sites (books.toscrape.com, example.com)
- Task state is stored in memory and resets when the server restarts
- MCP connector tools are demo stubs and are not yet called by the agent

## Roadmap

- Wire MCP tools into the agent for cross-app workflows (browser, then email or notify)
- Web UI with approve/reject buttons
- Persistent task history
