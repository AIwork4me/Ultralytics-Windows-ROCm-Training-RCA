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

    def test_gpu_name_with_parens_not_truncated(self):
        # R22A gfx1151 regression: "[^,)]+" truncated "AMD Radeon(TM) 8060S
        # Graphics" to "AMD Radeon(TM" (first ')' inside the name ended the
        # match), corrupting gpu_name/gfx_target in the G3 evidence record
        f = load_module("generate_report").parse_train_log(
            "CUDA:0 (AMD Radeon(TM) 8060S Graphics, 101293MiB)")
        assert f["gpu_selected"]["device"] == "CUDA:0"
        assert f["gpu_selected"]["name"] == "AMD Radeon(TM) 8060S Graphics"


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


# =============================================================================
# R21.1 TASK F — adversarial acceptance-contract tests (CPU-only).
# Every test proves a specific fail-closed property of the release gates.
# =============================================================================
DEV_TORCH = ("2.15.0+gitf6cd88cb.devrocm10.3.0.dev0."
             "ff5769655eeb1b91a46bce9edc16d87ca0efe7b6")  # exact observed DEV wheel
DEV_TORCH_URL = ("https://dev.repo.amd.com/rocm/pytorch/whl-next/torch/"
                 "torch-2.15.0%2Bgitf6cd88cb.devrocm10.3.0.dev0.ff5769655-cp312-"
                 "cp312-win_amd64.whl")

SUITES = {
    "gpA_provenance.json": {"provenance_status": "PROVENANCE_COMPLETE",
                            "loaded_miopen_dll": {"loaded": True, "sha256": "ab" * 32},
                            "wheel_lock": [{"name": "torch", "sha256": "cd" * 32}]},
    "gpB_torch_gates.json": {"gates": {"device_identity": {"status": "PASS"}},
                             "cpu_fallback_used": False},
    "gpC_nostl.json": {"classification": "OFFICIAL_CANDIDATE_PASS",
                       "leg_detail": {"exit_code": 0, "stderr_tail": ""}},
    "gpD_train_cli.json": {"parsed_facts": {"gpu_selected": {"device": "CUDA:0"}},
                           "checkpoints": [{"path": "last.pt"}, {"path": "best.pt"}]},
    "gpE_optimizer.json": {"optimizer_step_count": 3},
    "gpF_resume.json": {"stages": {"epoch_continuity": True},
                        "checkpoint_sha256": {"last.pt": "ef" * 32}},
    "gpH_stability.json": {"runs": [{"run": 1, "status": "PASS"}] * 10,
                           "n_total": 10, "cache_class": "cold"},
}
GATE_OF_FILE = {"gpA_provenance.json": "G0_provenance",
                "gpB_torch_gates.json": "G2_torch_torchvision_gpu",
                "gpC_nostl.json": "G1_miopen_nostl",
                "gpD_train_cli.json": "G3_ultralytics_cli",
                "gpE_optimizer.json": "G4_optimizer_update",
                "gpF_resume.json": "G5_checkpoint_resume",
                "gpH_stability.json": "G8_reliability"}


def _suite_record(name, runtime_class, gfx="gfx1100", **over):
    rec = {k: None for k in gp_lib.EVIDENCE_REQUIRED_KEYS}
    rec.update({
        "run_id": f"ADV-{name}", "mission": "R21.1",
        "timestamp": "2026-11-16T00:00:00+00:00",
        "gpu_name": "AMD Radeon RX 7900 XTX" if gfx == "gfx1100" else "AMD Radeon 8060S",
        "gfx_target": gfx, "windows_build": "10.0.26300",
        "driver_version": "32.0.21030.2001", "python": "3.12.16",
        "torch": DEV_TORCH, "torchvision": "0.29.2", "hip": "7.18.26441",
        "runtime_class": runtime_class, "command": "python gate",
        "exit_code": 0, "duration_s": 1.0, "pass_fail_skip": "PASS",
        "failure_classification": None, "raw_log_path": f"C:\\x\\{name}.log",
    })
    rec.update(SUITES[name])
    rec.update(over)
    return rec


def write_suite(tmp_path, runtime_class="OFFICIAL_CANDIDATE", gfx="gfx1100",
                omit=(), overrides=None, gate_status=True, gate_status_overrides=None,
                extra=None):
    """Write a provenance-complete gate suite + orchestrator gate_status.json."""
    overrides = overrides or {}
    for name in SUITES:
        if name in omit:
            continue
        (tmp_path / name).write_text(
            json.dumps(_suite_record(name, runtime_class, gfx,
                                     **overrides.get(name, {}))), encoding="utf-8")
        (tmp_path / (name[:-5] + ".log")).write_text("log\n", encoding="utf-8")
    if extra:
        for name, rec in extra.items():
            (tmp_path / name).write_text(json.dumps(rec), encoding="utf-8")
            (tmp_path / (name[:-5] + ".log")).write_text("log\n", encoding="utf-8")
    if gate_status:
        gates = []
        for name in SUITES:
            gate = GATE_OF_FILE[name]
            o = (gate_status_overrides or {}).get(name, {})
            entry = {"gate": gate, "exit_code": 0, "accepted": True,
                     "status": "PASS", "ended_utc": "2026-11-16T00:00:00+00:00"}
            entry.update(o)
            if entry.get("accepted"):
                entry["status"] = "PASS"
            else:
                entry["status"] = "FAIL"
            gates.append(entry)
        (tmp_path / "gate_status.json").write_text(json.dumps(
            {"run_id": "GP-x", "mode": "OfficialCandidate", "overall": "GO",
             "gates": gates}), encoding="utf-8")


def run_full(tmp_path, run_id="T", sequence="candidate", channel="dev"):
    gen = load_module("generate_report")
    rc = gen.cmd_full(type("A", (), {
        "run_id": run_id, "evidence_dir": str(tmp_path),
        "report_dir": str(tmp_path / "r"), "sequence": sequence,
        "channel": channel, "contract": None})())
    report = json.loads((tmp_path / "r" / "report.json").read_text(encoding="utf-8"))
    return rc, report


class TestAdversarialAcceptance:
    # 1. missing gate rejects the release
    def test_missing_gate_rejects(self, tmp_path):
        write_suite(tmp_path, omit=("gpD_train_cli.json",))
        rc, report = run_full(tmp_path)
        assert rc != 0 and report["verdict"] == "NO_GO"
        assert any("G3_ultralytics_cli: missing" in b for b in report["blockers"])

    # 2. failed gate rejects the release
    def test_failed_gate_rejects(self, tmp_path):
        write_suite(tmp_path, overrides={"gpE_optimizer.json": {
            "pass_fail_skip": "FAIL", "exit_code": 1}},
            gate_status_overrides={"gpE_optimizer.json": {
                "exit_code": 1, "accepted": False}})
        rc, report = run_full(tmp_path)
        assert rc != 0 and report["verdict"] == "NO_GO"
        assert report["gate_results"]["G4_optimizer_update"]["status"] != "PASS"

    # 3. an earlier failed gate cannot be hidden by a later PASS
    def test_early_failure_not_hidden_by_later_pass(self, tmp_path):
        write_suite(tmp_path, overrides={"gpC_nostl.json": {
            "pass_fail_skip": "FAIL", "exit_code": 1,
            "classification": "INCONCLUSIVE"}},
            gate_status_overrides={"gpC_nostl.json": {
                "exit_code": 1, "accepted": False}})
        rc, report = run_full(tmp_path)
        assert rc != 0 and report["verdict"] == "NO_GO"
        # the LATER gate still passed, yet the verdict must stay NO-GO
        assert report["gate_results"]["G2_torch_torchvision_gpu"]["status"] == "PASS"
        assert report["gate_results"]["G1_miopen_nostl"]["status"] != "PASS"

    # 4. a shimmed stack can never earn OfficialStable
    def test_shimmed_stack_cannot_earn_stable(self, tmp_path):
        write_suite(tmp_path, runtime_class="ENGINEERING_REFERENCE")
        rc, report = run_full(tmp_path, sequence="stable", channel="stable")
        assert rc != 0 and report["verdict"] == "NO_GO"
        assert report["final_golden_path_pass"] is False
        assert all(g["status"] != "PASS" for g in report["gate_results"].values())

    # 5. positive marker with unproven lineage cannot PASS (unit level)
    def test_marker_positive_unproven_lineage_cannot_pass(self):
        vp = load_module("verify_provenance")
        miopen_marker2 = {"loaded": True, "sha256": "ab" * 32,
                          "embedded_version_strings": ["3.6.3.4e7d93e3"],
                          "pr13437_marker_miopen_initializer_list": 2}
        lin = vp.evaluate_lineage(miopen_marker2, None)          # no ancestry proof
        assert lin["status"] == "ANCESTRY_ABSENT"
        assert lin["provenance_complete"] is False
        audit = {"merged_fix_commit": "f0a5d2664cf3334161f7b82c02dfcd2213988a8a",
                 "audits": [{"miopen_dll": {"sha256": "ab" * 32,
                                            "build_commit": "deadbee",
                                            "marker_miopen_initializer_list": 2},
                             "ancestry": {"status": "diverged", "ahead_by": 2,
                                          "behind_by": 92}}]}
        lin2 = vp.evaluate_lineage(miopen_marker2, audit)        # rc-style branch cut
        assert lin2["status"] == "ANCESTRY_BEHIND" and not lin2["provenance_complete"]
        ok_audit = {"merged_fix_commit": "f0a5d2664cf3334161f7b82c02dfcd2213988a8a",
                    "audits": [{"miopen_dll": {"sha256": "ab" * 32,
                                               "build_commit": "4e7d93e3"},
                                "ancestry": {"status": "ahead", "ahead_by": 604,
                                             "behind_by": 0}}]}
        lin3 = vp.evaluate_lineage(miopen_marker2, ok_audit)
        assert lin3["status"] == "ANCESTRY_VERIFIED" and lin3["provenance_complete"]

    # 6. a DEV wheel can never be promoted to Stable
    def test_dev_wheel_cannot_be_promoted_to_stable(self, tmp_path):
        write_suite(tmp_path)  # full DEV candidate suite, everything PASS
        rc, report = run_full(tmp_path, sequence="candidate", channel="dev")
        assert rc == 0
        assert report["verdict"] == "DEV_CANDIDATE_PASS"
        assert report["verdict"] != "OFFICIAL_STABLE_PASS"
        # a DEV-classified record smuggled into a stable sequence is rejected
        write_suite(tmp_path)
        rc2, report2 = run_full(tmp_path, sequence="stable", channel="stable")
        assert rc2 != 0 and report2["verdict"] == "NO_GO"
        assert gp_lib.classify_runtime({"any_workaround_present": False}, "dev",
                                       {"loaded": True,
                                        "pr13437_marker_miopen_initializer_list": 2}) \
            == "OFFICIAL_CANDIDATE"

    # 7. missing gfx1151 blocks any cross-arch release PASS
    def test_missing_gfx1151_blocks_cross_arch(self, tmp_path):
        write_suite(tmp_path, runtime_class="OFFICIAL_STABLE", gfx="gfx1100",
                    extra={"gpJ_clean_windows.json": {
                        **_suite_record("gpH_stability.json", "OFFICIAL_STABLE"),
                        "gate_id": "G9_clean_windows",
                        "evidence_class": "CLEAN_WINDOWS_INSTALL",
                        "gates": None, "runs": None, "n_total": None,
                        "cache_class": None, "parsed_facts": {"ok": True},
                        "checkpoints": []}},
                    gate_status=True)
        rc, report = run_full(tmp_path, sequence="stable", channel="stable")
        assert rc != 0 and report["verdict"] == "NO_GO"
        assert report["full_cross_arch_release_pass"] is False
        assert any("G7_gfx1151_physical" in b for b in report["blockers"])

    # 8. missing clean Windows blocks the final Golden Path PASS
    def test_missing_clean_windows_blocks_final(self, tmp_path):
        write_suite(tmp_path, runtime_class="OFFICIAL_STABLE")
        rc, report = run_full(tmp_path, sequence="stable", channel="stable")
        assert rc != 0 and report["verdict"] == "NO_GO"
        assert report["final_golden_path_pass"] is False

    # 8b. HOST_REUSE_FRESH_VENV alone is not CLEAN_WINDOWS_INSTALL
    def test_host_reuse_is_not_clean_windows(self, tmp_path):
        write_suite(tmp_path, runtime_class="OFFICIAL_STABLE",
                    extra={"gpI_gfx1151.json": _suite_record(
                        "gpC_nostl.json", "OFFICIAL_STABLE", gfx="gfx1151"),
                        "gpJ_clean_windows.json": {
                            **_suite_record("gpH_stability.json", "OFFICIAL_STABLE"),
                            "gate_id": "G9_clean_windows",
                            "evidence_class": "HOST_REUSE_FRESH_VENV",
                            "gates": None, "runs": None, "n_total": None,
                            "cache_class": None, "parsed_facts": {"ok": True},
                            "checkpoints": []}})
        rc, report = run_full(tmp_path, sequence="stable", channel="stable")
        assert report["final_golden_path_pass"] is False
        assert rc != 0

    # 9. the exact observed DEV torch local version is recognized as AMD HIP
    def test_dev_torch_local_version_recognized(self):
        p = gp_lib.parse_rocm_local_version(DEV_TORCH)
        assert p["is_amd_rocm_local"] is True
        assert p["rocm_version"] == "10.3.0"
        assert gp_lib.torch_wheel_is_amd_hip(DEV_TORCH, DEV_TORCH_URL) is True
        assert gp_lib.torch_wheel_is_amd_hip(DEV_TORCH, "https://pypi.org/simple/torch/") is False
        assert gp_lib.torch_wheel_is_amd_hip("2.15.0", DEV_TORCH_URL) is False
        assert gp_lib.torch_wheel_is_amd_hip("2.12.0+rocm7.14.1",
                                             "https://repo.amd.com/rocm/whl-multi-arch/torch/x.whl") is True
        assert gp_lib.parse_rocm_local_version(
            "2.16.0a0%2Bgitf1d8eb9e.devrocm10.2.0.dev0.434410c")["rocm_version"] == "10.2.0"
        assert gp_lib.rocm_family_of("rocm-bootstrap", "0.3.0") is None
        assert gp_lib.rocm_family_of("rocm-sdk-libraries", "10.3.0.dev0+ff") == "10"

    # 10. synthetic / hand-written evidence cannot AUTOMATICALLY earn a PASS
    def test_unorchestrated_evidence_cannot_pass(self, tmp_path):
        write_suite(tmp_path, gate_status=False)  # no gate_status.json at all
        rc, report = run_full(tmp_path)
        assert rc != 0 and report["verdict"] == "NO_GO"
        assert all(g["status"] == "UNORCHESTRATED"
                   for g in report["gate_results"].values())

    def test_harness_fixture_claiming_pass_is_violation(self, tmp_path):
        write_suite(tmp_path, overrides={"gpD_train_cli.json": {
            "harness_fixture": True}})
        rc, report = run_full(tmp_path)
        assert rc == 1  # PASS claim on a fixture is a violation
        assert any("HARNESS_FIXTURE_ONLY" in v for v in report["violations"])

    def test_handwritten_record_without_provenance_is_unproven(self, tmp_path):
        # complete-looking suite but ONE record lost its machine identity
        write_suite(tmp_path, overrides={"gpF_resume.json": {
            "gpu_name": None, "gfx_target": None, "windows_build": None,
            "driver_version": None, "hip": None, "raw_log_path": None}})
        rc, report = run_full(tmp_path)
        assert rc != 0 and report["verdict"] == "NO_GO"
        assert report["gates"]["gpF_resume.json"]["evidence_class"] == "PHYSICAL_UNPROVEN"

    # unscoped invocation (no --sequence) must never produce a verdict
    def test_unscoped_sequence_is_no_go(self, tmp_path):
        write_suite(tmp_path)
        gen = load_module("generate_report")
        rc = gen.cmd_full(type("A", (), {
            "run_id": "T", "evidence_dir": str(tmp_path),
            "report_dir": str(tmp_path / "r2"), "sequence": None,
            "channel": None, "contract": None})())
        report = json.loads((tmp_path / "r2" / "report.json").read_text(encoding="utf-8"))
        assert rc != 0 and report["verdict"] == "NO_GO_UNSCOPED"


# --- gate orchestration contract (TASK A, static) ------------------------------
class TestGateOrchestrationStatic:
    def test_harness_checks_exit_code_after_every_gate(self):
        src = (HERE.parent / "run-golden-path.ps1").read_text(encoding="utf-8")
        assert "Invoke-Gate" in src
        import re as _re
        blocks = _re.findall(r'Invoke-Gate "[^"]+" \{.*?\}\s*\|?\s*Out-Null',
                             src, _re.S)
        assert len(blocks) >= 15, f"expected all gates wrapped, got {len(blocks)}"
        # every venv gate call sits INSIDE an Invoke-Gate block (per-gate exit check)
        outside = src
        for b in blocks:
            outside = outside.replace(b, "")
        bare = [ln for ln in outside.splitlines()
                if "& $vpy -I" in ln and "train-summary" not in ln]
        assert not bare, f"gates not wrapped in Invoke-Gate: {bare}"
        # the report generator can never be the only success criterion
        assert "REPORT_generate_report_full" in src
        assert "$failed.Count -gt 0) { exit 3 }" in src

    def test_candidate_and_stable_sequences_include_exact_cli(self):
        src = (HERE.parent / "run-golden-path.ps1").read_text(encoding="utf-8")
        assert '"G3_ultralytics_cli"' in src  # inside Run-GateSequence
        # the exact CLI script is invoked with the candidate/stable venv
        assert "train_yolo.ps1" in src

    def test_quickstart_fails_closed_by_default(self):
        src = (HERE.parent / "docs" / "r23" / "quickstart.ps1").read_text(encoding="utf-8")
        assert '[string]$Mode = "Status"' in src
        assert "exit 3" in src and "EngineeringDemonstration" in src
        # no install command may run before the mode gate
        assert "-m venv" not in src.split("# --- explicitly labeled")[0]



# --- package source policy: adversarial origin audit (R22A.1 P0) --------------
# The frozen locks recorded gpu_stack_origin_official_channel.ok=false with
# violations=["rocm-bootstrap"] because a NAME-PREFIX rule treated every
# rocm* artifact as native stack. The corrected policy classifies per
# artifact: native AMD stack = exact official channel; approved pure-Python
# PyPI bootstrap = exact pinned verified artifact; third-party unconstrained.
# audit_lock() must recompute this from URLs + metadata and NEVER trust a
# serialized rules_checked.ok value.
class TestPackageOriginPolicy:
    DEV = gp_lib.OFFICIAL_CHANNELS["dev"]
    TORCH_DEV = "2.15.0+gitf6cd88cb.devrocm10.3.0.dev0.ff5769655eeb1b91a46bce9edc16d87ca0efe7b6"
    BOOTSTRAP_URL = ("https://files.pythonhosted.org/packages/0c/b6/30144880b8e2bad4e9991b"
                     "08352c7cec17931b5d26b1f9108192f4f17d91/rocm_bootstrap-0.3.0-py3-none-any.whl")
    BOOTSTRAP_SHA = gp_lib.APPROVED_PYPI_BOOTSTRAP["rocm-bootstrap"]["sha256"]

    def _pkg(self, name, version, url, sha=None):
        return {"name": name, "version": version, "url": url,
                "sha256": sha if sha is not None else "ab" * 32}

    def _lock(self, packages, rules_checked=None):
        return {"channel": "dev", "channel_url": self.DEV,
                "packages": packages,
                "rules_checked": rules_checked if rules_checked is not None else {}}

    def _installed(self, lock):
        # audit_lock checks coverage for installed gpu-stack names only
        return {p["name"].lower(): p["version"] for p in lock["packages"]
                if p["name"].lower().startswith(("torch", "torchvision", "rocm", "amd-torch"))}

    def _valid_packages(self):
        return [
            self._pkg("torch", self.TORCH_DEV,
                      self.DEV + "torch/torch-2.15.0-cp312-cp312-win_amd64.whl"),
            self._pkg("torchvision", "0.29.2+gitb2281111.devrocm10.3.0.dev0",
                      self.DEV + "torchvision/torchvision-0.29.2-py3-none-win_amd64.whl"),
            self._pkg("rocm", "10.3.0.dev0+ff5769655eeb1b91a46bce9edc16d87ca0efe7b6",
                      self.DEV + "rocm/rocm-10.3.0.dev0.tar.gz"),
            self._pkg("rocm-sdk-core", "10.3.0.dev0+ff5769655eeb1b91a46bce9edc16d87ca0efe7b6",
                      self.DEV + "rocm-sdk-core/rocm_sdk_core-10.3.0.dev0-py3-none-win_amd64.whl"),
            self._pkg("rocm-sdk-libraries", "10.3.0.dev0+ff5769655eeb1b91a46bce9edc16d87ca0efe7b6",
                      self.DEV + "rocm-sdk-libraries/rocm_sdk_libraries-10.3.0.dev0-py3-none-win_amd64.whl"),
            self._pkg("rocm-bootstrap", "0.3.0", self.BOOTSTRAP_URL,
                      sha=self.BOOTSTRAP_SHA),
            self._pkg("numpy", "2.5.5",
                      "https://files.pythonhosted.org/packages/np/numpy-2.5.5-cp312-cp312-win_amd64.whl"),
        ]

    def _audit(self, lock):
        vp = load_module("verify_provenance")
        return vp.audit_lock(lock, self._installed(lock), None)

    # 1. PyPI bootstrap with verified identity PASSES
    def test_pypi_bootstrap_verified_identity_passes(self):
        res = self._audit(self._lock(self._valid_packages()))
        assert res["ok"] is True, res["failures"]
        assert res["package_origin_audit"]["ok"] is True
        assert res["package_origin_audit"]["classes"] == {
            "native_amd_gpu_stack": 5, "approved_pypi_bootstrap": 1, "third_party": 1}
        assert res["rocm_family_mix_audit"]["families"] == ["10"]

    # 2. PyPI torch substitution FAILS
    def test_pypi_torch_substitution_fails(self):
        pkgs = self._valid_packages()
        pkgs[0] = self._pkg("torch", "2.15.0",
                            "https://files.pythonhosted.org/packages/aa/torch-2.15.0-cp312-cp312-win_amd64.whl")
        res = self._audit(self._lock(pkgs))
        assert res["ok"] is False
        assert any("torch" in f and "non-official" in f for f in res["failures"])

    # 3. PyPI MIOpen/ROCm native binary (rocm-sdk-libraries) FAILS
    def test_pypi_rocm_native_binary_fails(self):
        pkgs = self._valid_packages()
        pkgs[4] = self._pkg("rocm-sdk-libraries", "10.3.0.dev0",
                            "https://files.pythonhosted.org/packages/aa/rocm_sdk_libraries-10.3.0.dev0-py3-none-win_amd64.whl")
        res = self._audit(self._lock(pkgs))
        assert res["ok"] is False
        assert any("rocm-sdk-libraries" in f and "substitution" in f
                   for f in res["failures"])

    # 4. unknown bootstrap source FAILS (not served by PyPI)
    def test_unknown_bootstrap_source_fails(self):
        pkgs = self._valid_packages()
        pkgs[5] = self._pkg("rocm-bootstrap", "0.3.0",
                            "https://example.com/wheels/rocm_bootstrap-0.3.0-py3-none-any.whl",
                            sha=self.BOOTSTRAP_SHA)
        res = self._audit(self._lock(pkgs))
        assert res["ok"] is False
        assert any("unknown bootstrap source" in f for f in res["failures"])

    # 4b. approved bootstrap name but WRONG version / WRONG sha FAILS
    def test_bootstrap_wrong_version_and_wrong_sha_fail(self):
        for bad in (("0.9.9", self.BOOTSTRAP_SHA), ("0.3.0", "cd" * 32)):
            pkgs = self._valid_packages()
            pkgs[5] = self._pkg("rocm-bootstrap", bad[0], self.BOOTSTRAP_URL,
                                sha=bad[1])
            res = self._audit(self._lock(pkgs))
            assert res["ok"] is False, bad
            assert any("bootstrap rocm-bootstrap" in f for f in res["failures"]), bad

    # 5. forged rules_checked.ok=true FAILS (audit recomputes from URLs)
    def test_forged_rules_checked_ok_true_fails(self):
        pkgs = self._valid_packages()
        pkgs[0] = self._pkg("torch", "2.15.0",
                            "https://files.pythonhosted.org/packages/aa/torch-2.15.0-cp312-cp312-win_amd64.whl")
        forged = {"gpu_stack_origin_official_channel": {"ok": True, "violations": []},
                  "rocm_family_mix": {"ok": True}, "device_wheel_present": True,
                  "torch_is_amd_hip": True}
        res = self._audit(self._lock(pkgs, rules_checked=forged))
        assert res["ok"] is False, "forged rules_checked.ok=true must not pass"
        assert res["package_origin_audit"]["ok"] is False
        assert "rules_checked never read" in res["package_origin_audit"]["recomputed_from"]

    # 6. missing SHA256 FAILS (native stack and bootstrap alike)
    def test_missing_sha256_fails(self):
        pkgs = self._valid_packages()
        pkgs[0] = self._pkg("torch", self.TORCH_DEV,
                            self.DEV + "torch/torch-2.15.0-cp312-cp312-win_amd64.whl",
                            sha="")
        res = self._audit(self._lock(pkgs))
        assert res["ok"] is False
        assert any("no valid SHA256" in f for f in res["failures"])
        pkgs[5] = self._pkg("rocm-bootstrap", "0.3.0", self.BOOTSTRAP_URL, sha="")
        res = self._audit(self._lock(pkgs))
        assert res["ok"] is False
        assert any("does not match the verified PyPI artifact" in f
                   for f in res["failures"])

    # 7. mixed ROCm family FAILS (recomputed, not read from rules_checked)
    def test_mixed_rocm_family_fails(self):
        pkgs = self._valid_packages()
        pkgs[3] = self._pkg("rocm-sdk-core", "8.2.0",
                            self.DEV + "rocm-sdk-core/rocm_sdk_core-8.2.0-py3-none-win_amd64.whl")
        res = self._audit(self._lock(pkgs))
        assert res["ok"] is False
        assert any("mixed ROCm families" in f for f in res["failures"])
        assert res["rocm_family_mix_audit"]["families"] == ["10", "8"]

    # regression: BOTH frozen 46-artifact DEV locks pass the corrected policy.
    # Each lock = 45 wheels + 1 official ROCm source distribution (the rocm
    # sdist). Their historical rules_checked.gpu_stack_origin_official_channel
    # .ok=false (violations=["rocm-bootstrap"]) stays frozen in the files; the
    # corrected audit recomputes from URLs and PASSES.
    def test_frozen_dev_locks_pass_corrected_validation(self):
        root = HERE.parents[1]
        n_expected = {"native_amd_gpu_stack": 8, "approved_pypi_bootstrap": 1,
                      "third_party": 37}
        for rel in ("evidence/raw/r22-dev-rerun/resolved_wheel_lock.json",
                    "evidence/raw/r22a-gfx1151/R22A_PACKAGE_LOCK.json"):
            lock = json.loads((root / rel).read_text(encoding="utf-8"))
            assert len(lock["packages"]) == 46
            # exactly one non-wheel artifact: the official ROCm source dist
            non_whl = [p for p in lock["packages"]
                       if not p.get("wheel_filename", "").endswith(".whl")]
            assert [(p["name"], p["wheel_filename"].rsplit(".", 1)[-1])
                    for p in non_whl] == [("rocm", "gz")], rel
            historical = lock["rules_checked"]["gpu_stack_origin_official_channel"]
            assert historical["ok"] is False \
                and historical["violations"] == ["rocm-bootstrap"], rel
            res = self._audit(lock)
            assert res["ok"] is True, (rel, res["failures"])
            assert res["package_origin_audit"]["classes"] == n_expected, rel
            assert res["rocm_family_mix_audit"]["families"] == ["10"], rel


# --- R22A.3 Part A: default optimizer=auto→AdamW + AMP verdict (mission §10) --
class TestAdamWAmpVerdict:
    @staticmethod
    def _good_a() -> dict:
        return {
            "optim": {"requested": "auto",
                      "resolved_in_args_after_build": "AdamW",
                      "actual_class": "AdamW"},
            "amp": {"trainer_amp_resolved": True,
                    "autocast_forward_samples": {"sampled": 50, "enabled": 50},
                    "stem_conv_output_dtypes_observed": {"float16": 50}},
            "optimizer_steps": {
                "attempted_invocations": 12,
                "effective_updates_sentinel_proven": 9,
                "skipped_found_inf_flagged": 0,
                "grads_finite_on_stepped_updates": True},
            "gradscaler": {"present": True, "scale_history_len": 12},
            "raw_trainer_model_delta": {"tensors_changed_beyond_1e_9": 210,
                                        "all_finite": True},
            "batches_completed": 48,
        }

    def _v(self, facts, min_updates=3):
        aa = load_module("audit_adamw_amp")
        return aa.compute_adamw_verdict(facts, min_updates)

    def test_full_good_facts_pass(self):
        r = self._v(self._good_a())
        assert r["verdict"] == "ADAMW_AMP_MULTISTEP_PASS"
        assert r["failure_classification"] is None

    def test_auto_resolving_to_sgd_fails(self):
        f = self._good_a()
        f["optim"] = {"requested": "auto", "resolved_in_args_after_build": "SGD",
                      "actual_class": "SGD"}
        r = self._v(f)
        assert (r["verdict"], r["failure_classification"]) == ("FAIL", "ADAMW_AUTO_NOT_SELECTED")

    def test_manual_adamw_is_not_auto_selection(self):
        f = self._good_a()
        f["optim"]["requested"] = "AdamW"  # a forced AdamW must not count as auto
        assert self._v(f)["verdict"] == "FAIL"

    def test_amp_false_fails(self):
        f = self._good_a()
        f["amp"]["trainer_amp_resolved"] = False
        assert self._v(f)["failure_classification"] == "AMP_NOT_ENABLED"

    def test_amp_setup_without_forward_autocast_fails(self):
        f = self._good_a()
        f["amp"]["autocast_forward_samples"] = {"sampled": 50, "enabled": 0}
        assert self._v(f)["failure_classification"] == "NO_FORWARD_AUTOCAST"

    def test_autocast_without_observed_low_precision_is_inconclusive(self):
        f = self._good_a()
        f["amp"]["stem_conv_output_dtypes_observed"] = {"float32": 50}
        r = self._v(f)
        assert (r["verdict"], r["failure_classification"]) == \
            ("INCONCLUSIVE", "NO_LOW_PRECISION_OP_OBSERVED")

    def test_scaler_present_without_effective_updates_fails(self):
        f = self._good_a()
        f["optimizer_steps"]["effective_updates_sentinel_proven"] = 0
        assert self._v(f)["failure_classification"] == "NO_EFFECTIVE_OPTIMIZER_UPDATES"

    def test_missing_parameter_delta_fails(self):
        f = self._good_a()
        f["raw_trainer_model_delta"]["tensors_changed_beyond_1e_9"] = 0
        assert self._v(f)["failure_classification"] == "PARAM_DELTA_MISSING"

    def test_only_bn_buffers_changed_fails(self):
        # named_parameters deltas all zero while a forged bn_buffers_changed
        # flag claims otherwise — buffers are excluded BY DESIGN and can never
        # substitute for parameter evidence
        f = self._good_a()
        f["raw_trainer_model_delta"]["tensors_changed_beyond_1e_9"] = 0
        f["raw_trainer_model_delta"]["bn_buffers_changed"] = True
        assert self._v(f)["failure_classification"] == "PARAM_DELTA_MISSING"

    def test_nonfinite_gradients_in_any_group_fail(self):
        f = self._good_a()
        f["optimizer_steps"]["grads_finite_on_stepped_updates"] = False
        assert self._v(f)["failure_classification"] == "NONFINITE_GRADIENTS"

    def test_nonfinite_parameter_deltas_fail(self):
        f = self._good_a()
        f["raw_trainer_model_delta"]["all_finite"] = False
        assert self._v(f)["failure_classification"] == "NONFINITE_PARAM_DELTAS"

    def test_missing_step_evidence_fails(self):
        f = self._good_a()
        f["optimizer_steps"]["attempted_invocations"] = 0
        f["optimizer_steps"]["effective_updates_sentinel_proven"] = 0
        assert self._v(f)["failure_classification"] == "NO_EFFECTIVE_OPTIMIZER_UPDATES"

    def test_min_updates_threshold_enforced(self):
        f = self._good_a()
        f["optimizer_steps"]["effective_updates_sentinel_proven"] = 2
        assert self._v(f, 3)["verdict"] == "FAIL"
        assert self._v(f, 2)["verdict"] == "ADAMW_AMP_MULTISTEP_PASS"

    def test_empty_facts_fail_closed(self):
        assert self._v({})["verdict"] in ("FAIL", "INCONCLUSIVE")


# --- R22A.3 Part B: workers=8 verdicts (mission §10) --------------------------
class TestWorkers8Verdict:
    @staticmethod
    def _good_run(i: int = 1, cold: bool = True) -> dict:
        return {
            "run": i, "run_id": f"B-R{i}", "status": "PASS", "exit_code": 0,
            "resolved_num_workers": 8, "requested_workers": 8,
            "distinct_worker_pids": 12, "worker_shutdown": "CLEAN",
            "cache_class": ("cold(fresh-USERPROFILE, run-isolated)" if cold
                            else "warm(retained isolated home)"),
            "cold_identity_verified": True,
        }

    def _mod(self):
        return load_module("run_stability")

    def test_requested8_effective4_fails(self):
        rs = self._mod()
        base = self._good_run()
        base["resolved_num_workers"] = 4
        assert rs.finalize_worker_run(base) == ("FAIL", "WORKER_COUNT_NOT_MET")

    def test_effective8_without_pid_evidence_is_inconclusive(self):
        rs = self._mod()
        base = self._good_run()
        base["distinct_worker_pids"] = 0
        assert rs.finalize_worker_run(base) == ("INCONCLUSIVE", "NO_WORKER_PID_EVIDENCE")

    def test_partial_pid_evidence_is_inconclusive(self):
        rs = self._mod()
        base = self._good_run()
        base["distinct_worker_pids"] = 5  # 0 < observed < resolved
        assert rs.finalize_worker_run(base) == ("INCONCLUSIVE", "PARTIAL_WORKER_PID_EVIDENCE")

    def test_worker_spawn_failure_fails(self):
        rs = self._mod()
        v = rs.classify_run(1, "DataLoader worker failed to start on Windows")
        assert v["status"] == "FAIL" and "WORKER_SPAWN_FAILURE" in v["anomalies"]

    def test_worker_crash_fails(self):
        rs = self._mod()
        v = rs.classify_run(1, "DataLoader worker (pid 1234) exited unexpectedly")
        assert v["status"] == "FAIL" and "WORKER_CRASH" in v["anomalies"]

    def test_worker_orphaned_after_parent_fails(self):
        rs = self._mod()
        base = self._good_run()
        base["worker_shutdown"] = "ORPHANS(2): [111, 222]"
        assert rs.finalize_worker_run(base) == ("FAIL", "WORKER_SHUTDOWN_FAILURE")

    def test_timeout_fails(self):
        rs = self._mod()
        assert rs.classify_run(124, "")["failure_classification"] == "DATALOADER_TIMEOUT"

    def test_missing_process_exit_code_fails(self):
        rs = self._mod()
        base = self._good_run()
        del base["exit_code"]
        assert rs.finalize_worker_run(base) == ("FAIL", "MISSING_PROCESS_EXIT_CODE")

    def test_cold_cache_falsely_labeled_fails(self):
        rs = self._mod()
        base = self._good_run(cold=True)
        base["cold_identity_verified"] = False  # no isolated-home evidence
        assert rs.finalize_worker_run(base) == \
            ("FAIL", "COLD_LABEL_WITHOUT_CACHE_IDENTITY_EVIDENCE")

    def test_five_clean_runs_overall_pass(self):
        rs = self._mod()
        runs = [self._good_run(1, True), self._good_run(2, True)] + \
               [self._good_run(i, False) for i in (3, 4, 5)]
        ov = rs.overall_workers8_verdict(runs, 2, 3)
        assert ov["verdict"] == "WORKERS8_SHORT_RELIABILITY_PASS"
        assert ov["cold_pass"] == "2/2" and ov["warm_pass"] == "3/3"

    def test_four_pass_one_fail_overall_no_go(self):
        rs = self._mod()
        runs = [self._good_run(1, True), self._good_run(2, True),
                self._good_run(3, False), self._good_run(4, False)]
        bad = self._good_run(5, False)
        bad.update(status="FAIL", failure_classification="WORKER_CRASH")
        runs.append(bad)
        ov = rs.overall_workers8_verdict(runs, 2, 3)
        assert ov["verdict"] == "NO-GO"
        assert any("warm 2/3" in p for p in ov["problems"])

    def test_sixth_substitution_run_cannot_repair_matrix(self):
        rs = self._mod()
        runs = [self._good_run(1, True), self._good_run(2, True),
                self._good_run(3, False)]
        bad = self._good_run(4, False)
        bad.update(status="FAIL")
        runs += [bad, self._good_run(5, False), self._good_run(6, False)]
        assert rs.overall_workers8_verdict(runs, 2, 3)["verdict"] == "NO-GO"


class TestChildSpawnSafety:
    def _mod(self):
        return load_module("run_stability")

    def test_generated_child_is_spawn_safe(self):
        rs = self._mod()
        rendered = rs.CHILD.format(device=-1, project="C:/tmp/p", name="train",
                                   seed=1, workers=8, data="coco128.yaml", extra="",
                                   facts_path="C:/tmp/f.json", run_id="X",
                                   batch_arg="16", imgsz_arg="256")
        assert rs.child_spawn_safe(rendered) == (True, None)
        compile(rendered, "child.py", "exec")  # must also be valid python

    def test_child_without_main_guard_rejected(self):
        rs = self._mod()
        bad = "import sys\nfrom ultralytics import YOLO\nYOLO('yolo26n.pt').train()\n"
        ok, why = rs.child_spawn_safe(bad)
        assert ok is False and why

    def test_guard_present_but_module_level_train_rejected(self):
        rs = self._mod()
        bad = ("import multiprocessing\nfrom ultralytics import YOLO\n"
               "YOLO('yolo26n.pt').train()\n\n"
               "if __name__ == '__main__':\n    multiprocessing.freeze_support()\n")
        ok, why = rs.child_spawn_safe(bad)
        assert ok is False and "module-level" in why


# --- R22A.3 combined acceptance (mission §13) ---------------------------------
class TestR22A3Acceptance:
    @staticmethod
    def _part_a_pass() -> dict:
        return {
            "optim": {"requested": "auto", "resolved_in_args_after_build": "AdamW",
                      "actual_class": "AdamW"},
            "amp": {"trainer_amp_resolved": True,
                    "autocast_forward_samples": {"sampled": 50, "enabled": 50},
                    "stem_conv_output_dtypes_observed": {"float16": 50}},
            "optimizer_steps": {"attempted_invocations": 12,
                                "effective_updates_sentinel_proven": 9,
                                "grads_finite_on_stepped_updates": True},
            "gradscaler": {"present": True, "scale_history_len": 12},
            "raw_trainer_model_delta": {"tensors_changed_beyond_1e_9": 210,
                                        "all_finite": True},
            "batches_completed": 48,
            "gpu_name": "AMD Radeon(TM) 8060S Graphics", "gfx_target": "gfx1151",
            "runtime_class": "OFFICIAL_CANDIDATE",
            "minimum_effective_updates_required": 3,
        }

    @staticmethod
    def _part_b_pass() -> dict:
        def run(i, cold):
            return {"run_id": f"B-R{i}", "status": "PASS",
                    "cache_class": ("cold(fresh-USERPROFILE, run-isolated)" if cold
                                    else "warm(retained isolated home)")}
        return {"runs": [run(1, True), run(2, True), run(3, False), run(4, False),
                         run(5, False)],
                "cold_runs": 2,
                "gpu_name": "AMD Radeon(TM) 8060S Graphics", "gfx_target": "gfx1151",
                "runtime_class": "OFFICIAL_CANDIDATE"}

    def _mod(self):
        return load_module("r22a3_acceptance")

    def test_both_parts_pass_combined_pass(self):
        c = self._mod().combined_verdict(self._part_a_pass(), self._part_b_pass())
        assert c["verdict"] == "R22A3_GFX1151_SUPPLEMENTAL_PASS"

    def test_part_a_fail_gives_partial_or_no_go_with_reason(self):
        pa = self._part_a_pass()
        pa["optimizer_steps"]["effective_updates_sentinel_proven"] = 0
        c = self._mod().combined_verdict(pa, self._part_b_pass())
        assert c["verdict"] in ("PARTIAL_PASS", "NO-GO")
        assert any("PartA FAIL" in r for r in c["reasons"])

    def test_part_b_fail_gives_no_go(self):
        pb = self._part_b_pass()
        pb["runs"][3]["status"] = "FAIL"
        c = self._mod().combined_verdict(self._part_a_pass(), pb)
        assert c["verdict"] in ("PARTIAL_PASS", "NO-GO")

    def test_synthetic_receipt_claiming_physical_gpu_rejected(self):
        pa = self._part_a_pass()
        pa["gpu_name"] = None  # no physical GPU provenance
        c = self._mod().combined_verdict(pa, self._part_b_pass())
        assert c["verdict"] != "R22A3_GFX1151_SUPPLEMENTAL_PASS"
        assert any("synthetic" in r for r in c["reasons"])

    def test_wrong_architecture_cannot_earn_gfx1151_verdict(self):
        pa = self._part_a_pass()
        pa["gfx_target"] = "gfx1100"
        c = self._mod().combined_verdict(pa, self._part_b_pass())
        assert c["verdict"] != "R22A3_GFX1151_SUPPLEMENTAL_PASS"

    def test_engineering_reference_runtime_cannot_pass(self):
        pa = self._part_a_pass()
        pa["runtime_class"] = "ENGINEERING_REFERENCE"
        c = self._mod().combined_verdict(pa, self._part_b_pass())
        assert c["verdict"] != "R22A3_GFX1151_SUPPLEMENTAL_PASS"

    def test_claimed_verdict_is_never_authority(self):
        pa = self._part_a_pass()
        pa["pass_fail_skip"] = "ADAMW_AMP_MULTISTEP_PASS"  # forged claim
        pa["optim"]["resolved_in_args_after_build"] = "SGD"
        pa["optim"]["actual_class"] = "SGD"
        c = self._mod().combined_verdict(pa, self._part_b_pass())
        assert c["verdict"] != "R22A3_GFX1151_SUPPLEMENTAL_PASS"

    def test_ceiling_is_dev_candidate(self):
        c = self._mod().combined_verdict(self._part_a_pass(), self._part_b_pass())
        assert "DEV_CANDIDATE" in c["runtime_ceiling"]
        assert "OFFICIAL_STABLE" not in c["verdict"]


# --- R22A.3 evidence receipts must always serialize (harness robustness) ------
class TestEvidenceReceiptSerialization:
    def test_sanitize_converts_non_json_native_values(self):
        aa = load_module("audit_adamw_amp")

        class FakeDtype:  # stands in for torch.dtype (CPU test, no torch)
            def __repr__(self):
                return "torch.float16"

        rec = {"dtype": FakeDtype(), "nested": {"seq": [FakeDtype(), 1, None, True]},
               "plain": "x", "ok": [1, 2.5, False]}
        s = aa.sanitize(rec)
        out = json.dumps(s)  # must not raise
        assert s["dtype"] == "torch.float16"
        assert json.loads(out)["nested"]["seq"][1] == 1

    def test_spawn_safety_checker_accepts_single_quoted_guard(self):
        rs = load_module("run_stability")
        src = ("import multiprocessing\n\n\ndef main():\n    pass\n\n\n"
               "if __name__ == '__main__':\n    multiprocessing.freeze_support()\n"
               "    main()\n")
        assert rs.child_spawn_safe(src) == (True, None)
