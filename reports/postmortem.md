# Postmortem - DR Drill Lab 23 (COMPLETED)

## Timeline

| ISO time | Event | Evidence |
|---|---|---|
| 2026-08-25T16:17:14Z | Region A outage started | `chaos/chaos-events.jsonl:1` |
| 2026-08-25T16:17:14Z | First user errors | `reports/drill-1-nodr.jsonl:1` |
| 2026-08-25T16:20:29Z | Health checker marked A unhealthy | `reports/health-events.jsonl:1` |
| 2026-08-25T16:20:32Z | Snapshot restored and target verified | `reports/failover-events.jsonl:2` |
| 2026-08-25T16:20:32Z | DNS cutover to B | `reports/failover-events.jsonl:5` |

## RTO/RPO and gap analysis

- RTO target: 300s; measured: `22.8s`; gap: `277.2s`.
- RPO target: 300s; measured: `12.0s`; gap: `288.0s`; `6` documents lost.
- Largest RTO contributor: the `15.0s` health-check detection floor.

## Root cause (5 whys)

1. Users saw errors because the active inference region was paused.
2. The edge continued routing to Region A until failover.
3. Detection required three consecutive readiness failures.
4. Region B needed state restore and pool warm-up before serving.
5. The runbook had to coordinate health, state, compute, and DNS in order.

## Action items

| # | Action | Owner | Deadline |
|---|---|---|---|
| 1 | Replicate vector snapshots every 30s | Data platform | Next sprint |
| 2 | Pre-warm standby GPU capacity | SRE | Next sprint |

## Reflection

The detection floor is `15.0s`, about 66% of the measured `22.8s` RTO. Reducing the interval can lower RTO, but increases false positives and flapping risk. `docs_lost` represents customer documents written after the last replicated snapshot.
