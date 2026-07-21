"""Model IDs for the Incident War-Room.

Bare aliases only. Never append a date suffix — the alias always resolves to
the current snapshot, and a hand-written suffix will eventually 404.
"""

# Orchestration and synthesis: reconciling three specialist findings into one
# coherent postmortem is the hardest reasoning in the system.
COMMANDER = "claude-opus-4-8"

# Adversarial postmortem review (stretch goal).
REVIEWER = "claude-opus-4-8"

# SRE, Security and Comms. All three war-room outputs are high-stakes — the
# Comms draft could reach customers verbatim — so none is tiered down.
SPECIALIST = "claude-sonnet-5"

# Defined but unused. See PRD §11: a Timeline Assembler doing mechanical
# extraction from alert payloads is where this tier would legitimately fit.
LIGHTWEIGHT = "claude-haiku-4-5"
