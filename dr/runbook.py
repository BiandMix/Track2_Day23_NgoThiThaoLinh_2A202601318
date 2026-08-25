"""BƯỚC 3c — SINH VIÊN VIẾT. Tự động hoá runbook §4 "Runbook: Region Chính Down".

7 bước trên slide, mỗi bước 1 dòng log có ts. Log này CHÍNH LÀ timeline của postmortem.
  1 xac_nhan_outage          — probe cả 2 region, đừng tin 1 lần fail (dùng nhiều lần
                              hoặc gọi health_checker.probe nếu đã viết xong 3a)
  2 thong_bao_incident       — ts của dòng này là mốc "operator biết tin", LUÔN LUÔN
                              SAU t_outage trong chaos-events (không thể trùng — operator
                              không thể biết ngay giây outage xảy ra). Ghi cả 2 ts vào
                              log để postmortem tính được "độ trễ thông báo".
  3 scale_gpu_pool           — gọi HÀM `failover.failover(...)` MỘT LẦN DUY NHẤT. Hàm
                              đó tự làm đủ 5 bước con (verify/restore/scale/wait/cutover)
                              và tự ghi log riêng vào reports/failover-events.jsonl.
  4 verify_state_replica     — KHÔNG gọi lại failover — chỉ ĐỌC kết quả (vector count +
                              weights ở region phụ) từ dict mà bước 3 trả về, để log vào
                              runbook-run.jsonl cho postmortem đọc 1 chỗ duy nhất.
  5 dns_cutover              — cũng chỉ đọc lại: kết quả cutover có ok hay không.
  6 verify_golden_signals    — 10 request thật vào region phụ: p95 latency + error rate
  7 post_incident            — elapsed_s + lệnh đo RTO

BÁN TỰ ĐỘNG, KHÔNG FULL-AUTO (§4: "failover đầu tiên nên là bán tự động — alert +
1-click confirm — tránh flapping gây failover 2 chiều liên tục"). Mặc định phải hỏi
người vận hành confirm; --auto chỉ dùng trong CI/khi chấm điểm.

Chạy:  python dr/runbook.py --primary a --target b --backend fs
"""
import argparse
import json
import pathlib
import sys
import time

import httpx

sys.path.insert(0, ".")
from dr import failover as fo  # noqa: E402

LOG = pathlib.Path("reports/runbook-run.jsonl")
URL = {"a": "http://127.0.0.1:8001", "b": "http://127.0.0.1:8002"}


def step(n, name, **kw):
    """TODO: ghi 1 dòng {ts, iso, step, name, ...} vào LOG."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {"ts": time.time(), "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "step": n, "name": name, **kw}
    with LOG.open("a", encoding="utf-8") as f: f.write(json.dumps(event) + "\n")
    return event


def confirm(auto: bool, msg: str) -> bool:
    """TODO: auto=True -> True; ngược lại hỏi y/N. Đừng bỏ hàm này đi."""
    return True if auto else input(f"{msg} [y/N] ").strip().lower() == "y"


def run(primary: str, target: str, backend: str, auto: bool) -> dict:
    """TODO: 7 bước ở trên."""
    started = time.time(); checks = {}
    for r in (primary, target):
        try: checks[r] = httpx.get(f"{URL[r]}/readyz", timeout=2).status_code
        except Exception as exc: checks[r] = type(exc).__name__
    step(1, "xac_nhan_outage", primary=primary, target=target, checks=checks)
    if not confirm(auto, f"Failover {primary} -> {target}?"):
        step(2, "thong_bao_incident", cancelled=True); return {"ok": False, "cancelled": True}
    step(2, "thong_bao_incident", primary=primary, target=target, outage_ts=started)
    result = fo.failover(target, backend, wait=60)
    step(3, "scale_gpu_pool", failover_ok=result.get("ok"), result=result)
    state = result.get("state", {})
    step(4, "verify_state_replica", count=state.get("count"), weights=state.get("weights"))
    step(5, "dns_cutover", ok=result.get("ok"), target=target)
    latencies=[]; errors=0
    for _ in range(10):
        t=time.time()
        try:
            rr=httpx.get("http://127.0.0.1:8080/v1/infer", timeout=3)
            if rr.status_code >= 400: errors += 1
        except Exception: errors += 1
        latencies.append((time.time()-t)*1000)
    latencies.sort(); p95=latencies[min(9, max(0, int(len(latencies)*.95)-1))]
    step(6, "verify_golden_signals", p95_ms=round(p95,1), error_rate=errors/10)
    final=step(7, "post_incident", elapsed_s=round(time.time()-started,2), rto_command="python tools/measure_rto.py")
    return {"ok": result.get("ok", False), "failover": result, "runbook": final}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--primary", default="a")
    p.add_argument("--target", default="b")
    p.add_argument("--backend", default="fs", choices=["fs", "minio"])
    p.add_argument("--auto", action="store_true")
    a = p.parse_args()
    print(json.dumps(run(a.primary, a.target, a.backend, a.auto), indent=2))
