# Scenario Cards — Option 3

Each team picks ONE. Each is shaped like real incident response: a commander who
runs the bridge and specialists who own lanes.

---

## Card A — Checkout outage (default, fully wired in starter code)

**Coordinator:** "Incident Commander"
- Reads the incident ticket
- Tasks specialists in parallel
- Reconciles conflicting findings into a blameless postmortem

**Specialists:**
1. **SRE Responder** (skill: severity-runbook) — severity, root cause, rollback call
2. **Security Analyst** (skill: threat-triage) — attack or failure, blast radius, disclosure
3. **Comms Lead** (skill: status-page-voice) — customer-facing status update

**The trigger:** `synthetic-data/incident-INC-4417.md` — checkout API 5xx in
EU and APAC, with a config deploy *and* an anomalous traffic spike in the same
window.

**The deliverable:** `outputs/postmortem-INC-4417.docx`

**Why it's the default:** the dual-cause ambiguity means the commander has to
actually reconcile, not relay. That's the part that shows the architecture
earning its keep.

---

## Card B — Data breach response

**Coordinator:** "Breach Response Lead"

**Specialists:**
1. **Forensics** — what was accessed, when, by whom
2. **Legal & Privacy** — which disclosure clocks have started, in which jurisdictions
3. **Customer Trust** — notification drafting, support-team briefing
4. **Engineering** — containment and remediation

**The deliverable:** a regulator-ready incident report plus a customer
notification draft.

---

## Card C — Degraded-dependency triage

**Coordinator:** "Platform On-Call Lead"

**Specialists:**
1. **Dependency Analyst** — which upstream is failing and how far it propagates
2. **Capacity** — can we absorb it, or do we shed load
3. **Product Impact** — which user journeys break, ranked by revenue
4. **Vendor Liaison** — what the provider has said, what to escalate

**The deliverable:** a go/no-go decision memo on failing over.

---

## Picking guidance

| If your team is... | Pick |
| --- | --- |
| Just want the cleanest path | A (Checkout outage — code is ready) |
| Most senior / exec audience | B (Data breach — regulatory stakes) |
| Most relatable to platform / SRE clients | C (Degraded dependency) |
