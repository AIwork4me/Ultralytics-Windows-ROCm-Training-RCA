"""P18 Phase B2 (v2): exception-handling boundary of PR #27198 on real gfx1100.

check_amp(model) only uses the passed model's DEVICE; the probe builds a fresh
DetectionModel("yolo26n.yaml"). We pass a tiny nn.Linear on cuda:0 so the probe
path actually executes, and inject faults by swapping
ultralytics.nn.tasks.DetectionModel (imported at call time inside check_amp).

Cases:
  construction-phase control-flow injection (probe model build):
    RuntimeError / OutOfMemoryError / AcceleratorError -> caught, False, LOGGER.error
    ValueError / TypeError -> propagate
    KeyboardInterrupt / SystemExit -> propagate
  forward-phase REAL-GPU injection on the real DetectionModel (cuda kernels run
  until the hook raises): RuntimeError -> caught, False
  healthy control: unpatched probe on cuda -> True
"""
from __future__ import annotations

import json
import logging

RESULTS: dict = {"cases": []}


class CapturingHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.records: list[str] = []

    def emit(self, record):
        self.records.append(record.getMessage())


def run_case(name: str, exc_factory, expect: str, inject: str = "construction"):
    import torch
    import ultralytics.nn.tasks as nn_tasks
    import ultralytics.utils.checks as checks

    cap = CapturingHandler()
    checks.LOGGER.addHandler(cap)
    case = {"name": name, "expect": expect, "inject": inject}
    original_dm = nn_tasks.DetectionModel
    device = torch.device("cuda:0")
    try:
        if inject == "construction":

            class BoomDM(original_dm):
                def __init__(self, *a, **k):
                    raise exc_factory()

            nn_tasks.DetectionModel = BoomDM
        elif inject == "forward":

            class HookDM(original_dm):
                def __init__(self, *a, **k):
                    super().__init__(*a, **k)
                    for layer in self.modules():
                        if isinstance(layer, torch.nn.Conv2d):
                            layer.register_forward_hook(HookDM._raise_hook)
                            break

                @staticmethod
                def _raise_hook(module, args, output):
                    raise exc_factory()

            nn_tasks.DetectionModel = HookDM

        probe_device_model = torch.nn.Linear(4, 4).to(device)  # only its device is used
        try:
            ret = checks.check_amp(probe_device_model)
            case["returned"] = bool(ret)
            case["outcome"] = "caught" if ret is False else "returned_true"
        except BaseException as e:  # noqa: BLE001 - recording propagation is the test
            case["propagated"] = type(e).__name__
            case["outcome"] = "propagate"
        case["error_log_excerpt"] = cap.records[-1][:180] if cap.records else None
    finally:
        nn_tasks.DetectionModel = original_dm
        checks.LOGGER.removeHandler(cap)

    ok = case["outcome"] == expect
    case["pass"] = ok
    RESULTS["cases"].append(case)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: outcome={case['outcome']}" + (f" propagated={case.get('propagated')}" if case.get('propagated') else ""))
    if case.get("error_log_excerpt"):
        print(f"    log: {case['error_log_excerpt']}")
    return ok


def main() -> int:
    import torch
    import ultralytics
    import ultralytics.utils.checks as checks

    RESULTS["provenance"] = {
        "ultralytics_file": ultralytics.__file__,
        "torch": torch.__version__,
        "hip": torch.version.hip,
        "device": torch.cuda.get_device_name(0),
    }
    assert "pr27198" in ultralytics.__file__.replace("\\", "/").lower()

    facts = {}
    oom = torch.cuda.OutOfMemoryError
    facts["OutOfMemoryError_mro"] = [c.__name__ for c in oom.__mro__[:4]]
    facts["OOM_is_RuntimeError"] = issubclass(oom, RuntimeError)
    acc = getattr(torch, "AcceleratorError", None)
    facts["AcceleratorError"] = "present" if acc else "absent"
    if acc:
        facts["AcceleratorError_mro"] = [c.__name__ for c in acc.__mro__[:4]]
        facts["AcceleratorError_is_RuntimeError"] = issubclass(acc, RuntimeError)
    RESULTS["inheritance_facts"] = facts
    print(json.dumps(facts, indent=1))

    ok = True
    ok &= run_case("RuntimeError@construction -> caught/False", lambda: RuntimeError("simulated backend failure"), "caught")
    if facts["OOM_is_RuntimeError"]:
        ok &= run_case("OutOfMemoryError@construction -> caught/False", lambda: torch.cuda.OutOfMemoryError("CUDA out of memory. (simulated)"), "caught")
    if acc and facts.get("AcceleratorError_is_RuntimeError"):
        ok &= run_case("AcceleratorError@construction -> caught/False", lambda: acc("simulated accelerator error"), "caught")
    ok &= run_case("ValueError@construction -> propagate", lambda: ValueError("bad value"), "propagate")
    ok &= run_case("TypeError@construction -> propagate", lambda: TypeError("bad type"), "propagate")
    ok &= run_case("KeyboardInterrupt -> propagate", lambda: KeyboardInterrupt(), "propagate")
    ok &= run_case("SystemExit -> propagate", lambda: SystemExit(2), "propagate")
    ok &= run_case(
        "RuntimeError@forward REAL_GPU -> caught/False",
        lambda: RuntimeError("hipErrorInvalidKernelFile (simulated mid-forward)"),
        "caught",
        inject="forward",
    )
    # healthy control: unpatched probe on the real GPU
    healthy = checks.check_amp(torch.nn.Linear(4, 4).to("cuda:0"))
    RESULTS["healthy_control_check_amp"] = bool(healthy)
    print(f"[{'PASS' if healthy else 'FAIL'}] healthy control check_amp -> {healthy}")
    ok &= bool(healthy)

    RESULTS["all_pass"] = bool(ok)
    print("RESULT_JSON_BEGIN")
    print(json.dumps(RESULTS, indent=2))
    print("RESULT_JSON_END")
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
