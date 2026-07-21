"""Agent evals for the Incident War-Room — grading the run, not the code.

`pytest` (once swarm/ lands) proves the setup scripts and run loop are wired
correctly. It cannot tell you whether a given run's postmortem actually
reconciled the incident's two candidate causes, or whether the fan-out was
genuinely parallel. That's what this package is for. See PRD.md §10 and
evals/README.md.
"""
