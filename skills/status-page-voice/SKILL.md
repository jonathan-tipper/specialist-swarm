---
name: status-page-voice
description: BTS-Synthetic customer-facing incident communication standards — status page template, tone rules, and the rules on what may and may not be claimed before root cause is confirmed. Use whenever drafting a status page update, customer incident notification, or any external message during an active incident.
---

# Status Page Voice

## Template

Every update uses this shape. Do not improvise structure mid-incident.

```
**[STATUS] — [Component]**
[Timestamp UTC]

[What customers are experiencing — one sentence, plain language.]

[What we are doing — one or two sentences, present tense.]

[What customers should do, if anything. Omit this line if the answer is nothing.]

Next update: [time or interval].
```

Status values, in order of progression: **Investigating → Identified →
Monitoring → Resolved**. Never skip backwards without explanation. Never post
Resolved until recovery has held for at least 30 minutes.

## What you may and may not say

| Before root cause is confirmed | |
| --- | --- |
| ✅ "A subset of customers are experiencing errors at checkout." | Observable symptom |
| ✅ "We have identified a likely cause and are testing a fix." | Progress without a claim |
| ✅ "We do not yet know the cause." | Honest, and better than a wrong guess |
| ❌ "This was caused by a configuration change." | Unconfirmed attribution |
| ❌ "This is not a security incident." | Never claim this before Security has a verdict |
| ❌ "No customer data was affected." | An assertion you may have to retract |
| ❌ "Service will be restored within the hour." | A promise you cannot support |
| ❌ "A third-party provider is experiencing issues." | Never name or blame a vendor externally |

**The retraction rule.** The cost of saying "we don't know yet" is mild customer
frustration. The cost of retracting a confident claim is trust you do not get
back. When in doubt, say less.

## Tone rules

- **Plain language.** "Customers may see errors when completing a purchase" —
  not "the checkout service is returning elevated 5xx responses."
- **Active voice, first person plural.** "We are investigating." Not "the issue
  is being investigated."
- **No hedging stacks.** "We believe it may be possible that" is one sentence
  saying nothing. Pick a confidence level and state it once.
- **No apologising in every paragraph.** Once, sincerely, at Resolved. Repeated
  apologies read as panic.
- **No internal vocabulary.** No service names, no severity levels, no runbook
  terms, no incident IDs customers cannot use.
- **No emoji. No exclamation marks.**

## Cadence

| Severity | Update interval | First update due |
| --- | --- | --- |
| SEV1 | Every 30 min, without fail | Within 15 min of detection |
| SEV2 | Every 60 min | Within 30 min of detection |
| SEV3+ | No status page unless customers ask | — |

Post the update even when there is nothing new. "We are still investigating and
have no further update. Next update at 14:30 UTC." Silence reads as absence.

**Commit to a next-update time in every post, and meet it.** A missed committed
update is worse than a longer stated interval.

## Resolved posts

At Resolved, state: what happened in one plain sentence, when it started and
ended, who was affected, and whether a fuller writeup will follow. Do not
publish root-cause detail at Resolved unless it is confirmed — that is what the
postmortem is for.
