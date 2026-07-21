# Service Topology — Checkout Path

## Dependency chain

```
edge-cdn  →  api-gateway  →  checkout-api  →  payment-gateway  →  [external PSP]
                                  │
                                  ├──→  inventory-svc        (hard dependency)
                                  ├──→  pricing-svc          (hard dependency)
                                  ├──→  session-store        (Redis, hard)
                                  └──→  order-db             (Postgres, hard)
```

## Services

| Service | Owner role | Criticality | Notes |
| --- | --- | --- | --- |
| `edge-cdn` | Platform | SEV1 path | WAF runs here. Global anycast. |
| `api-gateway` | Platform | SEV1 path | Auth termination. Rate limiting configured here. |
| `checkout-api` | Payments | SEV1 path | The affected service. Stateless, autoscaled. |
| `payment-gateway` | Payments | SEV1 path | Connection-pooled. **Pool size is a config value, not autoscaled.** |
| `inventory-svc` | Fulfilment | SEV2 | Degrades to "assume in stock" on failure |
| `pricing-svc` | Commerce | SEV2 | Degrades to cached price on failure |
| `session-store` | Platform | SEV1 path | Redis cluster, per-region |
| `order-db` | Payments | SEV1 path | Postgres, primary in us-east-1, read replicas per region |

## Regional deployment

| Region | checkout-api | payment-gateway | session-store |
| --- | --- | --- | --- |
| us-east-1 | ✅ | ✅ (pool: 200) | ✅ |
| us-west-2 | ✅ | ✅ (pool: 200) | ✅ |
| eu-west-1 | ✅ | ✅ (pool: **50**) | ✅ |
| ap-southeast-1 | ✅ | ✅ (pool: **50**) | ✅ |

Pool sizes are set per-region in `checkout-api` config. EU and APAC were sized
smaller during a 2025 cost-reduction exercise and have not been revisited.

## Credentials and trust

- `checkout-api` holds: `payment-gateway` service token, `order-db` write
  credentials, `session-store` credentials
- `payment-gateway` holds: external PSP API key (scoped to charge + refund)
- `order-db` write credentials are **shared** between `checkout-api` and
  `fulfilment-worker`
- `payment-gateway` accepts requests from `checkout-api` without revalidating
  the customer session — it trusts the caller

## Data classification

| Store | Contains | Classification |
| --- | --- | --- |
| `order-db` | Order records, billing address, last-4 of card | PII + PCI-adjacent |
| `session-store` | Session tokens, cart contents | PII |
| `payment-gateway` | No storage — pass-through to PSP | Card data transits, never persisted |

## Pre-auth surface

`/api/v2/checkout/quote` is **unauthenticated by design** — it returns a price
quote for a cart without requiring login. It is rate-limited at the gateway to
100 req/min per IP. There is no per-ASN limit.

`/api/v2/checkout/session` requires authentication and creates a session record.
