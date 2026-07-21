"""Judged criteria for the postmortem — the things no regex can decide.

Mirrors the Postmortem Reviewer stretch goal's own standard (master plan
`swarm/roster.py`, REVIEWER_SYSTEM / PUBLISH-REVISE-ESCALATE) rather than
inventing a second, possibly-inconsistent bar. The eval judge asks the same
questions the reviewer would, but returns a structured per-criterion verdict
instead of one overall call, so a workshop run shows exactly which dimension
regressed.
"""

CRITERIA = [
    {
        "key": "reconciliation",
        "description": (
            "Does the postmortem address BOTH candidate causes — the CHG-9912 "
            "connection-pool timeout change AND the AS-204889 traffic anomaly — "
            "either by reconciling them into one causal chain or by explicitly "
            "ruling one out with stated reasoning? A postmortem that names only "
            "one cause and drops the other has relayed a single specialist's "
            "answer, not synthesised. An honest INCONCLUSIVE on the security "
            "question, reasoned from past-incidents.json's INC-4102, is a PASS."
        ),
    },
    {
        "key": "blameless",
        "description": (
            "Is the Contributing factors section blameless? It must describe "
            "what the system or process allowed to happen, and reference roles "
            "(e.g. 'the payments engineer'), never name or imply fault on a "
            "specific individual."
        ),
    },
    {
        "key": "action_items_specific",
        "description": (
            "Are the action items specific and verifiable — each with an owner "
            "role and a priority — rather than vague aspirations like 'improve "
            "deployment safety'?"
        ),
    },
    {
        "key": "comms_voice",
        "description": (
            "If a customer-facing status update is included or summarised, does "
            "it avoid stating an unconfirmed root cause, avoid naming or blaming "
            "a vendor, and avoid promising a restoration time it cannot support?"
        ),
    },
    {
        "key": "open_questions_honest",
        "description": (
            "Where a question is genuinely unresolved (e.g. why US regions were "
            "unaffected), does the postmortem say so explicitly rather than "
            "overstating certainty?"
        ),
    },
]


def build_judge_prompt(postmortem_text: str, incident_ticket_text: str) -> str:
    """Assemble the LLM-judge prompt. Pure string assembly — no network call."""
    criteria_block = "\n".join(
        f"{i}. **{criterion['key']}** — {criterion['description']}"
        for i, criterion in enumerate(CRITERIA, start=1)
    )
    keys = ", ".join(f'"{criterion["key"]}"' for criterion in CRITERIA)
    return f"""\
You are grading a postmortem written by an AI Incident Commander against a
fixed rubric. Be skeptical — your value is catching what a first read misses.

# Source incident ticket

{incident_ticket_text}

# Postmortem under review

{postmortem_text}

# Criteria

{criteria_block}

# Output

Return ONLY a JSON object mapping each criterion key to an object with
"verdict" (one of "PASS", "FAIL", "PARTIAL") and "evidence" (a one-sentence
quote or paraphrase from the postmortem that justifies the verdict).
Keys required, in this exact set: {keys}
"""
