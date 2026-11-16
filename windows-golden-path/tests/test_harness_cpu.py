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
REPO_ROOT = SCRIPTS.parent.parent


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


# =============================================================================
# R22A.2 Part A — DEFAULT optimizer=auto → AdamW + AMP acceptance contract
# (CPU-only; synthetic fixtures exercise evaluate_adamw_contract and can
#  NEVER earn a physical PASS)
# =============================================================================
def adamw_facts(**over):
    # base fixture mirrors the REAL observed gfx1100 Part A shape: 11 python
    # level step calls, 5 GradScaler backoffs, 6 CONFIRMED checksum updates —
    # fused AdamW semantics where the inf skip happens inside the kernel
    f = {
        "gpu_name": "AMD Radeon RX 7900 XTX", "gfx_target": "gfx1100",
        "harness_fixture": False,
        "optimizer_requested": "auto", "optimizer_class": "AdamW",
        "optimizer_resolution_note": "optimizer=auto resolved to AdamW",
        "amp_resolved": True,
        "autocast_forward_on": 48, "autocast_forward_samples": 48,
        "low_precision_op_samples": 48, "low_precision_dtype": "torch.float16",
        "optimizer_steps_underlying": 11, "confirmed_update_events": 6,
        "scaler_step_attempts": 11,
        "per_step_events": [
            {"step": i + 1, "param_checksum_changed": i < 6,
             "pre_step_grads_finite": i >= 5}
            for i in range(11)],
        "gradscaler_present": True,
        "grads_finite_all_steps": False,  # skipped steps carry nonfinite grads
        "grads_finite_at_confirmed_updates": True,
        "raw_trainer_model_delta": {"tensors_changed_beyond_1e-9": 350,
                                    "all_finite": True},
        "buffer_delta": {"tensors_changed_beyond_1e-9": 40},
        "training_completed": True,
    }
    f.update(over)
    return f


class TestAdamwAmpContract:
    ev = staticmethod(load_module("audit_adamw_amp").evaluate_adamw_contract)

    def test_auto_resolving_adamw_accepted(self):
        r = self.ev(adamw_facts())
        assert r["verdict"] == "ADAMW_AMP_MULTISTEP_PASS", r

    def test_auto_resolving_sgd_rejected(self):
        r = self.ev(adamw_facts(optimizer_class="SGD"))
        assert r["verdict"] == "ADAMW_AMP_FAIL"
        assert "not AdamW" in r["reason"]

    def test_auto_resolving_musgd_rejected(self):
        # 8.4.214 heuristic: iterations > 10000 selects MuSGD
        r = self.ev(adamw_facts(optimizer_class="MuSGD"))
        assert r["verdict"] == "ADAMW_AMP_FAIL" and "MuSGD" in r["reason"]

    def test_forced_adamw_request_rejected(self):
        # the harness must request the DEFAULT, never force AdamW
        r = self.ev(adamw_facts(optimizer_requested="AdamW"))
        assert r["verdict"] == "ADAMW_AMP_FAIL"
        assert "force" in r["reason"]

    def test_amp_false_rejected(self):
        r = self.ev(adamw_facts(amp_resolved=False))
        assert r["verdict"] == "ADAMW_AMP_FAIL" and "AMP" in r["reason"]

    def test_amp_pass_but_autocast_never_active_rejected(self):
        r = self.ev(adamw_facts(autocast_forward_on=0))
        assert r["verdict"] == "ADAMW_AMP_FAIL"
        assert "autocast never active" in r["reason"]

    def test_autocast_active_no_low_precision_evidence_inconclusive(self):
        r = self.ev(adamw_facts(low_precision_op_samples=0))
        assert r["verdict"] == "ADAMW_AMP_INCONCLUSIVE"
        assert "lower-precision" in r["reason"]

    def test_scaler_active_no_real_updates_rejected(self):
        # every step skipped by the fused inf-guard: python-level calls exist
        # but zero confirmed parameter updates
        r = self.ev(adamw_facts(optimizer_steps_underlying=11,
                                confirmed_update_events=0,
                                scaler_step_attempts=11))
        assert r["verdict"] == "ADAMW_AMP_FAIL"
        assert "every step skipped" in r["reason"]

    def test_missing_step_evidence_rejected(self):
        r = self.ev(adamw_facts(optimizer_steps_underlying=0,
                                confirmed_update_events=0,
                                scaler_step_attempts=0,
                                gradscaler_present=False))
        assert r["verdict"] == "ADAMW_AMP_FAIL"
        assert "missing optimizer step evidence" in r["reason"]

    def test_missing_confirmed_update_evidence_rejected(self):
        # wrapper-call counts alone prove nothing (mission A12)
        r = self.ev(adamw_facts(confirmed_update_events=None))
        assert r["verdict"] == "ADAMW_AMP_FAIL"
        assert "confirmed-update evidence" in r["reason"]

    def test_fewer_than_three_updates_rejected(self):
        r = self.ev(adamw_facts(confirmed_update_events=2))
        assert r["verdict"] == "ADAMW_AMP_FAIL"
        assert "insufficient optimizer updates" in r["reason"]

    def test_nonfinite_grads_at_confirmed_update_rejected(self):
        r = self.ev(adamw_facts(grads_finite_at_confirmed_updates=False))
        assert r["verdict"] == "ADAMW_AMP_FAIL"
        assert "nonfinite" in r["reason"]

    def test_no_parameter_changes_rejected(self):
        r = self.ev(adamw_facts(
            raw_trainer_model_delta={"tensors_changed_beyond_1e-9": 0,
                                     "all_finite": True}))
        assert r["verdict"] == "ADAMW_AMP_FAIL"

    def test_only_batchnorm_buffer_changes_rejected(self):
        r = self.ev(adamw_facts(
            raw_trainer_model_delta={"tensors_changed_beyond_1e-9": 0,
                                     "all_finite": True},
            buffer_delta={"tensors_changed_beyond_1e-9": 40}))
        assert r["verdict"] == "ADAMW_AMP_FAIL"
        assert "buffer changes" in r["reason"]

    def test_nonfinite_gradients_in_one_group_rejected(self):
        # the FAIL key is finite-at-CONFIRMED-updates; skipped-step nonfinite
        # grads (grads_finite_all_steps=False) are GradScaler working correctly
        r = self.ev(adamw_facts(grads_finite_all_steps=False,
                                grads_finite_at_confirmed_updates=False))
        assert r["verdict"] == "ADAMW_AMP_FAIL"
        assert "nonfinite" in r["reason"]

    def test_nonfinite_parameter_deltas_rejected(self):
        r = self.ev(adamw_facts(
            raw_trainer_model_delta={"tensors_changed_beyond_1e-9": 350,
                                     "all_finite": False}))
        assert r["verdict"] == "ADAMW_AMP_FAIL" and "nonfinite parameter" in r["reason"]

    def test_synthetic_gpu_evidence_rejected(self):
        r = self.ev(adamw_facts(harness_fixture=True))
        assert r["verdict"] == "ADAMW_AMP_FAIL" and "synthetic" in r["reason"]
        r2 = self.ev(adamw_facts(gpu_name=None))
        assert r2["verdict"] == "ADAMW_AMP_FAIL" and "synthetic" in r2["reason"]

    def test_training_not_completed_rejected(self):
        r = self.ev(adamw_facts(training_completed=False))
        assert r["verdict"] == "ADAMW_AMP_FAIL" and "complete" in r["reason"]

    def test_harness_does_not_force_optimizer_or_nbs(self):
        src = (SCRIPTS / "audit_adamw_amp.py").read_text(encoding="utf-8")
        assert 'optimizer="auto"' in src
        train_kwargs_block = src.split("train_kwargs = dict(")[1].split(")")[0]
        assert "AdamW" not in train_kwargs_block  # never force the optimizer
        assert "nbs" not in train_kwargs_block  # normal nbs behaviour retained

    def test_step_wrappers_save_and_call_same_bound_name(self):
        # attempt-1 regression: the scaler wrapper saved `orig_scaler` but
        # called `orig_scaler_step` — NameError at the first scaler.step.
        # The unified harness wraps only opt.step; the wrapper must call the
        # exact name it saved.
        src = (SCRIPTS / "audit_adamw_amp.py").read_text(encoding="utf-8")
        assert "orig = opt.step" in src
        assert "r = orig(*a, **kw)" in src
        assert "orig_scaler_step" not in src


# =============================================================================
# R22A.2 Part B — Windows workers=8 acceptance contract (CPU-only)
# =============================================================================
_worker_fixture_seq = {"n": 0}


def worker_run(**over):
    _worker_fixture_seq["n"] += 1
    n = _worker_fixture_seq["n"]
    r = {
        "gpu_name": "AMD Radeon RX 7900 XTX", "harness_fixture": False,
        "run_id": f"FIXTURE-R{n:03d}",
        "started_utc": f"2026-11-16T{10 + n // 60:02d}:{n % 60:02d}:00+00:00",
        "requested_workers": 8, "resolved_num_workers": 8,
        "distinct_worker_identities": 13, "worker_identities": [
            {"identity": f"{9000 + k}@1234.5", "pid": 9000 + k,
             "create_time": 1234.5, "first_seen": 1.0 + k * 0.1,
             "last_seen": 40.0, "sightings": 30 + k}
            for k in range(13)],
        "peak_concurrent_workers": 13,
        "monitor_health": {
            "monitoring_started": True, "monitoring_completed": True,
            "thread_alive_at_shutdown": False, "unexpected_exception_count": 0,
            "observation_samples": 40, "first_observation": "2026-11-16T10:00:00+00:00",
            "last_observation": "2026-11-16T10:00:41+00:00",
        },
        "exit_code": 0, "log_text": "STABILITY_CHILD_DONE 42.1s",
        "orphan_workers_alive": 0, "lingering_after_parent_exit": [],
        "training_completed": True,
        "checkpoint_exists": True, "checkpoint_path": "run/weights/last.pt",
        "cache_class": "warm(shared-isolated-USERPROFILE)",
        "cache_expectation": "warm", "home_dir": "C:/r22a2/cache/warm-home",
        "matrix": "warm", "run": 1, "child_has_main_guard": True,
        "torch": "2.15.0+gitf6cd88cb.devrocm10.3.0.dev0-test",
        "log_sha256": f"fixture-sha-{n:04d}",
    }
    r.update(over)
    return r


def worker_matrix(runs, **over):
    m = {"runs": runs, "harness_fixture": False,
         "child_has_main_guard": True,
         "gpu_name": "AMD Radeon RX 7900 XTX"}
    m.update(over)
    return m


def full_matrix_runs(n_warm=3, **over_per_run):
    """The exact physical R22A.2 shape: 2 COLD (distinct fresh homes) +
    1 CACHE_PRIMING (first use of the shared warm home) + n_warm pre-warmed."""
    runs = [worker_run(run=i, matrix="cold", cache_expectation="cold",
                       home_dir=f"C:/h/cold{i}",
                       cache_class="cold(fresh-USERPROFILE)")
            for i in (1, 2)]
    runs.append(worker_run(run=1, matrix="warm", cache_expectation="warm",
                           home_dir="C:/h/warm", duration_s=119.1, **over_per_run))
    runs += [worker_run(run=i, matrix="warm", cache_expectation="warm",
                        home_dir="C:/h/warm", **over_per_run)
             for i in range(2, 2 + n_warm)]
    return runs


class TestWorkersContract:
    rs = load_module("run_stability")

    def test_requested8_effective8_observed_accepted(self):
        r = self.rs.evaluate_single_run(worker_run())
        assert r["verdict"] == "PASS", r

    def test_effective4_rejected(self):
        r = self.rs.evaluate_single_run(worker_run(resolved_num_workers=4))
        assert r["verdict"] == "FAIL"
        assert r["classification"] == "WORKER_COUNT_NOT_MET"

    def test_effective8_no_activity_inconclusive(self):
        r = self.rs.evaluate_single_run(
            worker_run(distinct_worker_identities=0, worker_identities=[],
                       peak_concurrent_workers=None,
                       concurrency_lower_bound_derived=None))
        assert r["verdict"] == "INCONCLUSIVE"
        assert r["classification"] == "NO_WORKER_PID_EVIDENCE"

    def test_peak4_of_8_is_worker_count_not_met(self):
        r = self.rs.evaluate_single_run(worker_run(peak_concurrent_workers=4))
        assert r["verdict"] == "FAIL"
        assert r["classification"] == "WORKER_COUNT_NOT_MET"

    def test_missing_resolved_workers_evidence_rejected(self):
        r = self.rs.evaluate_single_run(worker_run(resolved_num_workers=None))
        assert r["verdict"] == "FAIL"
        assert r["classification"] == "MISSING_RESOLVED_WORKERS_EVIDENCE"

    def test_orphaned_workers_fail(self):
        r = self.rs.evaluate_single_run(worker_run(orphan_workers_alive=2))
        assert r["verdict"] == "FAIL"
        assert r["classification"] == "WORKER_SHUTDOWN_FAILURE"

    def test_child_crash_after_complete_fails(self):
        r = self.rs.evaluate_single_run(worker_run(exit_code=1))
        assert r["verdict"] == "FAIL"
        assert r["classification"] == "WORKER_CRASH_AFTER_COMPLETE"

    def test_child_crash_without_complete_marker_fails(self):
        r = self.rs.evaluate_single_run(
            worker_run(exit_code=1, log_text="RuntimeError: boom"))
        assert r["verdict"] == "FAIL"

    def test_timeout_run_fails(self):
        r = self.rs.evaluate_single_run(worker_run(exit_code=124))
        assert r["verdict"] == "FAIL"
        assert r["classification"] == "DATALOADER_TIMEOUT"

    def test_synthetic_worker_evidence_rejected(self):
        r = self.rs.evaluate_single_run(worker_run(harness_fixture=True))
        assert r["verdict"] == "FAIL" and "SYNTHETIC" in r["classification"]
        r2 = self.rs.evaluate_single_run(worker_run(gpu_name=None))
        assert r2["verdict"] == "FAIL"

    def test_five_pass_runs_pass_matrix(self):
        # the FULL exact shape: 2 COLD + 1 CACHE_PRIMING + 3 WARM
        r = self.rs.evaluate_workers_matrix(worker_matrix(full_matrix_runs()))
        assert r["verdict"] == "WORKERS8_SHORT_RELIABILITY_PASS", r
        assert r["roles"] == ["cold", "cold", "cache_priming", "warm", "warm", "warm"]

    def test_frozen_five_run_matrix_is_no_go_under_strict_contract(self):
        # P0-D honest reclassification: the ORIGINAL frozen matrix was
        # 2 COLD + 1 CACHE_PRIMING + 2 WARM (only 2 pre-warmed runs) — it can
        # no longer satisfy the strict 3-pre-warmed contract by itself
        r = self.rs.evaluate_workers_matrix(worker_matrix(full_matrix_runs(n_warm=2)))
        assert r["verdict"] == "NO_GO"
        assert "qualifying pre-warmed" in r["reason"]
        assert r["roles"] == ["cold", "cold", "cache_priming", "warm", "warm"]

    def test_single_successful_run_cannot_satisfy_matrix(self):
        r = self.rs.evaluate_workers_matrix(worker_matrix([worker_run()]))
        assert r["verdict"] == "NO_GO" and "matrix size" in r["reason"]

    def test_missing_warm_run_is_no_go_even_if_all_pass(self):
        runs = full_matrix_runs(n_warm=2)
        assert all(self.rs.evaluate_single_run(x)["verdict"] == "PASS" for x in runs)
        r = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert r["verdict"] == "NO_GO" and "matrix size" in r["reason"]

    def test_one_timeout_is_no_go(self):
        runs = full_matrix_runs()
        runs[4] = worker_run(run=3, matrix="warm", cache_expectation="warm",
                             home_dir="C:/h/warm", exit_code=124)
        r = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert r["verdict"] == "NO_GO" and "timed out" in r["reason"]

    def test_five_of_six_pass_is_no_go(self):
        runs = full_matrix_runs()
        runs[5] = worker_run(run=4, matrix="warm", cache_expectation="warm",
                             home_dir="C:/h/warm", exit_code=1)
        r = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert r["verdict"] == "NO_GO" and "5/6" in r["reason"]

    def test_exit0_but_orphans_is_no_go(self):
        runs = full_matrix_runs()
        runs[0] = worker_run(run=1, matrix="cold", cache_expectation="cold",
                             home_dir="C:/h/cold1", orphan_workers_alive=3)
        r = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert r["verdict"] == "NO_GO"

    def test_missing_child_main_guard_is_no_go(self):
        r = self.rs.evaluate_workers_matrix(
            worker_matrix(full_matrix_runs(), child_has_main_guard=False))
        assert r["verdict"] == "NO_GO" and "__main__ guard" in r["reason"]

    def test_duplicate_run_identity_rejected(self):
        runs = full_matrix_runs()
        runs[5] = dict(runs[4], log_sha256=runs[3]["log_sha256"])  # dup log
        r = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert r["verdict"] == "NO_GO" and "duplicate" in r["reason"]
        runs2 = full_matrix_runs()
        runs2[5] = dict(runs2[4], run=runs2[3]["run"], matrix=runs2[3]["matrix"],
                        log_sha256="x-unique")
        r2 = self.rs.evaluate_workers_matrix(worker_matrix(runs2))
        assert r2["verdict"] == "NO_GO" and "duplicate run identities" in r2["reason"]

    def test_cold_runs_sharing_home_rejected(self):
        runs = full_matrix_runs()
        runs[1] = worker_run(run=2, matrix="cold", cache_expectation="cold",
                             home_dir="C:/h/cold1",
                             cache_class="cold(fresh-USERPROFILE)")
        r = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert r["verdict"] == "NO_GO" and "DISTINCT fresh cache home" in r["reason"]

    def test_warm_runs_with_different_homes_rejected(self):
        runs = full_matrix_runs()
        # a 3rd qualifying warm run that drifted onto ANOTHER home (explicit
        # pre-existed flag keeps counts valid so the SHARED-home rule fires)
        runs[5] = worker_run(run=4, matrix="warm", cache_expectation="warm",
                             home_dir="C:/h/other", home_pre_existed=True)
        r = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert r["verdict"] == "NO_GO" and "SHARE one retained cache home" in r["reason"]

    def test_two_priming_runs_rejected(self):
        runs = full_matrix_runs()
        # a second run CLAIMING first use of the already-primed shared home
        runs.append(worker_run(run=5, matrix="warm", cache_expectation="warm",
                               home_dir="C:/h/warm", home_pre_existed=False))
        r = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert r["verdict"] == "NO_GO" and "primed exactly once" in r["reason"]

    def test_synthetic_matrix_rejected(self):
        r = self.rs.evaluate_workers_matrix(worker_matrix(full_matrix_runs(),
                                                          harness_fixture=True))
        assert r["verdict"] == "NO_GO" and "synthetic" in r["reason"]

    # --- cache role derivation (P0-D) ---------------------------------------
    def test_assign_cache_roles_order_based(self):
        roled = self.rs.assign_cache_roles([
            worker_run(run=1, matrix="cold", cache_expectation="cold", home_dir="C:/c1"),
            worker_run(run=1, matrix="warm", cache_expectation="warm", home_dir="C:/w"),
            worker_run(run=2, matrix="warm", cache_expectation="warm", home_dir="C:/w"),
        ])
        assert [r["cache_role"] for r in roled] == ["cold", "cache_priming", "warm"]

    def test_assign_cache_roles_home_pre_existed_wins(self):
        roled = self.rs.assign_cache_roles([
            worker_run(run=1, cache_expectation="warm", home_dir="C:/w",
                       home_pre_existed=True),
        ])
        assert roled[0]["cache_role"] == "warm"

    # --- P0-C: anomaly gate on exit-0 paths ----------------------------------
    def test_exit0_fatal_kernel_error_is_no_go(self):
        r = self.rs.evaluate_single_run(worker_run(
            exit_code=0, log_text="train ok\nhipErrorInvalidKernelFile while loading\n"
                                  "STABILITY_CHILD_DONE 10.0s"))
        assert r["verdict"] == "FAIL"
        assert r["classification"] == "HIP_KERNEL_IMAGE_FAILURE"
        assert any(not c["ok"] for c in r["checks"]
                   if c["check"] == "no_fatal_anomaly_signatures")

    def test_exit0_worker_crash_evidence_is_no_go(self):
        r = self.rs.evaluate_single_run(worker_run(
            exit_code=0,
            log_text="RuntimeError: DataLoader worker (pid 1234) exited unexpectedly\n"
                     "STABILITY_CHILD_DONE 10.0s"))
        assert r["verdict"] == "FAIL"
        assert r["classification"] == "WORKER_CRASH"
        assert "DataLoader worker (pid 1234)" in r["anomaly_evidence"]["fatal"][0]["raw_line"]

    def test_exit0_benign_documented_warning_classified_not_discarded(self):
        benign_line = ("MIOpen: Error [EvaluateInvokers] DESKTOP:.../solver_finders.cpp:545: "
                       "Invalid elapsed time detected in EvaluateInvokers, "
                       "failed condition: elapsed <= 0")
        r = self.rs.evaluate_single_run(worker_run(
            exit_code=0, log_text=f"training\n{benign_line}\nSTABILITY_CHILD_DONE 119.1s"))
        assert r["verdict"] == "PASS"
        assert r["anomaly_evidence"]["fatal"] == []
        b = r["anomaly_evidence"]["benign"][0]
        assert b["classification"] == "MIOPEN_FIND_TIMING_DIAGNOSTIC"
        assert "cache-priming" in b["rationale"]
        assert "EvaluateInvokers" in b["raw_line"]  # raw preserved verbatim

    def test_benign_plus_fatal_fatal_wins(self):
        r = self.rs.evaluate_single_run(worker_run(
            exit_code=0,
            log_text="MIOpen: Error [EvaluateInvokers] ... Invalid elapsed time\n"
                     "miopenStatusUnknownError\nSTABILITY_CHILD_DONE 5.0s"))
        assert r["verdict"] == "FAIL"
        assert r["classification"] == "MIOPEN_RUNTIME_KERNEL"
        assert len(r["anomaly_evidence"]["benign"]) == 1  # benign still preserved

    def test_clean_exit0_log_has_no_anomaly_evidence_fatals(self):
        r = self.rs.evaluate_single_run(worker_run())
        assert r["verdict"] == "PASS"
        assert r["anomaly_evidence"]["fatal"] == []

    # --- Windows spawn safety of the GENERATED child script -------------------
    def test_generated_child_has_main_guard_and_freeze_support(self):
        src = self.rs.CHILD.format(device=-1, project="p", name="n", seed=1,
                                   workers=8, data="coco128.yaml", batch=16,
                                   imgsz=256, extra="", facts_path="f.json",
                                   run_id="T", batch_arg="16", imgsz_arg="256")
        assert self.rs.child_has_main_guard(src)
        compile(src, "child.py", "exec")

    def test_default_workers0_child_matches_historical_shape(self):
        src = self.rs.CHILD.format(device=-1, project="p", name="n", seed=1,
                                   workers=0, data="coco8.yaml", batch=None,
                                   imgsz=None, extra="", facts_path="f.json",
                                   run_id="T", batch_arg="None",
                                   imgsz_arg="None")
        compile(src, "child0.py", "exec")
        assert self.rs.child_has_main_guard(src)
        assert "workers=0" in src
        assert "coco8.yaml" in src  # historical default dataset retained

    def test_worker_failure_families_present(self):
        src = (SCRIPTS / "run_stability.py").read_text(encoding="utf-8")
        for fam in ("WORKER_SPAWN_FAILURE", "WORKER_INIT_FAILURE", "WORKER_CRASH",
                    "WORKER_SHUTDOWN_FAILURE", "DATALOADER_DEADLOCK",
                    "DATALOADER_TIMEOUT", "GPU_OOM"):
            assert fam in src, fam

# =============================================================================
# R22A.4 — unified harness, monitor failure semantics, stored-verdict spoofing,
# schema adapters, dual-arch acceptance (CPU-only, mission §4/§5/§6/§10/§14)
# =============================================================================

WORKER_IDS_GFX1151 = [
    {"identity": f"{7000 + k}@99.0", "pid": 7000 + k, "create_time": 99.0,
     "ppid": 6000, "name": "python.exe", "first_seen": 1.0 + k * 0.2,
     "last_seen": 120.0, "sightings": 40 + k}
    for k in range(13)
]


def worker_run_1151(**over):
    """gfx1151-shaped fixture mirroring the frozen R22A3 receipts: no
    monitor-health state (historical harness) but independent lifecycle
    corroboration, derived concurrency bound, per-run device identity."""
    _worker_fixture_seq["n"] += 1
    n = _worker_fixture_seq["n"]
    r = {
        "gpu_name": "AMD Radeon(TM) 8060S Graphics", "harness_fixture": False,
        "run_id": f"R22A3-FIX-R{n}", "started_utc": f"2026-11-16T11:{n % 60:02d}:00+00:00",
        "requested_workers": 8, "resolved_num_workers": 8,
        "distinct_worker_identities": 13, "worker_identities": WORKER_IDS_GFX1151,
        "concurrency_lower_bound_derived": 13, "peak_concurrent_workers": None,
        "monitor_health": None,
        "independent_lifecycle_corroboration": {
            "source": "FIXTURE_PROCESS_LIFECYCLE.json", "distinct_identities": 13,
            "total_sightings": 900, "min_per_identity_sightings": 30,
            "all_have_create_time": True, "all_have_ppid": True},
        "exit_code": 0, "log_text": "STABILITY_CHILD_DONE 61.0s",
        "orphan_workers_alive": 0, "lingering_after_parent_exit": [],
        "training_completed": True, "val_completed": True,
        "checkpoint_exists": True, "checkpoint_path": "run/weights/last.pt",
        "cache_class": "warm(retained isolated home)", "cache_expectation": "warm",
        "home_dir": "C:/r22a3/scratch/warm-home-fixture",
        "matrix": "warm", "run": 1, "child_has_main_guard": True,
        "torch": "2.15.0+gitf6cd88cb.devrocm10.3.0.dev0-test",
        "log_sha256": f"fixture-sha-1151-{n:04d}",
    }
    r.update(over)
    return r


def full_matrix_runs_1151():
    """The derived honest gfx1151 shape: 2 COLD + 1 CACHE_PRIMING + 2 WARM
    (+ optional additional)."""
    runs = [worker_run_1151(run=i, matrix="cold", cache_expectation="cold",
                            home_dir=f"C:/r22a3/h/cold{i}",
                            cache_class="cold(fresh-USERPROFILE)")
            for i in (1, 2)]
    runs.append(worker_run_1151(run=1, matrix="warm", cache_expectation="warm",
                                home_dir="C:/r22a3/h/warm", duration_s=198.4))
    runs += [worker_run_1151(run=i, matrix="warm", cache_expectation="warm",
                             home_dir="C:/r22a3/h/warm")
             for i in (2, 3)]
    return runs


def adamw_flat_facts(**over):
    f = {
        "gpu_name": "AMD Radeon RX 7900 XTX", "gfx_target": "gfx1100",
        "harness_fixture": False, "runtime_class": "OFFICIAL_CANDIDATE",
        "optimizer_requested": "auto", "optimizer_class": "AdamW",
        "optimizer_resolved_in_args": "AdamW",
        "optimizer_resolution_note": "optimizer=auto resolved to AdamW",
        "amp_resolved": True, "autocast_forward_on": 48,
        "autocast_forward_samples": 48, "low_precision_op_samples": 48,
        "low_precision_dtype": "float16",
        "optimizer_steps_underlying": 11, "scaler_step_attempts": 11,
        "confirmed_update_events": 6, "found_inf_events": 5,
        "per_step_events": [{"param_checksum_changed": True, "step": i}
                            for i in range(11)],
        "gradscaler_present": True, "grads_finite_at_confirmed_updates": True,
        "gradscaler": {"present": True, "backoff_events_observed": 5,
                       "scale_backoff_events_observed": 5},
        "raw_trainer_model_delta": {"tensors_changed_beyond_1e-9": 366,
                                    "total_tensors": 366, "all_finite": True},
        "buffer_delta": {"tensors_changed_beyond_1e-9": 40},
        "training_completed": True,
    }
    f.update(over)
    return f


def adamw_nested_facts(**over):
    """R22A3-nested-schema fixture (7 effective / 4 found_inf — the real
    gfx1151 observation, which must stay acceptable alongside gfx1100's 6/5)."""
    per_step = []
    for i in range(11):
        eff = i < 7
        per_step.append({"invoked": True, "found_inf_any": (not eff and i >= 7),
                         "sentinel_max_abs_delta": 0.01 if eff else 0.0,
                         "grads_all_finite": eff})
    ev = {
        "gpu_name": "AMD Radeon(TM) 8060S Graphics", "gfx_target": "gfx1151",
        "runtime_class": "OFFICIAL_CANDIDATE",
        "optim": {"requested": "auto", "resolved_in_args_after_build": "AdamW",
                  "actual_class": "AdamW"},
        "amp": {"trainer_amp_resolved": True,
                "autocast_forward_samples": {"sampled": 48, "enabled": 48},
                "stem_conv_output_dtypes_observed": {"float16": 48}},
        "optimizer_steps": {
            "attempted_invocations": 11,
            "effective_updates_sentinel_proven": 7,
            "per_step": per_step,
            "skipped_found_inf_flagged": 4,
            "grads_finite_on_stepped_updates": True},
        "gradscaler": {"present": True, "scale_history_len": 11,
                       "backoff_events_observed": 4},
        "raw_trainer_model_delta": {"tensors_changed_beyond_1e_9": 366,
                                    "total_tensors": 366, "all_finite": True},
        "batches_completed": 24, "exit_code": 0,
    }
    ev.update(over)
    return ev


class TestAdamWAmpVerdict:
    """Unified contract exercised through the R22A.3-nested adapter."""
    a = load_module("audit_adamw_amp")

    def test_full_good_nested_facts_pass(self):
        v = self.a.compute_adamw_verdict(adamw_nested_facts(), 3)
        assert v["verdict"] == "ADAMW_AMP_MULTISTEP_PASS", v

    def test_auto_resolving_to_sgd_fails(self):
        ev = adamw_nested_facts()
        ev["optim"] = {"requested": "auto", "resolved_in_args_after_build": "SGD",
                       "actual_class": "SGD"}
        v = self.a.compute_adamw_verdict(ev, 3)
        assert v["verdict"] == "ADAMW_AMP_FAIL"

    def test_manual_adamw_is_not_auto_selection(self):
        ev = adamw_nested_facts()
        ev["optim"] = {"requested": "AdamW", "resolved_in_args_after_build": "AdamW",
                       "actual_class": "AdamW"}
        v = self.a.compute_adamw_verdict(ev, 3)
        assert v["verdict"] == "ADAMW_AMP_FAIL"  # harness forced the optimizer

    def test_amp_false_fails(self):
        ev = adamw_nested_facts()
        ev["amp"] = dict(ev["amp"], trainer_amp_resolved=False)
        v = self.a.compute_adamw_verdict(ev, 3)
        assert v["verdict"] == "ADAMW_AMP_FAIL"

    def test_autocast_without_observed_low_precision_is_inconclusive(self):
        ev = adamw_nested_facts()
        ev["amp"] = dict(ev["amp"], stem_conv_output_dtypes_observed={"float32": 48})
        v = self.a.compute_adamw_verdict(ev, 3)
        assert v["verdict"] == "ADAMW_AMP_INCONCLUSIVE"

    def test_scaler_present_without_effective_updates_fails(self):
        ev = adamw_nested_facts()
        ev["optimizer_steps"] = dict(ev["optimizer_steps"],
                                     effective_updates_sentinel_proven=0)
        v = self.a.compute_adamw_verdict(ev, 3)
        assert v["verdict"] == "ADAMW_AMP_FAIL"

    def test_missing_parameter_delta_fails(self):
        ev = adamw_nested_facts()
        ev["raw_trainer_model_delta"] = {"tensors_changed_beyond_1e_9": 0,
                                         "total_tensors": 366, "all_finite": True}
        v = self.a.compute_adamw_verdict(ev, 3)
        assert v["verdict"] == "ADAMW_AMP_FAIL"

    def test_nonfinite_parameter_deltas_fail(self):
        ev = adamw_nested_facts()
        ev["raw_trainer_model_delta"] = {"tensors_changed_beyond_1e_9": 366,
                                         "total_tensors": 366, "all_finite": False}
        v = self.a.compute_adamw_verdict(ev, 3)
        assert v["verdict"] == "ADAMW_AMP_FAIL"

    def test_min_updates_threshold_enforced(self):
        v = self.a.compute_adamw_verdict(adamw_nested_facts(), 8)
        assert v["verdict"] == "ADAMW_AMP_FAIL"  # only 7 effective

    def test_empty_facts_fail_closed(self):
        v = self.a.compute_adamw_verdict({}, 3)
        assert v["verdict"] in ("ADAMW_AMP_FAIL", "REJECTED")

    def test_inconsistent_step_accounting_fails(self):
        # forged: 11 effective updates with 4 found_inf skips among 11 steps
        ev = adamw_nested_facts()
        ev["optimizer_steps"] = dict(ev["optimizer_steps"],
                                     effective_updates_sentinel_proven=11)
        v = self.a.compute_adamw_verdict(ev, 3)
        assert v["verdict"] == "ADAMW_AMP_FAIL"
        assert "inconsistent step accounting" in v["reason"]

    def test_architecture_dependent_counts_both_accepted(self):
        # gfx1100 6/5 and gfx1151 7/4 are BOTH factual observations — the
        # contract must not hardcode either number
        v1100 = self.a.evaluate_adamw_contract(adamw_flat_facts())
        v1151 = self.a.compute_adamw_verdict(adamw_nested_facts(), 3)
        assert v1100["verdict"] == v1151["verdict"] == "ADAMW_AMP_MULTISTEP_PASS"

    def test_synthetic_gpu_evidence_rejected_nested(self):
        ev = adamw_nested_facts(harness_fixture=True)
        v = self.a.compute_adamw_verdict(ev, 3)
        assert v["verdict"] == "ADAMW_AMP_FAIL"
        assert "synthetic" in v["reason"]

    def test_missing_per_step_series_fails(self):
        ev = adamw_nested_facts()
        ev["optimizer_steps"] = {k: v for k, v in ev["optimizer_steps"].items()
                                 if k != "per_step"}
        v = self.a.compute_adamw_verdict(ev, 3)
        assert v["verdict"] == "ADAMW_AMP_FAIL"


class TestWorkers8VerdictCompat:
    """R22A.3 compat shims now recompute from facts (stored status ignored)."""
    rs = load_module("run_stability")

    def test_requested8_effective4_fails(self):
        st, cls = self.rs.finalize_worker_run(worker_run(resolved_num_workers=4))
        assert (st, cls) == ("FAIL", "WORKER_COUNT_NOT_MET")

    def test_effective8_without_pid_evidence_is_inconclusive(self):
        st, cls = self.rs.finalize_worker_run(
            worker_run(distinct_worker_identities=0, worker_identities=[],
                       peak_concurrent_workers=None,
                       concurrency_lower_bound_derived=None))
        assert (st, cls) == ("INCONCLUSIVE", "NO_WORKER_PID_EVIDENCE")

    def test_partial_pid_evidence_is_inconclusive(self):
        st, cls = self.rs.finalize_worker_run(
            worker_run(distinct_worker_identities=5))
        assert (st, cls) == ("INCONCLUSIVE", "PARTIAL_WORKER_PID_EVIDENCE")

    def test_worker_orphaned_after_parent_fails(self):
        st, cls = self.rs.finalize_worker_run(
            worker_run(orphan_workers_alive=1))
        assert (st, cls) == ("FAIL", "WORKER_SHUTDOWN_FAILURE")

    def test_timeout_fails(self):
        st, cls = self.rs.finalize_worker_run(worker_run(exit_code=124))
        assert (st, cls) == ("FAIL", "DATALOADER_TIMEOUT")

    def test_missing_process_exit_code_fails(self):
        st, cls = self.rs.finalize_worker_run(worker_run(exit_code=None))
        assert (st, cls) == ("FAIL", "MISSING_PROCESS_EXIT_CODE")

    def test_stored_status_pass_is_ignored(self):
        r = worker_run(exit_code=1)  # facts say crash…
        r["status"] = "PASS"  # …stored verdict claims PASS
        st, cls = self.rs.finalize_worker_run(r)
        assert st == "FAIL"

    def test_overall_recomputes_from_facts_not_stored_status(self):
        runs = full_matrix_runs()
        for r in runs:
            r["status"] = "PASS"
        runs[2]["exit_code"] = 1  # forged: facts contradict the stored status
        v = self.rs.overall_workers8_verdict(runs, 2, 3)
        assert v["verdict"] == "NO_GO"

    def test_overall_five_clean_runs_pass(self):
        v = self.rs.overall_workers8_verdict(full_matrix_runs(), 2, 3)
        assert v["verdict"] == "WORKERS8_SHORT_RELIABILITY_PASS"

    def test_sixth_substitution_run_cannot_repair_matrix(self):
        # one warm run FAILED; a later passing run cannot erase the failure
        runs = full_matrix_runs(n_warm=2)
        runs[3]["exit_code"] = 1  # a qualifying warm run failed
        runs.append(worker_run(matrix="warm", run=9, cache_expectation="warm",
                               home_dir="C:/h/warm", sample_class="original"))
        v = self.rs.overall_workers8_verdict(runs, 2, 3)
        assert v["verdict"] == "NO_GO"


class TestChildSpawnSafety:
    rs = load_module("run_stability")

    def test_generated_child_is_spawn_safe(self):
        src = self.rs.CHILD.format(device=-1, project="p", name="n", seed=1,
                                   workers=8, data="coco128.yaml", batch=16,
                                   imgsz=256, extra=", batch=16",
                                   facts_path="f.json", run_id="T",
                                   batch_arg="16", imgsz_arg="256")
        ok, why = self.rs.child_spawn_safe(src)
        assert ok, why
        assert self.rs.child_has_main_guard(src)

    def test_child_without_main_guard_rejected(self):
        src = "m = YOLO('yolo26n.pt')\nm.train(data='coco8.yaml', epochs=1)"
        assert not self.rs.child_spawn_safe(src)[0]

    def test_guard_present_but_module_level_train_rejected(self):
        src = ("import multiprocessing\n"
               "m.train(data='coco8.yaml', epochs=1)\n"
               "if __name__ == '__main__':\n"
               "    multiprocessing.freeze_support()\n")
        assert not self.rs.child_spawn_safe(src)[0]


class TestMonitorFailureSemantics:
    """Mission §4 A–J: the monitor must never silently die and certify."""
    rs = load_module("run_stability")

    def _healthy(self, **over):
        h = {"monitoring_started": True, "monitoring_completed": True,
             "thread_alive_at_shutdown": False, "unexpected_exception_count": 0,
             "observation_samples": 50, "first_observation": "t0",
             "last_observation": "t1"}
        h.update(over)
        return h

    def test_exit_race_recorded_run_still_passes(self):
        r = worker_run(monitor_health=self._healthy(),
                       monitor_event_summary={self.rs.MONITOR_EXIT_RACE: 3})
        v = self.rs.evaluate_single_run(r)
        assert v["verdict"] == "PASS"
        assert any("exit-race" in c["detail"] for c in v["checks"])

    def test_internal_failure_without_corroboration_inconclusive(self):
        r = worker_run(monitor_health=self._healthy(unexpected_exception_count=1),
                       independent_lifecycle_corroboration=None)
        v = self.rs.evaluate_single_run(r)
        assert v["verdict"] == "INCONCLUSIVE"
        assert v["classification"] == "MONITOR_INTERNAL_FAILURE"

    def test_thread_died_incomplete_inconclusive(self):
        r = worker_run(monitor_health=self._healthy(monitoring_completed=False))
        v = self.rs.evaluate_single_run(r)
        assert v["verdict"] == "INCONCLUSIVE"

    def test_zero_samples_inconclusive(self):
        r = worker_run(monitor_health=self._healthy(observation_samples=0))
        v = self.rs.evaluate_single_run(r)
        assert v["verdict"] == "INCONCLUSIVE"

    def test_last_observation_missing_inconclusive(self):
        r = worker_run(monitor_health=self._healthy(last_observation=None))
        v = self.rs.evaluate_single_run(r)
        assert v["verdict"] == "INCONCLUSIVE"

    def test_thread_alive_after_bounded_shutdown_inconclusive(self):
        r = worker_run(monitor_health=self._healthy(thread_alive_at_shutdown=True))
        v = self.rs.evaluate_single_run(r)
        assert v["verdict"] == "INCONCLUSIVE"

    def test_unhealthy_monitor_with_independent_corroboration_passes_disclosed(self):
        r = worker_run(monitor_health=self._healthy(unexpected_exception_count=2),
                       independent_lifecycle_corroboration={
                           "source": "LIFE.json", "distinct_identities": 13,
                           "total_sightings": 900})
        v = self.rs.evaluate_single_run(r)
        assert v["verdict"] == "PASS"
        assert any("UNHEALTHY" in c["detail"] for c in v["checks"])

    def test_monitor_health_unrecorded_without_corroboration_inconclusive(self):
        r = worker_run(monitor_health=None,
                       independent_lifecycle_corroboration=None)
        v = self.rs.evaluate_single_run(r)
        assert v["verdict"] == "INCONCLUSIVE"
        assert v["classification"] == "MONITOR_HEALTH_UNRECORDED"

    def test_training_exit0_but_unhealthy_monitor_not_full_pass(self):
        r = worker_run(monitor_health=self._healthy(monitoring_completed=False))
        v = self.rs.evaluate_single_run(r)
        assert v["verdict"] != "PASS"

    def test_worker_thread_loop_survives_exceptions(self):
        import types
        mon = self.rs.WorkerMonitor.__new__(self.rs.WorkerMonitor)
        threading_t = __import__("threading")
        super(self.rs.WorkerMonitor, mon).__init__(daemon=True)
        mon.root_pid, mon.interval = 1, 0.01
        mon.stop_event = threading_t.Event()
        mon._psutil = types.SimpleNamespace(
            Process=lambda pid: (_ for _ in ()).throw(
                RuntimeError("boom")),
            NoSuchProcess=type("NoSuchProcess", (Exception,), {}),
            ZombieProcess=type("ZombieProcess", (Exception,), {}),
            AccessDenied=type("AccessDenied", (Exception,), {}))
        mon.backend = "psutil"
        mon.health = {"monitoring_started": False, "monitoring_completed": False,
                      "thread_alive_at_shutdown": None, "unexpected_exception_count": 0,
                      "observation_samples": 0, "first_observation": None,
                      "last_observation": None}
        mon.events, mon.identities, mon.peak_concurrent, mon.root_gone_seen = [], {}, 0, False
        mon.start()
        mon.stop_event.wait(0.2)
        stopped = mon.stop(timeout=5)
        assert stopped  # bounded shutdown
        assert mon.health["monitoring_completed"] is True  # loop cannot die silently
        assert mon.health["unexpected_exception_count"] > 0  # failure counted
        assert mon.health["observation_samples"] == 0  # no fabricated samples

    def test_pid_reuse_is_not_an_orphan(self):
        mon = self.rs.WorkerMonitor.__new__(self.rs.WorkerMonitor)
        mon._psutil = None
        mon.identities = {"7@100.0": {"identity": "7@100.0", "pid": 7,
                                      "create_time": 100.0}}
        import types
        fake = types.SimpleNamespace()
        fake.Process = lambda pid: types.SimpleNamespace(create_time=lambda: 999.0)
        fake.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
        mon._psutil = fake
        assert mon._identity_alive(mon.identities["7@100.0"]) is False


class TestStoredVerdictSpoofing:
    """Mission §5 adversarial fixtures 1–13 + §14 examples."""
    rs = load_module("run_stability")
    sa = load_module("supplemental_acceptance")

    def test_forged_overall_pass_with_failing_run_rejected(self):
        runs = full_matrix_runs()
        runs[2]["exit_code"] = 1
        m = {"runs": runs, "harness_fixture": False, "child_has_main_guard": True,
             "gpu_name": runs[0]["gpu_name"],
             "workers8_overall": {"verdict": "WORKERS8_SHORT_RELIABILITY_PASS"}}
        v = self.rs.evaluate_workers_matrix(m)
        assert v["verdict"] == "NO_GO"

    def test_forged_per_run_status_pass_rejected(self):
        runs = full_matrix_runs()
        runs[3]["exit_code"] = 1
        runs[3]["status"] = "PASS"
        v = self.rs.overall_workers8_verdict(runs, 2, 3)
        assert v["verdict"] == "NO_GO"

    def test_missing_run_is_no_go(self):
        runs = full_matrix_runs()[:-1]
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"

    def test_duplicate_run_ids_no_go(self):
        runs = full_matrix_runs()
        runs[4]["run_id"] = runs[3]["run_id"]
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"

    def test_wrong_worker_count_no_go(self):
        runs = full_matrix_runs()
        runs[1]["resolved_num_workers"] = 4
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"

    def test_no_actual_worker_pid_evidence_inconclusive(self):
        runs = full_matrix_runs()
        for r in runs:
            r["distinct_worker_identities"] = 0
            r["worker_identities"] = []
            r["peak_concurrent_workers"] = None
            r["concurrency_lower_bound_derived"] = None
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "INCONCLUSIVE"

    def test_fatal_log_anomaly_with_exit0_no_go(self):
        runs = full_matrix_runs()
        runs[2]["log_text"] = ("STABILITY_CHILD_DONE 41s\n"
                               "DataLoader worker (pid 123) exited unexpectedly")
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"

    def test_orphan_worker_no_go(self):
        runs = full_matrix_runs()
        runs[4]["orphan_workers_alive"] = 2
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"

    def test_monitor_crash_fails_closed(self):
        runs = full_matrix_runs()
        runs[0]["monitor_health"] = {
            "monitoring_started": True, "monitoring_completed": False,
            "thread_alive_at_shutdown": False, "unexpected_exception_count": 1,
            "observation_samples": 3, "first_observation": "t0",
            "last_observation": "t1"}
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "INCONCLUSIVE"

    def test_mislabelled_priming_as_warm_with_direct_evidence_rejected(self):
        runs = full_matrix_runs(n_warm=3)
        # the PRIMING run (chronological first use of the shared home) claims
        # home_pre_existed=true — direct evidence contradicting the derivation
        for r in runs:
            if r.get("matrix") == "warm" and r.get("run") == 1:
                r["home_pre_existed"] = True
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"
        assert "mislabels a cache_priming" in v["reason"]

    def test_wrong_cache_home_identity_rejected(self):
        runs = full_matrix_runs()
        runs[0]["home_dir"] = runs[3]["home_dir"]  # a cold run on the warm home
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"

    def test_synthetic_evidence_no_physical_pass(self):
        runs = full_matrix_runs()
        for r in runs:
            r["harness_fixture"] = True
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"

    def test_mixed_gpu_runtime_evidence_no_go(self):
        runs = full_matrix_runs()
        runs[2]["gpu_name"] = "AMD Radeon(TM) 8060S Graphics"
        runs[2]["torch"] = "2.99.0+other"
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"

    def test_additional_without_justification_no_go(self):
        runs = full_matrix_runs(n_warm=2)
        runs.append(worker_run(matrix="warm", run=9, home_dir="C:/h/warm",
                               cache_expectation="warm", home_pre_existed=True,
                               sample_class="additional", justification="  "))
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"

    def test_additional_on_fresh_home_no_go(self):
        runs = full_matrix_runs(n_warm=2)
        runs.append(worker_run(matrix="warm", run=9, home_dir="C:/h/other-home",
                               cache_expectation="warm", home_pre_existed=False,
                               sample_class="additional",
                               justification="probe"))
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"

    def test_two_priming_runs_no_go(self):
        runs = full_matrix_runs(n_warm=2)
        runs.append(worker_run(matrix="warm", run=9, home_dir="C:/h/warm2",
                               cache_expectation="warm"))  # second fresh home
        v = self.rs.evaluate_workers_matrix(worker_matrix(runs))
        assert v["verdict"] == "NO_GO"


class TestSchemaAdapters:
    a = load_module("audit_adamw_amp")

    def test_changed_tensors_accepts_both_spellings(self):
        assert self.a.changed_tensors({"tensors_changed_beyond_1e-9": 5}) == 5
        assert self.a.changed_tensors({"tensors_changed_beyond_1e_9": 6}) == 6
        assert self.a.changed_tensors({}) == 0
        assert self.a.changed_tensors("junk") == 0

    def test_r22a2_adapter_maps_flat_receipt(self):
        rec = {
            "gpu_name": "AMD Radeon RX 7900 XTX", "gfx_target": "gfx1100",
            "exit_code": 0,
            "optimizer": {"requested": "auto", "resolved_class": "AdamW",
                          "trainer_args_optimizer_after_resolution": "AdamW",
                          "resolution_note": "note"},
            "amp": {"resolved": True, "autocast_dtype_observed": "float16"},
            "training_counts": {"forward_autocast_on": 48, "forward_samples": 48,
                                "optimizer_steps_underlying": 11,
                                "scaler_step_attempts": 11,
                                "confirmed_update_events": 6,
                                "per_step_events": [{"step": 1}],
                                "grads_finite_at_confirmed_updates": True},
            "low_precision_evidence": {"samples_low_precision": 48},
            "gradscaler": {"present": True,
                           "scale_backoff_events_observed": 5},
            "raw_trainer_model_delta": {"tensors_changed_beyond_1e-9": 366,
                                        "total_tensors": 366,
                                        "all_finite": True},
            "buffer_delta": {"tensors_changed_beyond_1e-9": 40},
        }
        f = self.a.flat_facts_from_r22a2_record(rec)
        assert f["optimizer_requested"] == "auto"
        assert f["confirmed_update_events"] == 6
        assert f["low_precision_op_samples"] == 48
        v = self.a.evaluate_adamw_contract(f)
        assert v["verdict"] == "ADAMW_AMP_MULTISTEP_PASS", v

    def test_r22a3_adapter_maps_nested_receipt(self):
        f = self.a.flat_facts_from_r22a3_record(adamw_nested_facts())
        assert f["optimizer_requested"] == "auto"
        assert f["confirmed_update_events"] == 7
        assert f["found_inf_events"] == 4
        assert f["low_precision_op_samples"] == 48
        assert f["grads_finite_at_confirmed_updates"] is True

    def test_real_frozen_receipts_accepted_when_present(self):
        p1100 = REPO_ROOT / "evidence/raw/r22a2-gfx1100/R22A2_ADAMW_AMP.json"
        p1151 = REPO_ROOT / "evidence/raw/r22a3-gfx1151/R22A3_ADAMW_AMP.json"
        if not (p1100.is_file() and p1151.is_file()):
            pytest.skip("frozen receipts not present in this checkout")
        import json as _json
        sa = load_module("supplemental_acceptance")
        v1100 = sa.recompute_part_a(_json.loads(p1100.read_text(encoding="utf-8")))
        v1151 = sa.recompute_part_a(_json.loads(p1151.read_text(encoding="utf-8")))
        assert v1100["verdict"] == "ADAMW_AMP_MULTISTEP_PASS", v1100
        assert v1151["verdict"] == "ADAMW_AMP_MULTISTEP_PASS", v1151

    def test_optimizer_class_adamw_but_zero_updates_rejected(self):
        # mission §14: optimizer_class = AdamW with effective updates = 0
        v = self.a.evaluate_adamw_contract(
            adamw_flat_facts(confirmed_update_events=0))
        assert v["verdict"] == "ADAMW_AMP_FAIL"

    def test_harness_fixture_with_real_gpu_name_rejected(self):
        # mission §14: harness_fixture=true but gpu_name=RX 7900 XTX
        v = self.a.evaluate_adamw_contract(
            adamw_flat_facts(harness_fixture=True))
        assert v["verdict"] == "ADAMW_AMP_FAIL"
        assert "synthetic" in v["reason"]


class TestUnifiedAcceptance:
    sa = load_module("supplemental_acceptance")

    def _part_a_1151(self):
        return adamw_nested_facts(runtime_class="OFFICIAL_CANDIDATE")

    def test_full_matrix_with_additional_pass(self):
        runs = full_matrix_runs_1151()
        runs.append(worker_run_1151(
            run=6, matrix="warm", home_dir="C:/r22a3/h/warm",
            home_pre_existed=True, sample_class="additional",
            justification="strict contract requires 3 qualifying warm; frozen "
                          "matrix supplies 2"))
        c = self.sa.combined_verdict(self._part_a_1151(), runs, "gfx1151")
        assert c["verdict"] == "R22A3_GFX1151_SUPPLEMENTAL_PASS", c["reasons"]
        assert c["part_b_overall"]["derived_cache_roles"] == [
            "cold", "cold", "cache_priming", "warm", "warm", "warm"]

    def test_original_five_without_additional_no_go(self):
        runs = full_matrix_runs_1151()
        c = self.sa.combined_verdict(self._part_a_1151(), runs, "gfx1151")
        assert c["part_b_overall"]["verdict"] == "NO_GO"
        assert "qualifying" in c["part_b_overall"]["reason"]
        assert c["verdict"] == "PARTIAL_PASS"  # Part A still PASS

    def test_wrong_architecture_cannot_earn_verdict(self):
        runs = full_matrix_runs()  # gfx1100-shaped evidence
        a = adamw_flat_facts(runtime_class="OFFICIAL_CANDIDATE")
        c = self.sa.combined_verdict(a, runs, "gfx1151")
        assert c["verdict"] == "NO-GO"
        assert any("gfx_target" in r for r in c["reasons"])

    def test_engineering_reference_runtime_cannot_pass(self):
        a = adamw_nested_facts(runtime_class="ENGINEERING_REFERENCE")
        c = self.sa.combined_verdict(a, full_matrix_runs_1151(), "gfx1151")
        assert c["verdict"] != "R22A3_GFX1151_SUPPLEMENTAL_PASS"

    def test_synthetic_receipt_claiming_physical_gpu_rejected(self):
        a = adamw_nested_facts(gpu_name=None, runtime_class="OFFICIAL_CANDIDATE")
        c = self.sa.combined_verdict(a, full_matrix_runs_1151(), "gfx1151")
        assert c["verdict"] != "R22A3_GFX1151_SUPPLEMENTAL_PASS"

    def test_part_a_fail_gives_partial_or_no_go_with_reason(self):
        a = adamw_nested_facts(runtime_class="OFFICIAL_CANDIDATE")
        a["optim"] = {"requested": "auto", "resolved_in_args_after_build": "SGD",
                      "actual_class": "SGD"}
        c = self.sa.combined_verdict(a, full_matrix_runs_1151(), "gfx1151")
        assert c["verdict"] in ("PARTIAL_PASS", "NO-GO")
        assert c["reasons"]

    def test_stored_workers8_overall_never_consulted(self):
        runs = full_matrix_runs_1151()
        runs.append(worker_run_1151(
            run=6, matrix="warm", home_dir="C:/r22a3/h/warm",
            home_pre_existed=True, sample_class="additional",
            justification="strict contract requires 3 qualifying warm"))
        c = self.sa.combined_verdict(self._part_a_1151(), runs, "gfx1151")
        assert c["verdict"] == "R22A3_GFX1151_SUPPLEMENTAL_PASS"
        # now corrupt one fact — the stored serialized verdict cannot save it
        runs[2]["exit_code"] = 1
        runs[2]["workers8_overall"] = {"verdict": "WORKERS8_SHORT_RELIABILITY_PASS"}
        c2 = self.sa.combined_verdict(self._part_a_1151(), runs, "gfx1151")
        assert c2["part_b_overall"]["verdict"] == "NO_GO"


class TestDualArch:
    sa = load_module("supplemental_acceptance")

    def _full(self):
        runs1100 = full_matrix_runs(n_warm=2)
        runs1100.append(worker_run(matrix="warm", run=9, home_dir="C:/h/warm",
                                   home_pre_existed=True,
                                   sample_class="additional",
                                   justification="3rd qualifying warm"))
        a1100 = adamw_flat_facts(runtime_class="OFFICIAL_CANDIDATE")
        runs1151 = full_matrix_runs_1151()
        runs1151.append(worker_run_1151(
            run=6, matrix="warm", home_dir="C:/r22a3/h/warm",
            home_pre_existed=True, sample_class="additional",
            justification="3rd qualifying warm"))
        a1151 = adamw_nested_facts(runtime_class="OFFICIAL_CANDIDATE")
        return a1100, runs1100, a1151, runs1151

    def test_both_archs_validated(self):
        a1, r1, a2, r2 = self._full()
        rep = self.sa.dual_arch_acceptance(a1, r1, a2, r2, {}, {})
        assert rep["verdict"] == "R22_DEV_DUAL_ARCH_SUPPLEMENTAL_VALIDATED"
        f1, f2 = rep["gfx1100"]["facts"], rep["gfx1151"]["facts"]
        assert f1["effective_updates"] == 6 and f2["effective_updates"] == 7
        assert f1["nonfinite_skip_or_backoff"] == 5
        assert f2["nonfinite_skip_or_backoff"] == 4
        assert rep["gfx1100"]["physical_training_functional"] == \
            "PHYSICAL_TRAINING_FUNCTIONAL_PASS"
        assert rep["gfx1151"]["release_grade_evidence"] == \
            "RELEASE_GRADE_EVIDENCE_ACCEPTED"

    def test_one_arch_incomplete_blocks_dual(self):
        a1, r1, a2, r2 = self._full()
        r2 = r2[:-1]  # drop the additional warm — composition incomplete
        rep = self.sa.dual_arch_acceptance(a1, r1, a2, r2, {}, {})
        assert rep["verdict"] == "NO-GO"
        assert rep["gfx1151"]["release_grade_evidence"] == "NOT_ACCEPTED"

    def test_ceiling_never_official_stable(self):
        a1, r1, a2, r2 = self._full()
        rep = self.sa.dual_arch_acceptance(a1, r1, a2, r2, {}, {})
        assert "OFFICIAL_STABLE" not in rep["verdict"]
        assert "OFFICIAL_STABLE" not in rep["verdict_ceiling"].split("(")[0]
        assert "R23_RELEASE" not in rep["verdict"]

    def test_monitor_exception_disclosure_recorded_not_deleted(self):
        a1, r1, a2, r2 = self._full()
        disc = {"gfx1151": {"classified_as": "MONITOR_PROCESS_EXIT_RACE",
                            "affected_runs": ["R22A3-B-R1"]}}
        rep = self.sa.dual_arch_acceptance(a1, r1, a2, r2, {}, {}, disc)
        assert rep["monitor_exception_disclosures"]["gfx1151"]["classified_as"] \
            == "MONITOR_PROCESS_EXIT_RACE"


class TestEvidenceTools:
    sa = load_module("supplemental_acceptance")

    def test_concurrency_lower_bound_sweep(self):
        ids = [{"first_seen": 0.0, "last_seen": 10.0},
               {"first_seen": 1.0, "last_seen": 2.0},
               {"first_seen": 3.0, "last_seen": 4.0}]
        assert self.sa.concurrency_lower_bound(ids) == 2
        assert self.sa.concurrency_lower_bound([]) == 0

    def test_log_sha_verified_both_forms(self, tmp_path):
        import hashlib
        text = "line1\nline2\n"
        p = tmp_path / "child.log"
        p.write_bytes(text.replace("\n", "\r\n").encode())  # CRLF on disk
        lf_sha = hashlib.sha256(text.encode()).hexdigest()
        got, ver = self.sa.load_log_text(p, lf_sha)
        assert ver["sha_match"] is True
        assert ver["matched_form"] == "lf-normalized"
        assert got.replace("\r\n", "\n") == text

    def test_log_sha_mismatch_marked(self, tmp_path):
        p = tmp_path / "child.log"
        p.write_bytes(b"tampered\n")
        _, ver = self.sa.load_log_text(p, "0" * 64)
        assert ver["sha_match"] is False

    def test_missing_log_recorded(self, tmp_path):
        _, ver = self.sa.load_log_text(tmp_path / "nope.log", "x")
        assert ver["exists"] is False
        assert ver["sha_match"] is False
