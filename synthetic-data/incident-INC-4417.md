# INC-4417 — Checkout API elevated 5xx, EU + APAC

**Status:** ACTIVE
**Declared:** 2026-07-21 13:42 UTC
**Detected by:** Automated alert — `checkout-api-error-rate` (Datadog monitor #8821)
**Current severity:** SEV2 (provisional — pending on-bridge classification)
**Incident channel:** #inc-4417
**Bridge opened:** 2026-07-21 13:51 UTC

## On-call acknowledgements

| Time (UTC) | Who | Note |
| --- | --- | --- |
| 13:42 | Auto-page → platform-oncall | — |
| 13:47 | platform-oncall ack | "Looking. Error rate climbing." |
| 13:51 | Bridge opened, IC assigned | — |
| 13:58 | security-oncall joined | "Saw the traffic alert, joining." |

## Symptoms

Checkout API returning HTTP 502 and 503 for a subset of requests. Customers
see "Something went wrong, please try again" at the payment step. Retry
sometimes succeeds.

### Error rate — `checkout-api`, 5-minute buckets

| Time (UTC) | Requests | 5xx | Error rate |
| --- | --- | --- | --- |
| 12:30 | 41,203 | 12 | 0.03% |
| 12:45 | 40,880 | 9 | 0.02% |
| 13:00 | 42,110 | 14 | 0.03% |
| 13:15 | 41,660 | 31 | 0.07% |
| 13:30 | 43,020 | 402 | 0.93% |
| 13:35 | 44,190 | 3,981 | 9.01% |
| 13:40 | 44,720 | 5,102 | 11.41% |
| 13:45 | 45,330 | 5,644 | 12.45% |
| 14:00 | 45,900 | 5,808 | 12.65% |
| 14:15 | 46,120 | 5,891 | 12.77% |

Onset is sharp between 13:15 and 13:35. Error rate has plateaued, not recovered.

### Affected regions

| Region | Error rate | Note |
| --- | --- | --- |
| eu-west-1 | 21.4% | Worst affected |
| ap-southeast-1 | 18.9% | |
| us-east-1 | 0.04% | Baseline — unaffected |
| us-west-2 | 0.03% | Baseline — unaffected |

### Latency

p50 unchanged at 82ms. p99 up from 340ms to 1,180ms in affected regions only.
Latency rise begins ~13:20, roughly 10 minutes before the error-rate step.

## Raw alert payloads

```json
[
  {
    "monitor": "checkout-api-error-rate",
    "id": 8821,
    "triggered_at": "2026-07-21T13:42:11Z",
    "threshold": "error_rate > 1% over 5m",
    "value": 0.0901,
    "scope": "service:checkout-api",
    "message": "Checkout API 5xx above threshold"
  },
  {
    "monitor": "payment-gateway-connection-pool",
    "id": 8834,
    "triggered_at": "2026-07-21T13:37:48Z",
    "threshold": "pool_available < 5 over 5m",
    "value": 0,
    "scope": "service:checkout-api,region:eu-west-1",
    "message": "Connection pool to payment-gateway exhausted"
  },
  {
    "monitor": "waf-anomalous-source-volume",
    "id": 9102,
    "triggered_at": "2026-07-21T13:19:30Z",
    "threshold": "single_asn_request_share > 15% over 10m",
    "value": 0.231,
    "scope": "edge:global",
    "message": "23.1% of edge traffic from AS-204889 (baseline 0.4%)"
  }
]
```

## Edge traffic detail (from WAF alert 9102)

Between 13:19 and 14:15, AS-204889 accounted for 23.1% of edge requests, up
from a 0.4% trailing baseline.

| Property | Value |
| --- | --- |
| Source ASN | AS-204889 |
| Distinct source IPs | 1,847 across 6 /24 ranges |
| Target paths | `/api/v2/checkout/session` (94%), `/api/v2/checkout/quote` (6%) |
| User-agent | `okhttp/4.9.3` on 100% of requests |
| Request interval | Median 1.02s, standard deviation 0.04s |
| HTTP status distribution | 502: 61%, 503: 22%, 200: 17% |
| Response size on 200s | Median 1.4 KB — matches normal quote response |
| Auth | 100% unauthenticated; all requests hit the pre-auth quote path |
| Geography | Registered to a mobile carrier, ap-southeast region |

No authentication attempts. No requests to paths outside the two above. No
parameter variation beyond normal quote fields.

## What we know

- The error rate stepped sharply between 13:15 and 13:35 and has plateaued
- Only eu-west-1 and ap-southeast-1 are affected; US regions are clean
- Connection pool to `payment-gateway` is exhausted in eu-west-1
- Latency began rising ~10 minutes before errors
- Anomalous single-ASN traffic began at ~13:19
- A change was deployed at 13:04 (see `recent-changes.json`)

## What we do not know

- Whether the deploy, the traffic, or both caused this
- Whether the AS-204889 traffic is an attack, a misbehaving mobile client, or a
  partner integration nobody documented
- Why US regions are unaffected
- Whether any customer completed a payment that was charged but not recorded
