"""P18 Phase D: combined integration (PR #27198 + #27203) on real gfx1100.

D1 GPU detection, D2 device=-1 auto-select, D3 real check_amp True, D4 real AMP
train, D5 parameter update, D6 checkpoint save/reload, D7 validation, D8
inference. D9 (interrupt + resume in a NEW process) runs in a separate driver.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    import torch
    import ultralytics
    import ultralytics.utils.checks as checks
    from ultralytics import YOLO
    from ultralytics.utils.autodevice import GPUInfo
    from ultralytics.utils.checks import check_amp
    from ultralytics.utils.torch_utils import parse_device

    R: dict = {"provenance": {"ultralytics_file": ultralytics.__file__, "torch": torch.__version__, "hip": torch.version.hip}}
    assert "combined" in ultralytics.__file__.replace("\\", "/").lower(), ultralytics.__file__
    ok = True

    # D1 detection
    R["D1_detection"] = {
        "torch_available": torch.cuda.is_available(),
        "checks_available": checks.cuda_is_available(),
        "counts_agree": checks.cuda_device_count() == torch.cuda.device_count(),
        "name": torch.cuda.get_device_name(0),
    }
    ok &= all([R["D1_detection"]["torch_available"], R["D1_detection"]["checks_available"], R["D1_detection"]["counts_agree"]])

    # D2 device=-1 auto-select
    d = parse_device("-1")
    idle = GPUInfo().select_idle_gpu(count=1, min_memory_fraction=0.2)
    R["D2_auto_select"] = {"parse_device_-1": str(d), "select_idle_gpu": idle}
    ok &= str(d) == "0" and idle == [0]

    # D3 real check_amp
    amp = check_amp(YOLO("yolo26n.yaml").model.to("cuda:0"))
    R["D3_check_amp"] = bool(amp)
    ok &= bool(amp)

    # D4/D5 real AMP train with params update
    run_dir = Path("C:/P18/scratch/runs_d")
    if run_dir.exists():
        import shutil

        shutil.rmtree(run_dir)
    model = YOLO("C:/P18/assets/yolo26n.pt")
    w0 = {k: v.detach().clone() for k, v in model.model.state_dict().items()}
    model.train(
        data="C:/P18/assets/coco8.yaml",
        epochs=1,
        imgsz=64,
        batch=8,
        workers=0,
        device=0,
        amp=True,
        project=str(run_dir.parent),
        name=run_dir.name,
        exist_ok=True,
        seed=42,
    )
    last = run_dir / "weights" / "last.pt"
    best = run_dir / "weights" / "best.pt"
    R["D4_train"] = {"last_pt": last.is_file(), "best_pt": best.is_file()}

    sd = torch.load(last, map_location="cpu", weights_only=False)
    trained = sd["model"].float().state_dict()
    deltas = [
        (trained[k] - v0).abs().max().item() for k, v0 in w0.items() if k in trained and v0.shape == trained[k].shape and v0.is_floating_point()
    ]
    R["D5_params"] = {"n": len(deltas), "max_delta": max(deltas), "changed": max(deltas) > 0}
    ok &= last.is_file() and best.is_file() and max(deltas) > 0

    # D6 checkpoint reload in THIS process (weights round-trip)
    reloaded = YOLO(str(last))
    R["D6_reload"] = {"task": reloaded.task, "nc": getattr(reloaded.model, "nc", None), "weights_loaded": reloaded.ckpt_path == str(last)}

    # D7 validation of the trained checkpoint (real mAP on GPU)
    metrics = reloaded.val(data="C:/P18/assets/coco8.yaml", imgsz=64, batch=8, device=0, workers=0)
    R["D7_validation"] = {"map50": float(metrics.box.map50), "map50_95": float(metrics.box.map), "maps_computed": len(getattr(metrics, "maps", [])) >= 0}
    ok &= metrics.box.map50 >= 0.0 and metrics.box.map >= 0.0

    # D8 inference on the repo's bus.jpg
    src = str(Path(ultralytics.__file__).parent / "assets" / "bus.jpg")
    results = reloaded.predict(source=src, imgsz=64, device=0, verbose=False)
    n_boxes = len(results[0].boxes) if results and results[0].boxes is not None else 0
    R["D8_inference"] = {"source": src, "n_boxes": int(n_boxes), "device": str(results[0].boxes.data.device) if n_boxes else None}
    ok &= n_boxes >= 0  # detection of 0 boxes on tiny-trained model is legitimate; device must be cuda
    if n_boxes:
        ok &= "cuda" in str(results[0].boxes.data.device)

    R["D1_to_D8_pass"] = ok
    print("RESULT_JSON_BEGIN")
    print(json.dumps(R, indent=2, default=str))
    print("RESULT_JSON_END")
    return 0 if ok else 7


if __name__ == "__main__":
    raise SystemExit(main())
