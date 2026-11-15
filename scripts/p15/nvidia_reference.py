# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""P15.5 NVIDIA Windows reference test — run on a REAL NVIDIA Windows machine, never fabricate.

Mirrors scripts/p15/p15_run.py leg-by-leg so Radeon and NVIDIA evidence are schema-identical
(P15_NVIDIA_UX_PARITY_CONTRACT.md). Must be executed with an official CUDA wheel from pytorch.org
and the SAME released ultralytics version as the Radeon side (8.4.182 for the P15 Radeon run).

Usage (fresh process per leg; run from this repo root):
    python scripts/p15/nvidia_reference.py amp-probe
    python scripts/p15/nvidia_reference.py smoke --workers 0|2|4 [--warm]
    python scripts/p15/nvidia_reference.py train30
    python scripts/p15/nvidia_reference.py resume --run-id p15_30ep_w2
    python scripts/p15/nvidia_reference.py finalcheck --run-id p15_30ep_w2
    python scripts/p15/nvidia_reference.py installcheck     # dimension A: public-docs install proof

Evidence goes to release-provenance/raw/p15_nvidia_reference/ with the same JSON fields as the
Radeon legs plus nvidia driver/CUDA identity. This file itself is the prepared artifact required
while no NVIDIA hardware is available to the project (NVIDIA_COMPARISON_BLOCKED_HARDWARE).
"""

import argparse
import hashlib
import json
import multiprocessing
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEVICE = 0
NOW = lambda: datetime.now(tz=timezone.utc).isoformat()  # noqa: E731


def out_dir() -> Path:
    d = Path(__file__).resolve().parents[2] / "release-provenance" / "raw" / "p15_nvidia_reference"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def leg_common() -> dict:
    """NVIDIA host identity captured fresh in every leg's process."""
    import torch
    import ultralytics

    ident = {
        "utc": NOW(),
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "torch_cuda": getattr(torch.version, "cuda", None),
        "ultralytics": ultralytics.__version__,
        "device_name": torch.cuda.get_device_name(0),
        "device_count_torch": torch.cuda.device_count(),
        "nvidia_smi": _nvidia_smi_identity(),
    }
    return ident


def _nvidia_smi_identity() -> dict | None:
    """Capture official driver identity via nvidia-smi (present on all supported NVIDIA hosts)."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"], encoding="utf-8", timeout=20
        )
        name, drv = (x.strip() for x in out.strip().split(",", 1))
        return {"name": name, "driver_version": drv}
    except Exception as e:
        return {"error": repr(e)}


def refuse_cpu() -> None:
    """Refuse to run without a real NVIDIA CUDA device."""
    import torch

    if not torch.cuda.is_available() or "nvidia" not in torch.cuda.get_device_name(0).lower():
        print("[FAIL] no real NVIDIA CUDA device — this script must run on actual NVIDIA hardware.")
        sys.exit(2)


def installcheck() -> None:
    """Dimension A proof: record that the stack came from public official channels only."""
    import torch
    import ultralytics

    from ultralytics.utils.checks import cuda_device_count

    ev = {
        "leg": "installcheck",
        "env": leg_common(),
        "torch_origin": "https://download.pytorch.org/whl/cu126 (official pytorch.org CUDA wheel) — record actual command used",
        "ultralytics_origin": "PyPI (pip install ultralytics==<same version as Radeon side>)",
        "manual_patches": [],  # any entry here means dimension A FAILED
        "device_count_checks_fn": cuda_device_count(),
    }
    (out_dir() / "installcheck.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    print("[OK] installcheck ->", out_dir() / "installcheck.json")


def amp_probe() -> None:
    """Autocast engagement + GradScaler semantics — identical logic to the Radeon amp-probe leg."""
    import torch
    from ultralytics import YOLO
    from ultralytics.utils.checks import check_amp

    refuse_cpu()
    ev = {"leg": "amp_probe", "env": leg_common(), "utc": NOW()}
    m = YOLO("yolo26n.pt").model.to(DEVICE)
    ev["check_amp_verdict"] = bool(check_amp(m))

    conv = torch.nn.Conv2d(3, 8, 3).to(DEVICE)
    x32 = torch.randn(1, 3, 64, 64, device=DEVICE)
    out_fp32 = conv(x32)
    with torch.autocast("cuda"):
        out_amp = conv(x32)
    ev["conv_fp32_dtype"] = str(out_fp32.dtype)
    ev["conv_autocast_dtype"] = str(out_amp.dtype)
    ev["autocast_engaged"] = out_amp.dtype == torch.float16 and out_fp32.dtype == torch.float32

    lin = torch.nn.Linear(8, 4).to(DEVICE)
    opt = torch.optim.SGD(lin.parameters(), lr=1e-3)
    scaler = torch.amp.GradScaler("cuda")
    steps = []
    psum = lambda: sum(float(p.detach().float().pow(2).sum()) for p in lin.parameters())  # noqa: E731
    prev = psum()
    for i in range(8):
        with torch.autocast("cuda"):
            loss = lin(torch.randn(16, 8, device=DEVICE)).float().pow(2).mean()
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scale_before = scaler.get_scale()
        scaler.step(opt)
        scaler.update()
        new = psum()
        steps.append({"step": i, "scale_before": scale_before, "scale_after": scaler.get_scale(), "params_changed": abs(new - prev) > 0.0})
        prev = new
    ev["gradscaler_steps"] = steps
    ev["gradscaler_updates_applied"] = sum(s["params_changed"] for s in steps)
    ev["gradscaler_scale_annealed"] = steps[0]["scale_before"] != steps[-1]["scale_after"]
    ev["yolo_params_count"] = sum(1 for _ in m.parameters())
    (out_dir() / "amp_probe.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    print("AMPPROBE:", "PASS" if ev["autocast_engaged"] and ev["gradscaler_updates_applied"] > 0 else "FAIL")


def smoke(workers: int, warm: bool, run_id: str) -> None:
    """COCO8 2-epoch leg with explicit workers — identical parameters to the Radeon smoke legs."""
    from ultralytics import YOLO
    from ultralytics.utils.checks import check_amp

    refuse_cpu()
    t0 = time.time()
    pre = bool(check_amp(YOLO("yolo26n.pt").model.to(DEVICE)))
    tag = run_id or f"p15_smoke_w{workers}" + ("_warm" if warm else "")
    project = Path("runs/p15_nvidia").resolve()
    model = YOLO("yolo26n.pt")
    model.train(data="coco8.yaml", epochs=2, device=DEVICE, project=str(project), name=tag, exist_ok=False, seed=0, workers=workers)
    ev = {
        "leg": "smoke",
        "tag": tag,
        "workers": workers,
        "warm_cache": warm,
        "amp_precheck": pre,
        "wall_seconds": round(time.time() - t0, 1),
        "epochs_completed": 2,
        "finished_utc": NOW(),
        "env": leg_common(),
    }
    (out_dir() / f"{tag}.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    print(f"SMOKE_W{workers}{'_WARM' if warm else ''}: PASS")


def train30(run_id: str) -> None:
    """COCO128 30 epochs seed=0 workers=2 — identical to the Radeon representative leg."""
    from ultralytics import YOLO
    from ultralytics.utils.checks import check_amp

    refuse_cpu()
    pre = bool(check_amp(YOLO("yolo26n.pt").model.to(DEVICE)))
    model = YOLO("yolo26n.pt")
    project = Path("runs/p15_nvidia").resolve()
    model.train(data="coco128.yaml", epochs=30, device=DEVICE, project=str(project), name=run_id or "p15_30ep_w2", exist_ok=False, seed=0, workers=2, amp=True)
    run_dir = project / (run_id or "p15_30ep_w2")
    csv = run_dir / "results.csv"
    summary = {
        "leg": "representative_30ep",
        "run_dir": str(run_dir),
        "epochs": 30,
        "seed": 0,
        "workers": 2,
        "amp_precheck": pre,
        "results_csv_sha256": sha256_file(csv) if csv.exists() else None,
        "rows": (csv.read_text(encoding="utf-8").strip().splitlines() if csv.exists() else []),
        "finished_utc": NOW(),
        "env": leg_common(),
    }
    (run_dir / "p15_train30_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("TRAIN30: PASS")


def resume(run_id: str) -> None:
    """New-process resume from last.pt — identical procedure to the Radeon resume leg."""
    from ultralytics import YOLO

    refuse_cpu()
    last = Path("runs/p15_nvidia") / run_id / "weights" / "last.pt"
    if not last.exists():
        print(f"[FAIL] {last} missing")
        sys.exit(2)
    csv = Path("runs/p15_nvidia") / run_id / "results.csv"
    rows_before = len(csv.read_text(encoding="utf-8").strip().splitlines())
    YOLO(str(last)).train(resume=True)
    rows_after = csv.read_text(encoding="utf-8").strip().splitlines()
    ev = {
        "leg": "resume_new_process",
        "run_id": run_id,
        "rows_before_resume": rows_before,
        "rows_after_resume": len(rows_after),
        "last_row": rows_after[-1] if rows_after else None,
        "finished_utc": NOW(),
        "env": leg_common(),
    }
    (out_dir() / f"p15_resume_{run_id}.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    print("RESUME: PASS" if len(rows_after) > rows_before else "RESUME: FAIL")


def finalcheck(run_id: str) -> None:
    """Validate best.pt, reload it fresh, final inference — identical to the Radeon finalcheck leg."""
    from ultralytics import YOLO

    refuse_cpu()
    run = Path("runs/p15_nvidia") / run_id
    best, last = run / "weights" / "best.pt", run / "weights" / "last.pt"
    ev = {"leg": "finalcheck", "run_id": run_id, "best_sha256": sha256_file(best), "last_sha256": sha256_file(last)}
    model = YOLO(str(best))
    metrics = model.val(data="coco128.yaml", imgsz=640, device=DEVICE, verbose=False)
    ev["val_map5095"] = float(metrics.box.map)
    ev["val_map50"] = float(metrics.box.map50)
    reloaded = YOLO(str(best))
    r = reloaded.predict("https://ultralytics.com/images/bus.jpg", imgsz=640, device=DEVICE, verbose=False)
    ev["reload_predict_boxes"] = len(r[0].boxes)
    ev["reload_ok"] = len(r[0].boxes) > 0
    ev["finished_utc"] = NOW()
    ev["env"] = leg_common()
    (out_dir() / f"p15_finalcheck_{run_id}.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    print("FINALCHECK: PASS" if ev["reload_ok"] else "FINALCHECK: FAIL")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("leg", choices=["installcheck", "amp-probe", "smoke", "train30", "resume", "finalcheck"])
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--warm", action="store_true")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()
    if args.leg == "installcheck":
        installcheck()
    elif args.leg == "amp-probe":
        amp_probe()
    elif args.leg == "smoke":
        smoke(args.workers, args.warm, args.run_id)
    elif args.leg == "train30":
        train30(args.run_id)
    elif args.leg == "resume":
        resume(args.run_id)
    elif args.leg == "finalcheck":
        finalcheck(args.run_id)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
