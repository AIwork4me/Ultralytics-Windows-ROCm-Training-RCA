# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""CPU-only harness contract tests (mission §11) — no GPU, no torch import.

Validates: wheel-filename parsing, fail-closed runtime classification,
no-STL failure-signature mapping, strict evidence schema (no stringified
bools), train-log parser, false-PASS rejection, and the rule that synthetic
fixtures can NEVER produce PHYSICAL_GPU_PASS.

    python -m pytest windows-golden-path/tests/ -q
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


gp_lib = load_module("gp_lib")


# --- wheel filename parsing -------------------------------------------------
class TestParseWheelFilename:
    def test_amd_torch_local_version(self):
        p = gp_lib.parse_wheel_filename(
            "torch-2.12.0+rocm7.14.1-cp313-cp313-win_amd64.whl")
        assert p["package"] == "torch"
        assert p["version"] == "2.12.0+rocm7.14.1"
        assert p["win_amd64"] is True
        assert p["python_tag"] == "cp313"

    def test_rocm_sdk_libraries_py3_none(self):
        p = gp_lib.parse_wheel_filename(
            "rocm_sdk_libraries-10.2.0rc2-py3-none-win_amd64.whl")
        assert p["package"] == "rocm-sdk-libraries"
        assert p["version"] == "10.2.0rc2"
        assert p["win_amd64"] is True

    def test_linux_wheel_not_windows(self):
        p = gp_lib.parse_wheel_filename("torch-2.13.0+rocm10.1.0-cp313-cp313-linux_x86_64.whl")
        assert p["win_amd64"] is False

    def test_non_wheel_rejected(self):
        assert gp_lib.parse_wheel_filename("not-a-wheel.txt") == {}


# --- fail-closed runtime classification --------------------------------------
class TestClassifyRuntime:
    def test_any_shim_forces_engineering_reference(self):
        w = {"any_workaround_present": True}
        assert gp_lib.classify_runtime(w, "stable", None) == "ENGINEERING_REFERENCE"

    def test_marker_positive_stable(self):
        w = {"any_workaround_present": False}
        m = {"loaded": True, "pr13437_marker_miopen_initializer_list": 2}
        assert gp_lib.classify_runtime(w, "stable", m) == "OFFICIAL_STABLE"

    def test_marker_positive_rc_channel_stays_candidate(self):
        w = {"any_workaround_present": False}
        m = {"loaded": True, "pr13437_marker_miopen_initializer_list": 2}
        assert gp_lib.classify_runtime(w, "rc", m) == "OFFICIAL_CANDIDATE"

    def test_marker_zero_is_pre_fix(self):
        w = {"any_workaround_present": False}
        m = {"loaded": True, "pr13437_marker_miopen_initializer_list": 0}
        assert gp_lib.classify_runtime(w, "stable", m) == "OFFICIAL_PRE_FIX"


# --- workaround detection -----------------------------------------------------
class TestDetectWorkarounds:
    def test_detects_hiprtc_append(self):
        w = gp_lib.detect_workarounds({"HIPRTC_COMPILE_OPTIONS_APPEND": "-IC:\\shim"})
        assert w["hiprtc_include_injection"] is True
        assert w["any_workaround_present"] is True

    def test_miopen_log_level_alone_is_not_a_workaround(self):
        w = gp_lib.detect_workarounds({"MIOPEN_LOG_LEVEL": "4"})
        assert w["any_workaround_present"] is False

    def test_miopen_override_flagged(self):
        w = gp_lib.detect_workarounds({"MIOPEN_FIND_MODE": "fast"})
        assert w["any_workaround_present"] is True


# --- no-STL failure signature classification ----------------------------------
class TestClassifyNostlFailure:
    def test_type_traits_signature(self):
        s = ("HIPRTC_ERROR_COMPILATION (6) ... miopen_type_traits.hpp:151:10: "
             "fatal error: 'type_traits' file not found ... miopenStatusUnknownError")
        assert gp_lib.classify_nostl_failure(s) == "MIOPEN_HIPRTC_COMPILATION"

    def test_invalid_kernel_file(self):
        assert gp_lib.classify_nostl_failure("hipErrorInvalidKernelFile") == "HIP_KERNEL_IMAGE_FAILURE"

    def test_nms_device_function(self):
        assert gp_lib.classify_nostl_failure("hipErrorInvalidDeviceFunction") == \
            "TORCHVISION_DEVICE_WHEEL_MISSING"

    def test_unknown_stays_inconclusive(self):
        assert gp_lib.classify_nostl_failure("something else") == "INCONCLUSIVE"


# --- strict evidence schema ---------------------------------------------------
class TestEvidenceSchema:
    def test_stringified_bool_rejected(self):
        with pytest.raises(ValueError, match="stringified boolean"):
            gp_lib.strict_json_types({"amp": "True"})

    def test_missing_keys_rejected(self):
        with pytest.raises(ValueError, match="missing required keys"):
            gp_lib.write_evidence({"run_id": "x"}, HERE / "_never.json")

    def test_valid_record_writes(self, tmp_path):
        rec = {k: None for k in gp_lib.EVIDENCE_REQUIRED_KEYS}
        rec.update({"exit_code": 0, "pass_fail_skip": "PASS", "amp": True})
        out = tmp_path / "ok.json"
        gp_lib.write_evidence(rec, out)
        assert json.loads(out.read_text(encoding="utf-8"))["amp"] is True

    def test_contract_keys_match_library(self):
        contract = json.loads((HERE.parent / "acceptance-contract.json").read_text(encoding="utf-8"))
        assert contract["evidence_schema_required_keys"] == gp_lib.EVIDENCE_REQUIRED_KEYS


# --- train log parser -----------------------------------------------------------
class TestParseTrainLog:
    GOOD = """
WARNING NVML stats unavailable, selecting the first CUDA devices without idle checks.
CUDA:0 (AMD Radeon RX 7900 XTX, 24560MiB)
AMP: checks passed ✅
                 Class     Images  Instances      Box(P          R      mAP50
                   all          4          9      0.544      0.965      0.943      0.687
      1/1      1.99G      0.856      1.586
Results saved to runs\\detect\\train2
"""

    def test_good_log_facts(self):
        f = gp_lib and load_module("generate_report").parse_train_log(self.GOOD)
        assert f["gpu_selected"]["device"] == "CUDA:0"
        assert f["gpu_selected"]["name"] == "AMD Radeon RX 7900 XTX"
        assert f["amp_check"] == "PASSED"
        assert f["validation_completed"] is True
        assert f["cpu_fallback"] is False

    def test_cpu_fallback_detected(self):
        f = load_module("generate_report").parse_train_log("using CPU device=cpu")
        assert f["cpu_fallback"] is True


# --- reproducer shape contract ---------------------------------------------------
def test_nostl_reproducer_uses_historical_shape():
    src = (SCRIPTS / "verify_miopen_nostl.py").read_text(encoding="utf-8")
    assert "BatchNorm2d(100)" in src
    assert "20, 100, 35, 45" in src
    assert "VCToolsInstallDir" in src and 'INCLUDE' in src


def test_stability_anomaly_families_are_separate():
    src = (SCRIPTS / "run_stability.py").read_text(encoding="utf-8")
    for fam in ("HIP_KERNEL_IMAGE_FAILURE", "MIOPEN_SOLVER_ANOMALY", "MIOPEN_MISSING_CK_SYMBOL"):
        assert fam in src


# --- false-PASS rejection in report generation -----------------------------------
class TestReportFalsePassRejection:
    def make_evidence(self, tmp_path, name, **over):
        rec = {k: None for k in gp_lib.EVIDENCE_REQUIRED_KEYS}
        rec.update({"exit_code": 0, "pass_fail_skip": "PASS",
                    "gpu_name": "AMD Radeon RX 7900 XTX", "hip": "7.14.60850"})
        rec.update(over)
        (tmp_path / name).write_text(json.dumps(rec), encoding="utf-8")

    def test_pass_with_nonzero_exit_rejected(self, tmp_path, capsys):
        self.make_evidence(tmp_path, "bad.json", exit_code=1)
        gen = load_module("generate_report")
        rc = gen.cmd_full(type("A", (), {
            "run_id": "T", "evidence_dir": str(tmp_path), "report_dir": str(tmp_path / "r")})())
        assert rc == 1
        report = json.loads((tmp_path / "r" / "report.json").read_text(encoding="utf-8"))
        assert any("claims PASS but exit_code=1" in v for v in report["violations"])

    def test_synthetic_fixture_never_physical_pass(self, tmp_path):
        self.make_evidence(tmp_path, "fix.json", harness_fixture=True)
        gen = load_module("generate_report")
        gen.cmd_full(type("A", (), {
            "run_id": "T", "evidence_dir": str(tmp_path), "report_dir": str(tmp_path / "r")})())
        report = json.loads((tmp_path / "r" / "report.json").read_text(encoding="utf-8"))
        assert report["any_physical_gpu_pass"] is False
        assert report["summary_class"] == "NO_PHYSICAL_PASS"

    def test_pass_without_gpu_provenance_rejected(self, tmp_path):
        self.make_evidence(tmp_path, "nogpuprov.json", gpu_name=None)
        gen = load_module("generate_report")
        rc = gen.cmd_full(type("A", (), {
            "run_id": "T", "evidence_dir": str(tmp_path), "report_dir": str(tmp_path / "r")})())
        assert rc == 1


# --- channel contract ------------------------------------------------------------
def test_official_channel_allowlist_is_exact():
    assert set(gp_lib.OFFICIAL_CHANNELS) == {"multi-arch", "stable", "rc", "nightly", "dev"}
    for url in gp_lib.OFFICIAL_CHANNELS.values():
        assert url.startswith("https://") and "repo.amd.com" in url


def test_discovery_never_synthesizes_urls_static():
    src = (SCRIPTS / "discover_official_wheels.py").read_text(encoding="utf-8")
    # every wheel_url must be built from an observed page url + observed filename
    assert '"wheel_url": url + fn' in src
