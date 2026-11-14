"""G3.7 — MIOpen EvaluateInvokers minimal reproduction WITHOUT Ultralytics.

    python tests/g3_evaluateinvokers_repro.py --out ../raw/g3_evi_<env>.json \
        --environment-id ENV_X [--repeat-anomaly 2]

Anomaly under investigation (mission §4.3): MIOpen logs
``MIOpen: Error [EvaluateInvokers] Invalid elapsed time detected ... failed
condition: elapsed <= 0`` (solver_finders.cpp) during solver benchmarking on
gfx1151 — observed 4x on ENV B (source-built MIOpen 3.6.2.f0a5d266) and 1x in
one aborted official-wheel attempt, 0x in the clean official re-run.

Design:
  - each probe is a SEPARATE subprocess running exactly one pure-torch Conv2d
    configuration (fwd+bwd) with a controlled MIOpen cache home, so every
    EvaluateInvokers occurrence is attributable to one config
  - stderr is captured per subprocess and archived verbatim
  - fresh-cache mode forces the Find-1 benchmarking path where the anomaly
    lives; default-cache mode is the control
  - a designated config is repeated to test determinism
  - no Ultralytics import anywhere in the probe path
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROBE_SRC = r'''
import json, os, sys, time
import torch
cfg = json.loads(sys.argv[1])
dev = torch.device("cuda:0")
torch.manual_seed(0)
c = cfg["conv"]
m = torch.nn.Sequential(
    torch.nn.Conv2d(c["in"], c["out"], c["k"], stride=c["stride"], padding=c["pad"],
                    bias=False, dtype=torch.float16 if cfg["dtype"] == "fp16" else torch.float32),
    torch.nn.BatchNorm2d(c["out"], dtype=torch.float16 if cfg["dtype"] == "fp16" else torch.float32),
).to(dev)
if cfg["dtype"] == "fp16":
    m = m.half()
x = torch.randn(c["batch"], c["in"], c["hw"], c["hw"], device=dev,
                dtype=torch.float16 if cfg["dtype"] == "fp16" else torch.float32)
opt = torch.optim.SGD(m.parameters(), lr=0.01)
t0 = time.time()
out = m(x)
loss = out.float().square().mean()
loss.backward()
opt.step()
torch.cuda.synchronize()
print(json.dumps({"wall_s": round(time.time() - t0, 2),
                  "loss_finite": bool(torch.isfinite(loss).item()),
                  "torch": torch.__version__, "hip": torch.version.hip or ""}))
'''


def probe(python_exe: str, cfg: dict, cache_dir: str | None, workdir: Path,
          env_label: str) -> dict:
    """One subprocess = one conv config + one cache home. Returns verdict."""
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(("MIOPEN", "ROCM"))}
    env["PYTHONPATH"] = ""
    if cache_dir:
        env["MIOPEN_USER_DB_PATH"] = cache_dir  # fresh DB -> Find-1 benchmarking path
        env["HOME"] = cache_dir
        env["USERPROFILE"] = cache_dir
    env["HIP_VISIBLE_DEVICES"] = "0"
    probe_file = workdir / "probe_inner.py"
    probe_file.write_text(PROBE_SRC, encoding="utf-8")
    try:
        p = subprocess.run([python_exe, "-u", "-I", str(probe_file), json.dumps(cfg)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900, env=env, cwd=str(workdir))
    except subprocess.TimeoutExpired:
        return {"config": cfg, "exit": "TIMEOUT", "evaluate_invokers_errors": -1,
                "stderr_excerpt": "subprocess timeout 900s"}
    err = p.stderr or ""
    n_err = err.count("EvaluateInvokers")
    n_invalid = err.count("Invalid elapsed time")
    lines = [l for l in err.splitlines()
             if "EvaluateInvokers" in l or "Invalid elapsed" in l or "solver_finders" in l]
    out = {"config": cfg, "exit": p.returncode, "cache": os.path.basename(cache_dir or "default"),
           "evaluate_invokers_lines": n_err, "invalid_elapsed_lines": n_invalid,
           "stdout_tail": (p.stdout or "").strip()[-300:],
           "stderr_excerpt": "\n".join(lines[:12])[:2000], "stderr_bytes": len(err)}
    if p.returncode != 0 and n_err == 0:
        out["stderr_excerpt"] = err[-1500:]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--python", required=True, help="target env python")
    ap.add_argument("--environment-id", required=True)
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    OUT = {"environment_id": args.environment_id,
           "run_id": args.run_id or f"g3evi_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
           "python": args.python, "started_utc": datetime.now(timezone.utc).isoformat(),
           "probes": [], "summary": {}, "limitations": []}
    if os.path.isabs(args.out):
        out_path = Path(args.out)
    else:
        out_path = Path(args.out)

    workdir = Path(tempfile.mkdtemp(prefix="g3evi_"))
    convs = [
        {"in": 3, "out": 8, "k": 3, "stride": 1, "pad": 1, "batch": 4, "hw": 32},
        {"in": 3, "out": 16, "k": 3, "stride": 2, "pad": 1, "batch": 8, "hw": 64},
        {"in": 16, "out": 32, "k": 5, "stride": 1, "pad": 2, "batch": 16, "hw": 64},
        {"in": 32, "out": 64, "k": 3, "stride": 2, "pad": 1, "batch": 16, "hw": 128},
    ]
    with tempfile.TemporaryDirectory(prefix="g3evi_cache_") as cache:
        cache_fresh = str(Path(cache) / "fresh_home")
        os.makedirs(cache_fresh, exist_ok=True)
        probes = []
        for dtype in ("fp16", "fp32"):
            for i, c in enumerate(convs):
                probes.append({"dtype": dtype, "conv": c, "cache": cache_fresh})
        # determinism check: repeat the first fp16 config on ANOTHER fresh cache
        probes.append({"dtype": "fp16", "conv": convs[0],
                       "cache": str(Path(cache) / "fresh_home_2"), "repeat_of": 0})
        os.makedirs(Path(cache) / "fresh_home_2", exist_ok=True)
        for i, pr in enumerate(probes):
            cache_dir = pr.pop("cache")
            repeat_of = pr.pop("repeat_of", None)
            r = probe(args.python, pr, cache_dir, workdir, args.environment_id)
            r["probe_index"] = i
            r["repeat_of"] = repeat_of
            OUT["probes"].append(r)
            OUT_PATH = out_path
            OUT_PATH.write_text(json.dumps(OUT, indent=2), encoding="utf-8")  # incremental
            print(f"[probe {i}] {pr['dtype']} conv{pr['conv']['in']}->{pr['conv']['out']} "
                  f"exit={r['exit']} evi_errors={r['evaluate_invokers_lines']} "
                  f"invalid={r['invalid_elapsed_lines']}", flush=True)

    n_probes = len(OUT["probes"])
    n_evi = sum(1 for r in OUT["probes"] if r.get("evaluate_invokers_lines", 0) > 0)
    n_invalid = sum(1 for r in OUT["probes"] if r.get("invalid_elapsed_lines", 0) > 0)
    n_fail = sum(1 for r in OUT["probes"] if r.get("exit") not in (0,) and r.get("exit") != "TIMEOUT")
    n_timeout = sum(1 for r in OUT["probes"] if r.get("exit") == "TIMEOUT")
    # determinism verdict on the repeat pair
    rep = next((r for r in OUT["probes"] if r.get("repeat_of") is not None), None)
    orig = OUT["probes"][rep["repeat_of"]] if rep else None
    OUT["summary"] = {
        "probes_total": n_probes, "probes_with_evaluate_invokers_error": n_evi,
        "probes_with_invalid_elapsed": n_invalid, "probes_failed": n_fail,
        "probes_timeout": n_timeout,
        "repeat_deterministic": bool(orig and rep and
                                     rep.get("invalid_elapsed_lines") == orig.get("invalid_elapsed_lines")
                                     and rep.get("evaluate_invokers_lines") == orig.get("evaluate_invokers_lines")),
        "anomaly_reproduced": n_evi > 0,
    }
    OUT["completed_utc"] = datetime.now(timezone.utc).isoformat()
    OUT_PATH.write_text(json.dumps(OUT, indent=2), encoding="utf-8")
    print(f"SUMMARY {json.dumps(OUT['summary'])}", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
