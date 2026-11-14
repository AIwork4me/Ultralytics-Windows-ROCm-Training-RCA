"""G3.6 — paired FP32/AMP box capture + matcher validation on real GPU.

    python tests/g3_amp_paired_boxes.py --out ../raw/g3_paired_<env>.json \
        --boxes ../raw/paired_boxes_<env>.pt [--repeats 5]

Executes the exact check_amp probe (8x bus.jpg, imgsz = stride*4) and:
  1. ARCHIVES the paired FP32/AMP post-NMS box tensors per repeat (.pt) —
     the audit C-o5 requirement that the PR-C matcher be validated on CPU
     against archived REAL tensors before any upstream submission
  2. verdicts per repeat: old amp_allclose (allclose atol=0.5) AND the new
     amp_match_verdict — on stacks where the old check flips on cache state,
     the new matcher must pass benign quantization
  3. planted-corruption negative controls ON THE REAL TENSORS: +30 px shift,
     class flip, NaN injection, 10% confidence collapse — every corruption
     MUST be caught (verdict False), proving the fix does not hide real
     anomalies (mission §4.2)
  4. full provenance: environment, in-process loaded MIOpen DLL SHA256,
     weights SHA256, cache-home identity (mission §3.4)
"""
import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amp_iou_matcher import amp_match_verdict
from harness_common import dll_provenance, env_meta, new_run_id, save_immutable, sha256_file, utcnow


def capture(yolo_obj, nn_module, device):
    """Mirror of check_amp's amp_allclose probe: `yolo_obj` is the YOLO
    object passed as `m` upstream; `nn_module` supplies stride (the outer
    `model` closure variable in upstream code)."""
    from ultralytics.utils import ASSETS
    from ultralytics.utils.torch_utils import autocast
    im = ASSETS / "bus.jpg"
    batch = [im] * 8
    imgsz = max(256, int(nn_module.stride.max() * 4))
    a = yolo_obj(batch, imgsz=imgsz, device=device, verbose=False)[0].boxes.data
    with autocast(enabled=True, device=device.type):
        b = yolo_obj(batch, imgsz=imgsz, device=device, verbose=False)[0].boxes.data
    return a.detach().float().cpu(), b.detach().float().cpu(), imgsz


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--boxes", required=True)
    ap.add_argument("--weights", default="yolo26n.pt")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--environment-id", default="unknown")
    ap.add_argument("--cache-label", default="default",
                    help="MIOpen cache-home label for the archive metadata")
    ap.add_argument("--warm-training", action="store_true",
                    help="reproduce the historical 'training context' cache state: run a "
                         "1-epoch AMP training BEFORE the captures in the same process "
                         "(the 0.7606px FAIL state of g3_amp_envB_defaulthome.json)")
    args = ap.parse_args()

    OUT = {"environment": {}, "repeats": [], "negative_controls": [], "summary": {}}
    OUT["run_id"] = args.run_id or new_run_id("g3paired")
    OUT["environment_id"] = args.environment_id
    OUT["cache_label"] = args.cache_label
    if not (torch.cuda.is_available() and torch.version.hip):
        OUT["environment"] = {"gpu_authentic": False}
        save_immutable(Path(args.out), OUT)
        sys.exit(3)
    OUT["environment"] = env_meta()
    OUT["started_utc"] = utcnow()

    weights = Path(args.weights)
    OUT["weights_sha256"] = sha256_file(weights) if weights.is_file() else None

    from ultralytics import YOLO
    yolo_obj = YOLO(str(weights))            # exactly what check_amp passes as m
    nn_module = yolo_obj.model.cuda().eval()  # the outer `model` closure (stride/device)
    device = torch.device("cuda:0")

    warm_meta = None
    if args.warm_training:
        # build the TRAINING-CONTEXT cache first (conv shapes chosen by actual
        # training) — reproduces the kernel-selection state that produced the
        # historical 0.7606px crossing on ENV B default home
        tr = YOLO(str(weights))
        tr.train(data="coco8.yaml", epochs=1, device=0, workers=0, amp=True,
                 name=f"warmctx_{OUT['run_id']}", exist_ok=True, plots=False, seed=42)
        warm_meta = {"warm_training_amp_effective": bool(getattr(tr.trainer, "amp", None)),
                     "warm_save_dir": str(tr.trainer.save_dir)}
        OUT["warm_training"] = warm_meta
        print(f"[warm] training-context cache built amp_effective={warm_meta['warm_training_amp_effective']}",
              flush=True)

    captures = []
    for i in range(args.repeats):
        a, b, imgsz = capture(yolo_obj, nn_module, device)
        old = {"shape_equal": a.shape == b.shape,
               "max_abs_diff": float((a - b).abs().max()) if a.shape == b.shape and a.numel() else None,
               "allclose_atol_0.5": (bool(torch.allclose(a, b, atol=0.5))
                                     if a.shape == b.shape and a.numel() else False)}
        new = amp_match_verdict(a, b, imgsz=float(imgsz))
        OUT["repeats"].append({
            "repeat": i, "imgsz": int(imgsz),
            "fp32_shape": list(a.shape), "amp_shape": list(b.shape),
            "old_allclose": old, "new_matcher": {k: v for k, v in new.items() if k != "pairs"},
        })
        captures.append({"label": f"{args.environment_id}_{args.cache_label}_r{i}",
                         "fp32_boxes": a, "amp_boxes": b, "imgsz": int(imgsz),
                         "old_allclose": old["allclose_atol_0.5"],
                         "expected_verdict": True})
        print(f"[repeat {i}] old={old['allclose_atol_0.5']} "
              f"maxdiff={old['max_abs_diff']} new={new['verdict']} "
              f"maxdrift={new.get('max_abs_coord_drift_px')}", flush=True)

    # ---- negative controls on REAL archived tensors (must all be caught) ----
    a0, b0, imgsz = captures[0]["fp32_boxes"], captures[0]["amp_boxes"], captures[0]["imgsz"]
    if a0.numel():
        corrupt = []
        b_shift = b0.clone()
        b_shift[0, :4] += 30.0
        corrupt.append(("shift_30px", amp_match_verdict(a0, b_shift, float(imgsz))["verdict"]))
        b_cls = b0.clone()
        b_cls[0, 5] = (b_cls[0, 5] + 1.0) % 80.0
        corrupt.append(("class_flip", amp_match_verdict(a0, b_cls, float(imgsz))["verdict"]))
        b_nan = b0.clone()
        b_nan[0, 4] = float("nan")
        corrupt.append(("nan_inject", amp_match_verdict(a0, b_nan, float(imgsz))["verdict"]))
        b_conf = b0.clone()
        b_conf[:, 4] *= 0.9
        corrupt.append(("conf_collapse_10pct", amp_match_verdict(a0, b_conf, float(imgsz))["verdict"]))
        b_drop = b0[:-1].clone() if b0.shape[0] > 1 else b0
        corrupt.append(("drop_detection", amp_match_verdict(a0, b_drop, float(imgsz))["verdict"]))
        OUT["negative_controls"] = [
            {"corruption": name, "caught": not passed, "matcher_passed": passed}
            for name, passed in corrupt]
        all_caught = all(not passed for _name, passed in corrupt)
        OUT["summary"]["negative_controls_all_caught"] = all_caught

    n_new_pass = sum(1 for r in OUT["repeats"] if r["new_matcher"]["verdict"])
    n_old_pass = sum(1 for r in OUT["repeats"] if r["old_allclose"]["allclose_atol_0.5"])
    OUT["summary"].update({
        "repeats": args.repeats,
        "old_allclose_pass": f"{n_old_pass}/{args.repeats}",
        "new_matcher_pass": f"{n_new_pass}/{args.repeats}",
        "completed_utc": utcnow(),
    })
    OUT["dll_provenance"] = dll_provenance()

    # archive tensors AFTER success (immutable)
    torch.save({"captures": captures,
                "meta": {"environment_id": args.environment_id, "cache_label": args.cache_label,
                         "run_id": OUT["run_id"], "environment": OUT["environment"],
                         "weights_sha256": OUT["weights_sha256"],
                         "created_utc": utcnow()}}, args.boxes)
    save_immutable(Path(args.out), OUT)
    print(f"SUMMARY old={n_old_pass}/{args.repeats} new={n_new_pass}/{args.repeats} "
          f"negctrl_all_caught={OUT['summary'].get('negative_controls_all_caught')}", flush=True)
    ok = (OUT["summary"]["negative_controls_all_caught"]
          and n_new_pass == args.repeats)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
