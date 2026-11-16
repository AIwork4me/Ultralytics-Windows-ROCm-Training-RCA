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

