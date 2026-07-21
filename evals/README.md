# Agent evals

`pytest` (once `swarm/` lands, per the Epic plans) proves the setup scripts
and run loop are wired correctly with no network and no API key. It cannot
tell you whether a *given run's* postmortem actually reconciled the
incident's two candidate causes, was blameless, or fanned out in parallel —
those are PRD §10 criteria, and today they're checked by a human eyeballing
Task G's live run. This package makes that repeatable.

## Structural vs judged

| Check | Module | Tested offline? | PRD reference |
|---|---|---|---|
| All 7 postmortem sections present | `sections.py` | Yes | §8.3, §10 |
| Fan-out was parallel, not serial | `fanout.py` | Yes | G2, Task G Step 2 |
| Reconciles both causes (not relay) | `rubric.py` + `judge.py` | Prompt is; the live call isn't | §10, Task G Step 4 |
| Blameless framing | `rubric.py` + `judge.py` | Prompt is; the live call isn't | §10, Task G Step 5 |
| Action items specific | `rubric.py` + `judge.py` | Prompt is; the live call isn't | §8.3 |
| Comms voice compliance | `rubric.py` + `judge.py` | Prompt is; the live call isn't | `status-page-voice` skill |

The judged criteria reuse the Postmortem Reviewer stretch goal's own rubric
language (master plan `swarm/roster.py`, `REVIEWER_SYSTEM`) rather than
inventing a second, possibly-inconsistent bar — the eval judge asks the same
questions the reviewer would, but returns one verdict per criterion instead
of a single PUBLISH/REVISE/ESCALATE call, so a regression is traceable to a
specific dimension.

`judge.py` is deliberately not unit tested, for the same reason
`run_war_room.py` isn't: it's a thin wrapper around a live model call.
Mocking the Messages API would test the mock. Everything it depends on
(`rubric.build_judge_prompt`, `scorecard.render`) is pure and is tested.

## Running it

```bash
# Structural only — offline, no API key, safe to run in CI
python run_eval.py outputs/postmortem-INC-4417.docx

# Add the live judge — spends one API call
python run_eval.py outputs/postmortem-INC-4417.docx --judge

# Add the fan-out check once an event log exists (see gap below)
python run_eval.py outputs/postmortem-INC-4417.docx --events outputs/events.jsonl --judge
```

## Known gap: no event log yet

`fanout.is_parallel_fanout` expects a JSONL file of the run's SSE events,
one JSON object per line, using the vocabulary the master plan's
`swarm/events.py` already defines (`session.thread_created`,
`agent.thread_message_received`, …). `run_war_room.py` doesn't write one —
it only prints narration to stdout. To wire this up, add a line to the run
loop's event handler that appends `json.dumps(event_dict) + "\n"` to
`outputs/events.jsonl` alongside the existing `describe()` print. Until
that lands, omit `--events` and the scorecard reports that check as `SKIP`
rather than failing on a file that was never produced.

## Extending to a second scenario

If this repo ever runs a second scenario, `sections.py`'s
`POSTMORTEM_SECTIONS` and `rubric.py`'s `CRITERIA` are the two things that
change — same shape as `swarm/roster.py` being the one scenario-specific
module in the main system.
