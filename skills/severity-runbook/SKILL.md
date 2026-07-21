---
name: severity-runbook
description: BTS-Synthetic production severity matrix, SLO burn thresholds, known failure modes and rollback criteria. Use whenever classifying an incident's severity, forming a root-cause hypothesis, or deciding whether to roll back. Trigger on any request to triage, diagnose, classify, or mitigate a production incident.
---

# Production Severity Runbook

## Severity matrix

Classify by customer impact, not by how alarming the graph looks.

| Sev | Criterion (any one matches) | Response |
| --- | --- | --- |
| SEV1 | Total outage of a revenue path, OR confirmed data loss, OR >25% of requests failing globally | Page exec on-call. Bridge within 5 min. Status page immediately. |
| SEV2 | A revenue path degraded for a subset of users, OR 5–25% error rate, OR a hard dependency down with degraded fallback | Page service owner. Bridge within 15 min. Status page within 30 min. |
| SEV3 | Single non-critical service degraded, no revenue impact, fallback holding | Ticket. Business hours. No status page. |
| SEV4 | Cosmetic, internal-only, or fully absorbed by redundancy | Ticket. Next sprint. |

**Checkout is a revenue path.** Any confirmed checkout failure is SEV2 minimum,
regardless of the percentage affected.

## SLO burn thresholds

Checkout API SLO: 99.9% success, 30-day window. Error budget = 43.2 min/month.

| Burn rate | Meaning | Action |
| --- | --- | --- |
| >14.4x | Budget exhausted in <2 days | Page. Treat as SEV1/SEV2. |
| 6x–14.4x | Budget exhausted in 2–5 days | Page. SEV2. |
| 1x–6x | Elevated, budget survives the window | Ticket, monitor |
| <1x | Within budget | No action |

## Known failure modes

Check these before hypothesising anything novel. In order of historical frequency:

1. **Config change without staged rollout.** Our config deploys are not canaried.
   A bad value reaches all regions in one push. Signature: onset is sharp, error
   rate steps rather than ramps, and onset correlates within ~60 min of a
   config-type entry in the change log.
2. **Connection pool exhaustion under retry storm.** A downstream slowdown causes
   client retries, which exhaust the pool, which causes more failures. Signature:
   latency climbs *before* errors, and the error rate is self-sustaining after
   the original trigger clears.
3. **Certificate or credential expiry.** Signature: total, instant, and
   region-uniform. If failures are partial or regional, this is not it.
4. **Regional dependency failure.** Signature: error rate correlates precisely
   with a region boundary and no change was deployed.
5. **Traffic-shape change exceeding capacity.** Signature: gradual ramp, no
   deploy correlation, request volume elevated above the trailing baseline.

## Rollback criteria

Roll back when **all three** hold:

- A change was deployed within 2 hours before onset
- The change touches the failing path
- Rollback is safe — no schema migration, no irreversible data write since deploy

Roll back **immediately without waiting for root cause** if it is SEV1. Diagnosis
is cheaper after the bleeding stops.

Do **not** roll back when:
- The change predates onset by more than 2 hours with no plausible latency
- Rollback would itself cause data inconsistency
- Error rate is already recovering on its own

## Hypothesis discipline

State confidence explicitly, and state disconfirming evidence. A correlated
deploy is evidence, not proof — two things can change in the same window. If a
second signal (traffic anomaly, dependency alert) is present in the same window,
say so rather than dismissing it; someone else on the bridge may be looking at
the other half of the same event.
