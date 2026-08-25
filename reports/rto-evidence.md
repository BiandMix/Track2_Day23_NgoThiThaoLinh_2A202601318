# RTO/RPO Evidence - Lab 23 (COMPLETED)

## Drill 1 - baseline without DR

| Metric | Result | Evidence |
|---|---:|---|
| First outage | 2026-08-25T16:17:14Z | `chaos/chaos-events.jsonl:1` |
| Failed requests | 16 | `reports/drill-1-nodr.jsonl:1` |
| Recovery | NO_RECOVERY | `reports/measure-drill-1.json:1` |

## Drill 2 - automated DR

| Milestone | Seconds from outage | Evidence |
|---|---:|---|
| First user error | 0.1s | `reports/drill-2-withdr.jsonl:1` |
| Health check detects Region A | 19.3s | `reports/health-events.jsonl:1` |
| Snapshot restore complete | 19.5s | `reports/failover-events.jsonl:2` |
| Region B ready | 19.6s | `reports/failover-events.jsonl:4` |
| DNS cutover | 22.3s | `reports/failover-events.jsonl:5` |
| First successful request from B | 22.8s | `reports/drill-2-withdr.jsonl:1` |

| Metric | Result | Target | Verdict |
|---|---:|---:|---|
| RTO - inference API | 22.8s | 300s | PASS |
| RPO - vector DB | 12.0s / 6 docs | 300s | PASS |

## RTO breakdown

| Component | Seconds | Evidence | Reduction |
|---|---:|---|---|
| Health-check detection floor | 15.0s | `reports/health-events.jsonl:1` | Tune interval carefully |
| Snapshot restore | 0.2s | `reports/failover-events.jsonl:2` | Keep replica warm |
| GPU pool warm-up | 6.3s | `reports/failover-events.jsonl:4` | Pre-warm standby |
| DNS/LB TTL cache | 0.5s | `reports/failover-events.jsonl:5` | Reduce incident TTL |

Measured RTO: `22.8s`. Measured RPO: `12.0s`, with `6` documents lost.
