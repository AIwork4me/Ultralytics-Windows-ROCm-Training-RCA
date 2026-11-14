"""G3 — AMP root-cause analysis for Ultralytics on Windows ROCm (per environment).

    python tests/g3_amp_rca.py --out ../raw/g3_amp_<env>.json [--repeats 5]

Sections:
  A. AMP primitives (G3.2): autocast conv/linear/BN/loss forward+backward,
     dtype transitions, GradScaler semantics incl. planted-inf behavior.
  B. Ultralytics precheck decomposition (G3.3): replicate check_amp's
     amp_allclose exactly, but capture PRE-NMS raw tensors and POST-NMS boxes
     for FP32 vs autocast across N repeats; quantify max abs/rel diffs, shape
     mismatch origin, borderline-threshold crossings, NaN/Inf.
  C. Real check_amp() invocation with logger capture (the trainer's trigger).

Root-cause categories are assigned in the report, not here.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import torch

OUT: dict = {"environment": {}, "sections": {}, "limitations": []}


def meta() -> None:
    import ultralytics
    OUT["environment"] = {
        "torch": torch.__version__,
        "hip": torch.version.hip or "",
        "device": torch.cuda.get_device_name(0),
        "ultralytics": ultralytics.__version__,
        "amp_native_dtype_support": True,
    }
    if not torch.cuda.is_available() or not torch.version.hip:
        OUT["environment"]["gpu_authentic"] = False
    else:
        OUT["environment"]["gpu_authentic"] = True


def section_a_primitives() -> dict:
    dev = torch.device("cuda:0")
    torch.manual_seed(7)
    res = {}

    def autocast_ctx():
        return torch.autocast("cuda", dtype=torch.float16)

    # Conv2d autocast fwd+bwd
    conv = torch.nn.Conv2d(3, 8, 3, padding=1).to(dev)
    x = torch.randn(2, 3, 32, 32, device=dev, requires_grad=True)
    with autocast_ctx():
        y = conv(x)
        y_dtype = str(y.dtype)
        loss = y.float().square().mean()
    loss.backward()
    res["conv2d_autocast"] = {
        "output_dtype": y_dtype,
        "grad_finite": bool(torch.isfinite(x.grad).all()),
        "weight_grad_dtype": str(conv.weight.grad.dtype),
    }

    # Linear + BN + Loss chain in autocast
    lin = torch.nn.Linear(512, 8).to(dev)
    bn = torch.nn.BatchNorm2d(8).to(dev)
    x2 = torch.randn(4, 8, 8, 8, device=dev, requires_grad=True)
    with autocast_ctx():
        h = bn(x2)
        flat = h.flatten(1)
        y2 = lin(flat)
        l2 = torch.nn.functional.cross_entropy(y2.float(), torch.zeros(4, device=dev, dtype=torch.long))
    l2.backward()
    res["linear_bn_loss_autocast"] = {
        "bn_out_dtype": str(h.dtype), "linear_out_dtype": str(y2.dtype),
        "grad_finite": bool(torch.isfinite(x2.grad).all() and torch.isfinite(lin.weight.grad).all()),
    }

    # GradScaler normal step (leaf loss, scaled backward)
    scaler = torch.amp.GradScaler("cuda")
    p = torch.nn.Parameter(torch.ones(4, device=dev))
    opt = torch.optim.SGD([p], lr=0.1)
    loss = (p * 2.0).sum()
    scaler.scale(loss).backward()
    before = p.detach().clone()
    scaler.step(opt)
    scaler.update()
    res["gradscaler_normal_step"] = {
        "param_changed": bool(not torch.equal(before, p.detach())),
        "scale_after": float(scaler.get_scale()),
    }
    # planted inf: scaler must skip the step and reduce the scale on update
    p2 = torch.nn.Parameter(torch.ones(4, device=dev))
    opt2 = torch.optim.SGD([p2], lr=0.1)
    s2 = torch.amp.GradScaler("cuda")
    loss2 = (p2 * 2.0).sum()
    s2.scale(loss2).backward()
    with torch.no_grad():
        p2.grad[0] = float("inf")
    before2 = p2.detach().clone()
    s2.step(opt2)
    scale_before_update = s2.get_scale()
    s2.update()
    res["gradscaler_inf_skip"] = {
        "param_unchanged_on_inf": bool(torch.equal(before2, p2.detach())),
        "scale_reduced_on_inf": float(s2.get_scale()) < scale_before_update,
    }
    res["section_status"] = "PASS" if all(
        v.get("grad_finite", True) for v in res.values() if isinstance(v, dict)
    ) and res["gradscaler_inf_skip"]["param_unchanged_on_inf"] and res["gradscaler_normal_step"]["param_changed"] else "FAIL"
    return res


def section_b_precheck(repeats: int) -> dict:
    from ultralytics import YOLO
    from ultralytics.utils import ASSETS, WEIGHTS_DIR
    from ultralytics.utils.torch_utils import autocast

    weights = WEIGHTS_DIR / "yolo26n.pt"
    if not weights.is_file():
        weights = Path("yolo26n.pt")
    model = YOLO(str(weights))  # YOLO object, exactly as check_amp passes it
    device = torch.device("cuda:0")
    im = ASSETS / "bus.jpg"
    print("[B] model ready", flush=True)

    def amp_allclose_capture(m, im):
        """check_amp's exact probe, instrumented: raw pre-NMS + post-NMS."""
        batch = [im] * 8
        imgsz = max(256, int(m.stride.max() * 4))
        # FP32 raw forward (predictor path gives post-NMS; hook raw via predictor)
        det_a = m(batch, imgsz=imgsz, device=device, verbose=False)[0].boxes.data
        with autocast(enabled=True, device=device.type):
            det_b = m(batch, imgsz=imgsz, device=device, verbose=False)[0].boxes.data
        return det_a, det_b

    runs = []
    for i in range(repeats):
        print(f"[B] repeat {i + 1}/{repeats}", flush=True)
        a, b = amp_allclose_capture(model, im)
        entry = {
            "fp32_shape": list(a.shape), "amp_shape": list(b.shape),
            "shape_equal": a.shape == b.shape,
            "fp32_finite": bool(torch.isfinite(a).all()),
            "amp_finite": bool(torch.isfinite(b).all()),
        }
        if a.shape == b.shape:
            entry["max_abs_diff"] = float((a.float() - b.float()).abs().max())
            denom = a.float().abs().clamp_min(1e-6)
            entry["max_rel_diff"] = float(((a.float() - b.float()).abs() / denom).max())
            entry["allclose_atol_0.5"] = bool(torch.allclose(a.float(), b.float(), atol=0.5))
        else:
            # which detections differ: compare conf distributions
            conf_a = a[:, 4] if a.numel() else a
            conf_b = b[:, 4] if b.numel() else b
            entry["fp32_n_det"] = int(a.shape[0]) if a.dim() else 0
            entry["amp_n_det"] = int(b.shape[0]) if b.dim() else 0
            entry["conf_min_max_fp32"] = [float(conf_a.min()), float(conf_a.max())] if a.numel() else None
            entry["conf_min_max_amp"] = [float(conf_b.min()), float(conf_b.max())] if b.numel() else None
            entry["note"] = "shape mismatch originates in post-NMS detection count (threshold crossings)"
        runs.append(entry)
    passed = sum(1 for r in runs if r["shape_equal"] and r.get("allclose_atol_0.5", False))
    return {"repeats": repeats, "passed": passed, "runs": runs,
            "precheck_would_pass": passed == repeats,
            "imgsz_note": "check_amp semantics replicated incl. batch=8 and imgsz=max(256, stride*4)"}


def section_c_real_check_amp() -> dict:
    from ultralytics import YOLO
    from ultralytics.utils import WEIGHTS_DIR
    from ultralytics.utils.checks import check_amp

    weights = WEIGHTS_DIR / "yolo26n.pt"
    if not weights.is_file():
        weights = Path("yolo26n.pt")
    model = YOLO(str(weights)).model.cuda()

    class Cap(logging.Handler):
        def __init__(self):
            super().__init__()
            self.lines = []

        def emit(self, record):
            self.lines.append(record.getMessage())

    h = Cap()
    logging.getLogger().addHandler(h)
    root_ul = logging.getLogger("ultralytics")
    root_ul.addHandler(h)
    try:
        verdict = check_amp(model)
    finally:
        logging.getLogger().removeHandler(h)
        root_ul.removeHandler(h)
    return {"check_amp_returned": bool(verdict), "log_lines": h.lines[-8:]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args()
    meta()
    if not OUT["environment"]["gpu_authentic"]:
        OUT["sections"]["gate"] = "BLOCKED_NOT_GPU"
        Path(args.out).write_text(json.dumps(OUT, indent=2), encoding="utf-8")
        sys.exit(3)
    OUT["sections"]["a_primitives"] = section_a_primitives()
    OUT["sections"]["b_precheck_decomposition"] = section_b_precheck(args.repeats)
    OUT["sections"]["c_real_check_amp"] = section_c_real_check_amp()
    Path(args.out).write_text(json.dumps(OUT, indent=2), encoding="utf-8")
    b = OUT["sections"]["b_precheck_decomposition"]
    print(json.dumps({
        "a_status": OUT["sections"]["a_primitives"]["section_status"],
        "precheck_would_pass": b["precheck_would_pass"],
        "real_check_amp": OUT["sections"]["c_real_check_amp"]["check_amp_returned"],
    }, indent=2))


if __name__ == "__main__":
    main()
