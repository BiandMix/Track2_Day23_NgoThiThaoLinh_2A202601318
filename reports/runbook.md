# Runbook - Primary Region Down

| # | Step | Command | Success signal | Owner |
|---|---|---|---|---|
| 1 | Confirm outage | `python chaos/kill_region.py status` | Region A fails readiness three times | On-call |
| 2 | Open incident | `date -Is` | Timestamp in `reports/runbook-run.jsonl` | Incident commander |
| 3 | Restore state | `python state/snapshot.py get --region b --backend fs` | Snapshot and model version restored | Data platform |
| 4 | Scale and wait | `echo full > state/region-b/pool_state; curl -i localhost:8002/readyz` | HTTP 200 and ready true | SRE |
| 5 | Cut over | `python dr/failover.py --target b --backend fs` | Edge active region is b | SRE |
| 6 | Verify signals | `python -c "import httpx; print([httpx.get('http://localhost:8080/v1/infer').status_code for _ in range(10)])"` | 10 successful requests | SRE |
| 7 | Measure RTO | `python tools/measure_rto.py --loadgen reports/drill-2-withdr.jsonl --target-rto 300` | Verdict is PASS | Incident commander |

## Rollback

Rollback to Region A only when Region B fails readiness or golden-signal checks and the incident commander approves. Restore A, verify `/readyz` returns 200, then run `python dr/failover.py --target a --backend fs`. Never cut over before the target is ready.
