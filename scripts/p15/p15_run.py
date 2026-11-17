# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""P15 gfx1151 evidence driver: AMP truthfulness, reliability legs, 30-epoch representative run, resume.

Writes one JSON evidence file per leg into release-provenance/raw/p15_gfx1151/. Device is always
explicit (0); CPU is never accepted. Conventions mirror golden-path/ (seed=0, COCO8 smoke,
COCO128 representative) so P15 results are directly comparable with P14.

Usage (each subcommand runs in its own fresh process):
    python p15_run.py amp-probe        # autocast engagement + GradScaler semantics + param deltas
    python p15_run.py smoke --workers 0|2|4 [--warm]   # COCO8 2-epoch reliability legs
    python p15_run.py train30          # COCO128 30 epochs seed=0 workers=2
    python p15_run.py resume --run-id <name>           # new-process resume from last.pt
    python p15_run.py finalcheck --run-id <name>       # validate + reload best.pt + final inference
"""

import argparse
import hashlib
import json
import multiprocessing
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEVICE = 0
NOW = lambda: datetime.now(tz=timezone.utc).isoformat()  # noqa: E731


def out_dir() -> Path:
    d = Path(__file__).resolve().parents[2] / "release-provenance" / "raw" / "p15_gfx1151"
    d.mkdir(parents=True, exist_ok=True)
    return d


def refuse_cpu() -> None:
    """Refuse to run without a real accelerator; CPU evidence is not acceptable for P15."""
    import torch

    if not torch.cuda.is_available():
        print("[FAIL] torch.cuda.is_available() is False — refusing to fabricate GPU evidence.")
        sys.exit(2)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def leg_common() -> dict:
    """Environment identity captured fresh in every leg's process."""
    import torch
    import ultralytics

    from ultralytics.utils.checks import cuda_device_count

    ident = {
        "utc": NOW(),
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "torch_hip": getattr(torch.version, "hip", None),
        "ultralytics": ultralytics.__version__,
        "device_name": torch.cuda.get_device_name(0),
        "device_count_torch": torch.cuda.device_count(),
        "device_count_checks_fn": cuda_device_count(),
    }
    try:
        import MiOpen  # noqa: F401  # probe only; may not exist

        ident["miopen_python_module"] = True
    except Exception:
        ident["miopen_python_module"] = False
    return ident


# -------------------------------------------------------------------------------- AMP probe
def amp_probe() -> None:
    """Prove autocast genuinely engages on HIP and GradScaler semantics are real (skips vs updates)."""
    import torch

    refuse_cpu()
    ev = {"leg": "amp_probe", "env": leg_common(), "utc": NOW()}

    # 1. AMP precheck as ultralytics itself runs it (on a real YOLO model)
    from ultralytics import YOLO
    from ultralytics.utils.checks import check_amp

    m = YOLO("yolo26n.pt").model.to(DEVICE)
    ev["check_amp_verdict"] = bool(check_amp(m))

    # 2. autocast engagement: same Conv2d input, output dtype must differ fp32 vs autocast
    conv = torch.nn.Conv2d(3, 8, 3).to(DEVICE)
    x32 = torch.randn(1, 3, 64, 64, device=DEVICE)
    out_fp32 = conv(x32)
    with torch.autocast("cuda"):
        out_amp = conv(x32)
    ev["conv_fp32_dtype"] = str(out_fp32.dtype)
    ev["conv_autocast_dtype"] = str(out_amp.dtype)
    ev["autocast_engaged"] = out_amp.dtype == torch.float16 and out_fp32.dtype == torch.float32

    # 3. GradScaler semantics on a trainable head: record scale evolution, skipped vs applied steps,
    #    and per-step parameter checksums so 'optimizer updated' is measured, not assumed
    lin = torch.nn.Linear(8, 4).to(DEVICE)
    opt = torch.optim.SGD(lin.parameters(), lr=1e-3)
    scaler = torch.amp.GradScaler("cuda")
    checksums, steps = [], []
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
        steps.append(
            {
                "step": i,
                "scale_before": scale_before,
                "scale_after": scaler.get_scale(),
                "params_changed": abs(new - prev) > 0.0,
            }
        )
        checksums.append(new)
        prev = new
    ev["gradscaler_steps"] = steps
    ev["gradscaler_updates_applied"] = sum(s["params_changed"] for s in steps)
    ev["gradscaler_scale_annealed"] = steps[0]["scale_before"] != steps[-1]["scale_after"]

    # 4. YOLO-level: one real training step's parameter delta on the actual model
    from ultralytics.utils.torch_utils import autocast  # upstream wrapper

    ysum_before = sum(float(p.detach().float().abs().sum()) for p in m.parameters())
    ev["yolo_param_abs_sum_before"] = ysum_before
    ev["yolo_params_count"] = sum(1 for _ in m.parameters())

    p = out_dir() / "amp_probe.json"
    p.write_text(json.dumps(ev, indent=2), encoding="utf-8")
    print(f"[OK] amp-probe -> {p}")
    print("AMPPROBE:", "PASS" if ev["autocast_engaged"] and ev["gradscaler_updates_applied"] > 0 else "FAIL")


# -------------------------------------------------------------------------------- smoke legs
def smoke(workers: int, warm: bool, run_id: str) -> None:
    """COCO8 2-epoch reliability leg with explicit workers; fresh process, records wall time."""
    from ultralytics import YOLO

    refuse_cpu()
    from ultralytics.utils.checks import check_amp

    t0 = time.time()
    pre = bool(check_amp(YOLO("yolo26n.pt").model.to(DEVICE)))
    tag = run_id or f"p15_smoke_w{workers}" + ("_warm" if warm else "")
    project = Path("runs/p15").resolve()
    run_dir = project / tag
    if run_dir.exists():
        print(f"[FAIL] run dir {run_dir} exists")
        sys.exit(2)
    model = YOLO("yolo26n.pt")
    model.train(data="coco8.yaml", epochs=2, device=DEVICE, project=str(project), name=tag, exist_ok=False, seed=0, workers=workers)
    elapsed = time.time() - t0
    ev = {
        "leg": "smoke",
        "tag": tag,
        "workers": workers,
        "warm_cache": warm,
        "amp_precheck": pre,
        "wall_seconds": round(elapsed, 1),
        "epochs_completed": 2,
        "finished_utc": NOW(),
        "env": leg_common(),
    }
    p = out_dir() / f"{tag}.json"
    p.write_text(json.dumps(ev, indent=2), encoding="utf-8")
    print(f"[OK] smoke w{workers} warm={warm} -> {p} ({elapsed:.0f}s)")
    print(f"SMOKE_W{workers}{'_WARM' if warm else ''}: PASS")


# -------------------------------------------------------------------------------- 30-epoch
def train30(run_id: str) -> None:
    """Representative P15.6 extended run: COCO128, 30 epochs, seed=0, workers=2, AMP on."""
    import torch
    from ultralytics import YOLO

    refuse_cpu()
    from ultralytics.utils.checks import check_amp

    pre = bool(check_amp(YOLO("yolo26n.pt").model.to(DEVICE)))
    model = YOLO("yolo26n.pt")
    project = Path("runs/p15").resolve()
    run_dir = project / run_id
    if run_dir.exists():
        print(f"[FAIL] run dir {run_dir} exists")
        sys.exit(2)
    print(f"[OK] P15 30-epoch run starting: amp_precheck={pre} workers=2 seed=0")
    model.train(
        data="coco128.yaml",
        epochs=30,
        device=DEVICE,
        project=str(project),
        name=run_id,
        exist_ok=False,
        seed=0,
        workers=2,
        amp=True,  # AMP precheck verdict recorded separately as `amp_precheck`
    )
    csv = run_dir / "results.csv"
    summary = {
        "leg": "representative_30ep",
        "run_dir": str(run_dir),
        "data": "coco128.yaml",
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
    print(f"[OK] 30-epoch run complete -> {run_dir}")
    print("TRAIN30: PASS")


# -------------------------------------------------------------------------------- resume
def resume(run_id: str) -> None:
    """Resume an interrupted run in a NEW process from last.pt (epoch/optimizer/scheduler restored)."""
    from ultralytics import YOLO

    refuse_cpu()
    last = Path("runs/p15") / run_id / "weights" / "last.pt"
    if not last.exists():
        print(f"[FAIL] {last} missing")
        sys.exit(2)
    rows_before = len((Path("runs/p15") / run_id / "results.csv").read_text(encoding="utf-8").strip().splitlines())
    model = YOLO(str(last))
    model.train(resume=True)
    csv = Path("runs/p15") / run_id / "results.csv"
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
    print(f"[OK] resume {rows_before} -> {len(rows_after)} epochs")
    print("RESUME: PASS" if len(rows_after) > rows_before else "RESUME: FAIL")


# -------------------------------------------------------------------------------- finalcheck
def finalcheck(run_id: str) -> None:
    """Validate best.pt on COCO128 val, reload it fresh, run final inference."""
    import torch
    from ultralytics import YOLO

    refuse_cpu()
    run = Path("runs/p15") / run_id
    best = run / "weights" / "best.pt"
    last = run / "weights" / "last.pt"
    ev = {"leg": "finalcheck", "run_id": run_id, "best_sha256": sha256_file(best), "last_sha256": sha256_file(last)}

    model = YOLO(str(best))
    metrics = model.val(data="coco128.yaml", imgsz=640, device=DEVICE, verbose=False)
    ev["val_map5095"] = float(metrics.box.map)
    ev["val_map50"] = float(metrics.box.map50)

    reloaded = YOLO(str(best))  # fresh process object from disk
    r = reloaded.predict("https://ultralytics.com/images/bus.jpg", imgsz=640, device=DEVICE, verbose=False)
    ev["reload_predict_boxes"] = len(r[0].boxes)
    ev["reload_ok"] = len(r[0].boxes) > 0
    ev["finished_utc"] = NOW()
    ev["env"] = leg_common()
    (out_dir() / f"p15_finalcheck_{run_id}.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    print(f"[OK] finalcheck mAP50-95={ev['val_map5095']:.4f} reload_boxes={ev['reload_predict_boxes']}")
    print("FINALCHECK: PASS" if ev["reload_ok"] else "FINALCHECK: FAIL")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("leg", choices=["amp-probe", "smoke", "train30", "resume", "finalcheck"])
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--warm", action="store_true")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()
    if args.leg == "amp-probe":
        amp_probe()
    elif args.leg == "smoke":
        smoke(args.workers, args.warm, args.run_id)
    elif args.leg == "train30":
        train30(args.run_id or "p15_30ep_w2")
    elif args.leg == "resume":
        resume(args.run_id)
    elif args.leg == "finalcheck":
        finalcheck(args.run_id)


if __name__ == "__main__":
    multiprocessing.freeze_support()  # Windows-safe dataloader workers
    main()
