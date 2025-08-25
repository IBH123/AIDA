# AIDA — Adaptive Intelligent Day Assistant
**Planning Document • v0.1 → v0.3**  
Target: quick implementation in Claude Code, then iterate.

---

## 1) Objectives & Success Criteria (MVP v0.1)
**Goal:** Turn a very short morning check‑in into a realistic day plan and run it with a Pomodoro timer.

**Success criteria**
- Accept a brief text payload (goals, hard stops, known meetings, cadence) and generate a chronological plan.
- Pack tasks into Pomodoro blocks around fixed calendar events with 5‑min breaks and a 15‑min long break every 4 cycles.
- Console timer: start/finish announcements per block (text; TTS optional).
- Export plan as JSON; optional `.ics` file.
- Persist settings and logs locally (SQLite or JSONL log is fine for v0.1).

**Non‑goals (v0.1)**
- No external OAuth, no email send, no event creation.
- No multi‑day planning.
- No learning from history yet (hard‑coded heuristics).

---

## 2) Scope (In / Out)
**In:**
- Single‑user local tool with CLI and minimal REST API (FastAPI).
- Deterministic planner module + timer module.
- JSON schema for tasks/events/preferences + validation.

**Out (until v0.3+):**
- Calendar/Email integrations.
- Web UI beyond a simple Swagger UI.
- Notifications beyond console (optional OS notifs later).

---

## 3) Primary User Stories
1. *As a researcher*, I give AIDA my top goals, known meetings, and a cadence; I get a full-day plan I can run.
2. *As a busy person*, I want fixed meetings to be respected with buffers so the plan is realistic.
3. *As a focus‑seeker*, I want Pomodoro cycles with automatic breaks and a clear current task.
4. *As a planner*, I want to export the schedule to my calendar (.ics) if I choose.

---

## 4) High‑Level Architecture
- **CLI** (Typer) → calls planner + timer.
- **API** (FastAPI) → `/v1/plan`, `/v1/timer/*`, `/v1/summary`.
- **Planner** → split tasks into cycles, score & pack into free intervals.
- **Timer** → state machine that runs blocks serially.
- **Storage** → `prefs.json` (or SQLite) + `logs/` session logs.
- **(Later) MCP** tools for calendar/email/agenda.

```text
 ┌────────┐   plan req   ┌──────────┐   blocks   ┌─────────┐
 │  CLI   │ ───────────▶ │ Planner  │ ─────────▶ │  Timer  │
 └────────┘              └──────────┘            └─────────┘
        ▲                        │                     │
        │            prefs/tasks/events JSON           │ logs
        │                        ▼                     ▼
     FastAPI                Storage (local)        Summary/ICS
```

---

## 5) Tech Stack & Repo Layout
**Stack**: Python 3.11+, FastAPI, Uvicorn, Typer, Pydantic, SQLite (or JSONL), `pyttsx3` (optional TTS).

**Repo**
```
AIDA/
  pyproject.toml
  README.md
  Makefile
  aida/
    __init__.py
    models.py        # Pydantic models
    planner.py       # plan_day(), scoring, interval ops
    timer.py         # run_timer(), state machine
    api.py           # FastAPI app
    storage.py       # prefs + logs (SQLite or JSONL)
    ics.py           # to_ics(blocks)
    prompts.py       # morning check-in templates
    cli.py           # Typer CLI entrypoint
    mcp_tools/
      calendar.py    # stubs for Phase 2
      email.py       # stubs for Phase 2
      meetings.py    # stubs for Phase 2
  examples/
    today.json
  tests/
    test_planner.py
    test_intervals.py
    test_ics.py
```

---

## 6) Data Model (Pydantic)
```python
# aida/models.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime

class Preferences(BaseModel):
    workday_start: datetime
    workday_end: datetime
    pomodoro_min: int = 25
    break_min: int = 5
    long_break_min: int = 15
    cycles_per_long_break: int = 4

class Task(BaseModel):
    id: str
    title: str
    estimate_min: int = Field(ge=1)
    priority: int = Field(3, ge=1, le=5)
    deadline: Optional[datetime] = None
    energy: Literal['deep','light'] = 'light'
    requires_deep_work: bool = False
    notes: Optional[str] = None

class Event(BaseModel):
    start: datetime
    end: datetime
    title: str
    location: Optional[str] = None

class Block(BaseModel):
    start: datetime
    end: datetime
    type: Literal['event','pomodoro','break','long_break']
    title: str
    task_id: Optional[str] = None

class PlanRequest(BaseModel):
    preferences: Preferences
    tasks: List[Task] = []
    events: List[Event] = []

class PlanResponse(BaseModel):
    blocks: List[Block]
    summary: dict
```

---

## 7) Planning Algorithm
**Interval ops**
- Merge & subtract busy time from work window.
- Add ±5–10 min buffers around external events.

**Task segmentation**
- `n_cycles = ceil(estimate_min / pomodoro_min)`

**Scoring**
```
score = 5*priority + urgency + energy_match
urgency = max(0, 10 - days_until_deadline)
energy_match = 2 if requires_deep_work and block_start in [9,12) else 0
```

**Packing** (greedy for v0.1)
- Fill free intervals chronologically with highest‑score segments.
- Insert 5‑min breaks; every 4th cycle insert 15‑min long break.
- Stop when out of time; report leftovers in summary.

**Later (v0.3)**: EDF (Earliest Deadline First) or WSJF; learn deep‑window from logs.

---

## 8) API Design (FastAPI)
**POST** `/v1/plan`
- **Body:** `PlanRequest`
- **Returns:** `PlanResponse`

**GET** `/v1/plan/ics`
- **Query:** `from` (iso), `to` (iso) optional
- **Returns:** `.ics` with Pomodoro/Break blocks only

**POST** `/v1/timer/start`
- **Body:** `{ blocks: Block[], start_index?: int }`
- **Effect:** runs timer sequentially (server process) — v0.1 may be CLI only

**GET** `/v1/summary/today`
- **Returns:** JSON recap of completed cycles, carry‑overs.

**GET** `/healthz`
- **Returns:** `{status: 'ok'}`

### Example — `/v1/plan`
```json
{
  "preferences": {
    "workday_start": "2025-08-25T09:00:00-07:00",
    "workday_end":   "2025-08-25T17:30:00-07:00",
    "pomodoro_min": 25,
    "break_min": 5,
    "long_break_min": 15,
    "cycles_per_long_break": 4
  },
  "tasks": [
    {"id":"t1","title":"Revise STOTEN cover letter","estimate_min":60,"priority":4,"deadline":"2025-08-27T23:59:00-07:00","energy":"deep","requires_deep_work":true},
    {"id":"t2","title":"Reply to reviewer 2","estimate_min":50,"priority":3}
  ],
  "events": [
    {"start":"2025-08-25T11:00:00-07:00","end":"2025-08-25T12:00:00-07:00","title":"Team sync","location":"Zoom"}
  ]
}
```

---

## 9) CLI Commands (Typer)
- `aida plan examples/today.json` → prints schedule
- `aida plan examples/today.json --ics out.ics` → writes ICS
- `aida run examples/today.json` → plan + run timer
- `aida timer start plan.json` → run timer on precomputed plan

---

## 10) Prompt Library (for LLM front‑end)
**Ultra‑brief**
> Today’s top 3 goals: [..]; fixed events: [..]; cadence: [25/5 or 50/10]; hard stops: [..].

**Conversational**
> Morning! What are the must‑wins today? Any fixed meetings or hard stops? Stay with 25/5 or switch to 50/10 for deep work?

**“Do not schedule” examples**
> Avoid booking between 3:00–3:30pm (commute); leave 45 min for lunch between 12–2.

---

## 11) Storage Plan
- **prefs**: `~/.aida/prefs.json`
- **logs**: `~/.aida/logs/YYYY‑MM‑DD.jsonl` (each line: `{block, started_at, ended_at, outcome}`)
- **(Optional) SQLite**: `~/.aida/aida.db` with tables `prefs`, `logs`, `sessions`.

---

## 12) Privacy & Safety
- Local‑only by default; no external network calls.
- Explicit confirmation gates in future for sending emails/creating events.
- Red‑team rules for outbound drafts (tone, no PII/PHI, no commitments without approval).

---

## 13) Testing Strategy
**Unit tests**
- Interval subtraction & merging edge cases.
- Task segmentation math.
- Scoring & sort stability.
- Packing correctness (no overlaps, within work window).

**Integration tests**
- `/v1/plan` request → valid `PlanResponse`.
- `.ics` export parses in a calendar client.

**CLI tests**
- `aida plan` prints blocks; exit codes.

---

## 14) Work Breakdown (Tickets)
**T1. Project bootstrap (2h)**
- pyproject, Makefile, black/ruff, pre‑commit, README skeleton.

**T2. Models & validation (2h)**
- `models.py` with Pydantic; sample `examples/today.json`.

**T3. Interval ops (3h)**
- merge & subtract busy time; unit tests.

**T4. Planner core (4h)**
- segmentation, scoring, greedy packing; summary generation; tests.

**T5. Timer (3h)**
- simple sequential runner with console output; CTRL‑C safe; optional `pyttsx3`.

**T6. CLI (2h)**
- Typer commands: `plan`, `run`, `timer start`.

**T7. FastAPI (3h)**
- `/v1/plan`, `/healthz`; docs via Swagger; CORS local.

**T8. ICS export (2h)**
- `.ics` writer; sanity test in a calendar app.

**T9. Logging (2h)**
- session JSONL logs + daily summary endpoint.

**T10. Polish (2h)**
- README quickstart; examples; error messages.

> Stretch (v0.2–v0.3): **T11** deep‑window preference; **T12** EDF/WSJF mode; **T13** MCP tool stubs and interface contracts.

---

## 15) Definition of Done (v0.1)
- Given `examples/today.json`, `aida plan` prints a chronological schedule with Pomodoro/Break/Event blocks.
- `aida run` runs through at least one Pomodoro + break with start/finish messages.
- `/v1/plan` returns the same blocks as CLI for the same input.
- (Optional) `--ics` produces a valid file importable to a calendar.

---

## 16) Risks & Mitigations
- **Time‑zone parsing**: require ISO8601 with TZ; test DST cases.
- **Unrealistic plans**: add default buffers; surface leftovers in summary.
- **Long tasks**: enforce segmentation; report spillover next‑day suggestion.

---

## 17) Roadmap
- **v0.1 (MVP)**: CLI + planner + timer + JSON logs.
- **v0.2**: ICS export, configurable buffers, lunch detection.
- **v0.3**: FastAPI service, simple web page (Swagger only), MCP tool stubs.
- **v0.4**: Email draft + agenda generator (human‑in‑the‑loop send).

---

## 18) Glossary
- **Block**: a contiguous chunk of time (event, pomodoro, break, long_break).
- **Deep window**: hours with highest focus; initially 9–12 local time.
- **MCP**: Model Context Protocol tools for external integrations.

