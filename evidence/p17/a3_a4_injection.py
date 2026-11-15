# CONTROL_FLOW_INJECTION verification for PR #27198 check_amp exception boundary.
# Faults are injected at the probe boundary via monkeypatch; no GPU runtime is damaged.
import logging, json, datetime
from types import SimpleNamespace
import torch
from ultralytics.nn.tasks import DetectionModel
from ultralytics.utils import LOGGER
from ultralytics.utils.checks import check_amp


class FakeAcceleratorModel:
    """Stand-in exposing an accelerator device so check_amp takes its probe path without real hardware."""
    def parameters(self):
        p = SimpleNamespace()
        p.device = torch.device("cuda")  # HIP reports device.type == "cuda"
        return iter([p])


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []
    def emit(self, record):
        self.records.append(record.getMessage())


def run_with_exc(exc):
    """Inject exc at DetectionModel.__init__ (probe boundary) and return (result_or_None, raised_or_None, logs)."""
    h = Capture(); LOGGER.addHandler(h)
    orig = DetectionModel.__init__
    def broken(self, *a, **k):
        raise exc
    DetectionModel.__init__ = broken
    raised, result = None, None
    try:
        result = check_amp(FakeAcceleratorModel())
    except BaseException as e:
        raised = e
    finally:
        DetectionModel.__init__ = orig
        LOGGER.removeHandler(h)
    return result, raised, h.records


out = {"injection_type": "CONTROL_FLOW_INJECTION", "results": {}}

# A3: RuntimeError-family must be caught -> False with truthful logging
for name, exc in [
    ("RuntimeError", RuntimeError("simulated backend failure while building the probe model")),
    ("torch.cuda.OutOfMemoryError", torch.cuda.OutOfMemoryError("simulated OOM")),
    ("torch.AcceleratorError", torch.AcceleratorError("simulated accelerator fault")),
]:
    result, raised, logs = run_with_exc(exc)
    err_lines = [m for m in logs if "checks failed with an exception" in m]
    out["results"][name] = {
        "caught": raised is None,
        "returned": result,
        "is_false": result is False,
        "logged_error": bool(err_lines),
        "log_includes_exception_type": bool(err_lines and type(exc).__name__ in err_lines[0]),
        "log_includes_exception_message": bool(err_lines and str(exc) in err_lines[0]),
        "log_includes_not_amp_specific_disclaimer": bool(err_lines and "not necessarily AMP-specific" in err_lines[0]),
        "log_includes_no_fp32_health_guarantee": bool(err_lines and "if FP32 training also fails" in err_lines[0]),
        "log_claims_numerical_anomaly": any("Anomalies were detected with AMP" in m for m in logs),
    }

# A4: non-RuntimeError must propagate
for name, exc in [
    ("ValueError", ValueError("simulated bad value")),
    ("TypeError", TypeError("simulated bad type")),
    ("KeyboardInterrupt", KeyboardInterrupt()),
    ("SystemExit", SystemExit(1)),
]:
    result, raised, logs = run_with_exc(exc)
    out["results"][name] = {
        "propagated": isinstance(raised, type(exc)) and type(raised) is type(exc),
        "raised_type": type(raised).__name__ if raised is not None else None,
        "check_amp_result_when_raised": result,
    }

out["timestamp"] = datetime.datetime.now().astimezone().isoformat()
json.dump(out, open("a3_a4_result.json", "w"), indent=2)
print(json.dumps(out, indent=2))
