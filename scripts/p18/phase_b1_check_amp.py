"""P18 Phase B1: real-GPU AMP precheck on PR #27198 HEAD (gfx1100 RX 7900 XTX).

Verifies check_amp(model) on a real Radeon GPU with no CPU fallback:
imports the worktree source explicitly, runs the official YOLO26 probe.
"""
from __future__ import annotations

import json
import subprocess
import sys


def main() -> int:
    import ultralytics
    import torch
    from ultralytics import YOLO
    from ultralytics.utils.checks import check_amp

    provenance = {
        "ultralytics_file": ultralytics.__file__,
        "ultralytics_version": ultralytics.__version__,
        "torch": torch.__version__,
        "hip": torch.version.hip,
        "device": torch.cuda.get_device_name(0),
    }
    assert "pr27198" in ultralytics.__file__.replace("\\", "/").lower(), f"WRONG SOURCE: {ultralytics.__file__}"

    model = YOLO("yolo26n.yaml").model.to("cuda:0")
    result = check_amp(model)
    provenance["check_amp_result"] = bool(result)
    print("RESULT_JSON_BEGIN")
    print(json.dumps(provenance, indent=2))
    print("RESULT_JSON_END")
    return 0 if result else 3


if __name__ == "__main__":
    raise SystemExit(main())
