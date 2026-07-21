# War-Room Web UI — Design

**Status:** Approved for planning
**Date:** 2026-07-21

## Purpose

A super-simple local web interface for the Incident War-Room: a page with one
button that starts the INC-4417 run and shows the parallel fan-out live,
ending with a download link for the postmortem `.docx`. This replaces
running `run_war_room.py` from the terminal; it does not touch setup
(`setup_environment.py`, `create_specialists.py`, `upload_skills.py`,
`create_coordinator.py`), which stays exactly as-is.

## Scope

- Run-only. The UI assumes setup has already been done via the existing CLI
  scripts (`.swarm_ids.json` already has `coordinator` and `environment`).
- One-click trigger only — no free-text input. The button sends the same
  fixed INC-4417 kickoff message `run_war_room.py` sends today.
- Single incident scenario, single user, local use (`127.0.0.1`). No auth,
  no multi-session management beyond preventing two overlapping runs.

## Architecture

FastAPI backend + Server-Sent Events (SSE) + a single static vanilla-JS/HTML
page. No frontend build step, no extra JS framework.

Rejected alternatives:
- **Flask + polling** — simpler dependency, but loses the live "watch it
  happen" feel; events would arrive in batches instead of streaming.
- **Streamlit** — fastest to scaffold, but its rerun-on-interaction model
  fights a long-running blocking event stream; would need extra threading
  plumbing that erodes the "simple" goal.

### Shared runner (`swarm/runner.py`, new)

The event loop currently inline in `run_war_room.py` moves into a generator:

```python
def run_session(client, commander_id, environment_id, kickoff_text, title) -> Iterator[dict]
```

Yielded event dicts (a `"kind"` field plus payload):
- `session_started` — `{kind, session_id, console_url}`
- `line` — `{kind, text}` — narration from the existing `swarm/events.py:describe`
- `agent_text` — `{kind, text}` — streamed commander reply text chunks
- `terminated` — `{kind}` — bridge closed
- `outputs` — `{kind, files: [filename, ...]}` — result of `download_outputs`
  (moves into this module too), including the empty-list case
- `error` — `{kind, message}` — any exception during the run, caught so the
  generator ends cleanly instead of crashing its caller

This is the one place that knows how to drive a war-room session end to end.
Both `run_war_room.py` (prints based on `kind`, writes the transcript file)
and `webapp.py` (forwards each dict as SSE) consume it. No duplicated event
loop.

### Backend (`webapp.py`, new)

- `GET /` — serves `web/index.html`.
- `GET /events` (SSE) — on connect:
  - If a run is already in progress (simple in-process flag), immediately
    sends one `error` event ("a run is already in progress") and closes.
  - Reads `coordinator`/`environment` from `.swarm_ids.json` via the
    existing `IdStore`. If either is missing, sends one `error` event with
    the exact setup commands (mirrors today's `SystemExit` message in
    `run_war_room.py`) and closes.
  - Otherwise calls `swarm.runner.run_session(...)` and forwards each
    yielded dict as `data: <json>\n\n`.
- `GET /outputs/{filename}` — static mount of the `outputs/` directory, for
  downloading the finished `.docx` (and the transcript, if useful).

### Frontend (`web/index.html`, new)

Single static file, no build step:
- Title ("Incident War-Room") and a short static one-line description of
  INC-4417.
- "Start Incident" button — disabled while a run is in progress, re-enabled
  after (each click starts a fresh session; re-running is expected).
- A status line (idle / running / done / error).
- A scrolling monospace log panel, fed by `EventSource('/events')`, one line
  per `line`/`agent_text`/`error` event, auto-scrolling to the bottom.
- On the `outputs` event: render a download link per file
  (`/outputs/<filename>`) and the Console URL from `session_started` for
  "view full session."
- `error` events render in the log in a visually distinct (red) style rather
  than failing silently.

## Error handling

- Missing setup IDs → clear message in the log with the exact commands to
  run, matching today's CLI behavior.
- Mid-run API failure (e.g. `403 permission_error`) → caught inside
  `run_session`, yielded as an `error` event, shown in the log; the SSE
  connection then closes normally rather than the server crashing.
- Zero output files → same "no files produced, check the session trace"
  messaging as today's CLI, shown as a `line`/`error` event instead of
  crashing.

## Dependencies

Add `fastapi` and `uvicorn` to `requirements.txt`. Launch with
`python webapp.py` (calls `uvicorn.run(...)` on `127.0.0.1:8000` and prints
the URL to open).

## Testing

- The event-shaping in `swarm/runner.py` — turning an SDK event object into
  one of the `kind` dicts above — gets unit tests the same way
  `swarm/events.py` does today: feed fake event objects, assert the yielded
  `kind`/fields, no network or API key required.
- `run_session` itself (like `run_war_room.main()` today) is an integration
  function requiring a live API key and isn't unit tested — consistent with
  the existing split where only pure logic under `swarm/` is covered by
  `pytest`.
- No new UI/browser tests; this is verified manually against a live run.

## Non-goals

- Running setup scripts from the UI.
- Free-text / custom incident input.
- Multi-scenario support, auth, or remote hosting.
- Persisting run history across page reloads.
