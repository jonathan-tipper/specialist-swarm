---
name: threat-triage
description: BTS-Synthetic security incident triage — attack-versus-failure decision tree, blast-radius method, indicator checklist, and regulatory disclosure triggers. Use whenever assessing whether a production incident involves malicious activity, scoping what an attacker could have reached, or deciding whether disclosure obligations are triggered.
---

# Security Incident Triage

## Attack vs. failure decision tree

Work top down. Stop at the first node that resolves.

1. **Is there a plausible non-malicious cause with matching timing?**
   A deploy, config change, cert expiry, or dependency failure in the window.
   → If yes, and it explains the *full* symptom set, verdict is NOT AN ATTACK.
   → If it explains only part, continue. Partial explanation is the most
     commonly missed case: a real failure and a real probe can coincide.

2. **Is the anomalous traffic distinguishable from legitimate traffic?**
   Check: source concentration (single ASN, single /24, single UA string),
   request shape (identical paths, unusual parameter patterns, absent referrers),
   and timing (machine-regular intervals).
   → Concentrated + machine-regular + unusual shape → continue to 3.
   → Diffuse, human-irregular, normal shape → likely legitimate. Note it and
     move on.

3. **Is the traffic targeting something valuable, or just present?**
   Scanning for `/wp-admin` on a service that has never had WordPress is noise.
   Repeated auth attempts, parameter fuzzing on a payment path, or enumeration
   of valid identifiers is not.
   → Targeting a valuable path → continue to 4.
   → Untargeted background noise → NOT AN ATTACK, note as background.

4. **Did it succeed at anything?**
   Any 2xx on an attack-shaped request. Any auth success from the anomalous
   source. Any data-volume anomaly on the response side.
   → Yes → ATTACK, and treat as confirmed compromise until disproven.
   → No, but the attempt is clear and targeted → ATTACK (attempted).
   → Cannot determine from available telemetry → INCONCLUSIVE.

**INCONCLUSIVE is a legitimate verdict.** Use it when telemetry cannot settle
the question. Do not resolve ambiguity by guessing in either direction — an
overstated ATTACK triggers costly response, an overstated NOT AN ATTACK ends
the investigation early.

## The coincidence rule

An anomalous traffic pattern in the same window as a deploy does **not** make
the deploy innocent, and does not make the traffic guilty. Both can be real and
unrelated. Explicitly consider three cases and say which you believe:

| Case | What it looks like |
| --- | --- |
| Traffic caused the failure | Failure onset follows traffic onset; failure scales with traffic volume |
| Failure attracted the traffic | Traffic onset follows failure onset (scanners find error pages) |
| Unrelated coincidence | Onsets are independent; failure symptom is fully explained by the change |

## Blast radius method

Trace outward from the affected service in `service-topology.md`:

1. **Direct reach** — what the affected service can call, and with what credentials
2. **Data reach** — what data stores those credentials can read or write
3. **Lateral reach** — what else shares those credentials or that network segment
4. **Trust reach** — what downstream systems accept output from this service without revalidation

Report reach as *what was possible*, and separately *what telemetry shows was
actually accessed*. Do not conflate them.

## Indicator checklist

- [ ] Source ASN / IP concentration
- [ ] User-agent anomalies or absence
- [ ] Request-rate regularity (machine vs human distribution)
- [ ] Auth failure spike, and any auth success from the anomalous source
- [ ] Response-size anomalies (exfiltration signature)
- [ ] Requests to paths that have never legitimately existed
- [ ] Timing relative to the change log

## Disclosure triggers

Escalate to Legal and Privacy **immediately** if any hold:

| Trigger | Obligation |
| --- | --- |
| Personal data confirmed accessed by an unauthorised party | GDPR Art. 33 — 72h regulator notification |
| Payment card data in the blast radius, access not excluded | PCI DSS incident response, acquirer notification |
| Authentication credentials exposed | Forced rotation + user notification |
| Confirmed unauthorised access to any production data store | Legal review for contractual notification duties |

"Access not excluded" is the trigger, not "access confirmed." If you cannot rule
it out, escalate — the clock starts at awareness, not at proof.
