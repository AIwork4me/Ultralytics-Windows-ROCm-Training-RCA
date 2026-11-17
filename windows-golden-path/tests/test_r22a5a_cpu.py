# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5A CPU-only adversarial contract tests (mission §10) — no GPU, no
network, no torch import.

Every mandatory negative behavior (list 1–20) is pinned here with a
deterministic fixture. The R22A.4.1 baseline suite (test_harness_cpu.py,
197 tests) stays untouched; this file is purely additive.

    python -m pytest windows-golden-path/tests/test_r22a5a_cpu.py -q
"""
from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
REPO_ROOT = SCRIPTS.parent.parent
R22A5A = REPO_ROOT / "scripts" / "r22a5a"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


lib = load_module("r22a5a_lib", R22A5A / "r22a5a_lib.py")
plan_mod = load_module("r22a5a_gen_install_plan", R22A5A / "gen_install_plan.py")
g9 = load_module("r22a5a_g9_preflight", R22A5A / "g9_preflight.py")
gp_lib = load_module("gp_lib_r22a5a", SCRIPTS / "gp_lib.py")


def row(channel="stable", package="rocm-sdk-libraries", version="10.2.0",
        cls="STABLE_CANDIDATE_PENDING_GPU_VALIDATION", tag="cp312",
        url=None):
    return {"channel": channel, "package": package, "version": version,
            "python_tag": tag, "wheel_filename": f"{package}-{version}-{tag}-cp313-win_amd64.whl"
            if package == "torch" else f"{package.replace('-', '_')}-{version}-py3-none-win_amd64.whl",
            "wheel_url": url or f"https://{channel if channel != 'multi-arch' else 'repo'}.repo.amd.com/rocm/whl-next/{package}/x.whl"
            if channel != "multi-arch" else f"https://repo.amd.com/rocm/whl-multi-arch/{package}/x.whl",
            "classification": cls}


def stable_fix_confirmed_rows(tag="cp312", gfx="gfx1100"):
    """A coherent fix-confirmed stable candidate set (positive fixture)."""
    rows = [
        row(package="rocm-sdk-libraries", version="10.2.0", tag="py3"),
        row(package="rocm-sdk-core", version="10.2.0", tag="py3"),
        row(package=f"rocm-sdk-device-{gfx}", version="10.2.0", tag="py3"),
        row(package="torch", version="2.15.0+rocm10.2.0", tag=tag),
        row(package="torchvision", version="0.29.2+rocm10.2.0", tag=tag),
    ]
    return rows


# --- 1/2/3. channel/index/metadata failure handling ---------------------------
class TestIndexFailureClassification:
    def test_missing_index_is_blocked_network_not_no_release(self):
        c = lib.classify_channel_artifact("stable", "rocm-sdk-libraries",
                                          "10.2.0", channel_reachable=False)
        assert c["classification"] == "BLOCKED_NETWORK"

    def test_partial_or_garbled_index_is_blocked_metadata(self):
        c = lib.classify_channel_artifact("stable", "rocm-sdk-libraries",
                                          None, channel_reachable=True,
                                          metadata_ok=False)
        assert c["classification"] == "BLOCKED_METADATA"

    def test_blocked_network_never_counts_as_fix_absent(self):
        # a network outage must NOT be misread as "no fix anywhere"
        c = lib.classify_channel_artifact("stable", "rocm-sdk-libraries",
                                          "10.2.0", channel_reachable=False)
        assert c["classification"] != "OFFICIAL_PRE_FIX"
        assert c["classification"] != "NO_NEW_ARTIFACT"


# --- 4/11/12. version/family/dependency coherence -----------------------------
class TestSetCoherence:
    def test_conflicting_rocm_generations_rejected(self):
        # cross-generation leftover rows are set-filtered to the sdk anchor
        # set (moving channels retain older builds) — the plan stays coherent
        rows = stable_fix_confirmed_rows() + [
            row(package="torch", version="2.12.0+rocm7.14.1", tag="cp312")]
        ev = plan_mod.evaluate_channel("stable", rows, "gfx1100", "cp312")
        assert ev["rocm_families"] == ["10"]
        assert ev["dep_coherent"] is True
        # …but WITHOUT a sdk anchor to disambiguate, two set versions for
        # one package+ABI remain an explicit conflict, never a silent pick
        rows2 = stable_fix_confirmed_rows()
        rows2 = [r for r in rows2 if r["package"] != "rocm-sdk-libraries"]
        rows2.append(row(package="torch", version="2.12.0+rocm7.14.1",
                         tag="cp312"))
        ev2 = plan_mod.evaluate_channel("stable", rows2, "gfx1100", "cp312")
        assert any("conflicting" in b and "torch" in b
                   for b in ev2["plan"]["blockers"])
        assert ev2["dep_coherent"] is False
        assert ev2["plan"]["emit_commands"] is False

    def test_missing_dependency_blocks_plan(self):
        rows = [r for r in stable_fix_confirmed_rows()
                if r["package"] != "torchvision"]
        ev = plan_mod.evaluate_channel("stable", rows, "gfx1100", "cp312")
        assert "torchvision" in ev["missing_packages"]
        assert ev["plan"]["emit_commands"] is False

    def test_gpu_blind_by_construction(self):
        # the qualification decision never receives GPU availability — an
        # unavailable GPU can never be turned into success by these tools
        import inspect
        for fn in (plan_mod.evaluate_channel, g9.qualify_package_inputs):
            sig = inspect.signature(fn)
            assert not any("gpu" in p or "cuda" in p for p in sig.parameters)


# --- 5/6/17. fake marker / old DLL behind new version / forged verdicts -------
class TestFakeFixEvidence:
    def test_higher_version_with_old_dll_is_pre_fix(self):
        # the rc 10.2.0rc2 precedent: NEW version, marker 0
        c = lib.classify_channel_artifact(
            "rc", "rocm-sdk-libraries", "10.2.0rc3",
            audit={"marker_miopen_initializer_list": 0,
                   "ancestry_status": "diverged", "ancestry_behind_by": 92})
        assert c["classification"] == "OFFICIAL_PRE_FIX"

    def test_fake_marker_with_diverged_ancestry_is_pre_fix(self):
        c = lib.classify_channel_artifact(
            "stable", "rocm-sdk-libraries", "10.2.0",
            audit={"marker_miopen_initializer_list": 2,
                   "ancestry_status": "diverged", "ancestry_behind_by": 5})
        assert c["classification"] == "OFFICIAL_PRE_FIX"

    def test_marker_without_ancestry_is_inconclusive(self):
        c = lib.classify_channel_artifact(
            "stable", "rocm-sdk-libraries", "10.2.0",
            audit={"marker_miopen_initializer_list": 2,
                   "ancestry_status": None, "ancestry_behind_by": None})
        assert c["classification"] == "BINARY_PROVENANCE_INCONCLUSIVE"

    def test_missing_build_identity_stays_inconclusive(self):
        c = lib.classify_channel_artifact(
            "stable", "rocm-sdk-libraries", "10.2.0",
            audit={"marker_miopen_initializer_list": 2})
        assert c["classification"] == "BINARY_PROVENANCE_INCONCLUSIVE"

    def test_forged_serialized_verdict_field_is_ignored(self):
        # a faked "verdict": "PASS"/"fix_present": True in the audit facts is
        # never consulted — only marker + ancestry decide
        c = lib.classify_channel_artifact(
            "stable", "rocm-sdk-libraries", "10.2.0",
            audit={"verdict": "PASS", "fix_present": True,
                   "marker_miopen_initializer_list": 0,
                   "ancestry_status": "diverged", "ancestry_behind_by": 92})
        assert c["classification"] == "OFFICIAL_PRE_FIX"

    def test_unaudited_new_artifact_is_pending(self):
        c = lib.classify_channel_artifact("stable", "rocm-sdk-libraries",
                                          "10.2.0", audit=None)
        assert c["classification"] == "NEW_ARTIFACT_PROVENANCE_PENDING"


# --- 7. hash identity ---------------------------------------------------------
class TestHashIdentity:
    def test_correctly_named_wheel_with_wrong_hash_rejected(self):
        # anchor (stable, rocm-sdk-libraries, 10.1.0) exists; a wheel claiming
        # the same version with a DIFFERENT sha must not inherit the verdict
        c = lib.classify_channel_artifact(
            "stable", "rocm-sdk-libraries", "10.1.0",
            wheel_sha256="0" * 64)
        assert c["classification"] in ("NEW_ARTIFACT_PROVENANCE_PENDING",
                                       "BINARY_PROVENANCE_INCONCLUSIVE")
        assert "wrong hash" in c["reason"] or "!=" in c["reason"]

    def test_anchor_sha_match_reuses_frozen_verdict(self):
        a = lib.FROZEN_CHANNEL_ANCHORS[("stable", "rocm-sdk-libraries", "10.1.0")]
        c = lib.classify_channel_artifact(
            "stable", "rocm-sdk-libraries", "10.1.0",
            wheel_sha256=a["wheel_sha256"])
        assert c["classification"] == "OFFICIAL_PRE_FIX"
        assert c["anchor"]["identity"] == "wheel_sha256"


# --- 8/9. platform / ABI confusion ---------------------------------------------
class TestPlatformAbi:
    def test_linux_wheel_cannot_qualify_as_windows(self):
        p = gp_lib.parse_wheel_filename(
            "torch-2.15.0+rocm10.2.0-cp312-cp312-linux_x86_64.whl")
        assert p["win_amd64"] is False

    def test_wrong_python_abi_blocks_plan(self):
        rows = stable_fix_confirmed_rows()
        # only torch/torchvision carry ABI tags; force them to cp39
        rows = [dict(r, python_tag="cp39") if r["package"] in ("torch",
                                                              "torchvision")
                else r for r in rows]
        ev = plan_mod.evaluate_channel("stable", rows, "gfx1100", "cp312")
        assert ev["abi_blocked"], "ABI mismatch must be an explicit blocker"
        assert ev["plan"]["emit_commands"] is False
        assert any("ABI" in b for b in ev["plan"]["blockers"])

    def test_matching_abi_emits_plan(self):
        ev = plan_mod.evaluate_channel("stable", stable_fix_confirmed_rows(),
                                       "gfx1100", "cp312")
        assert ev["plan"]["emit_commands"] is True
        assert ev["plan"]["tier"] == "OFFICIAL_STABLE"


# --- 10. device packages -------------------------------------------------------
class TestDevicePackages:
    def test_wrong_gfx_device_package_rejected(self):
        rows = [r for r in stable_fix_confirmed_rows(gfx="gfx1100")
                if not r["package"].endswith("gfx1100")]
        rows.append(row(package="rocm-sdk-device-gfx1151", version="10.2.0",
                        tag="py3"))
        ev = plan_mod.evaluate_channel("stable", rows, "gfx1100", "cp312")
        assert "rocm-sdk-device-gfx1100" in ev["missing_packages"]
        assert ev["plan"]["emit_commands"] is False

    def test_multiarch_requires_amd_device_family_wheels(self):
        assert "amd-torch-device-gfx110x" in \
            plan_mod.required_device_packages("multi-arch", "gfx1100")


# --- 13. archive safety --------------------------------------------------------
class TestArchiveSafety:
    def _mini_wheel(self, tmp_path: Path, members: dict, name="fakewheel.whl"):
        p = tmp_path / name
        with zipfile.ZipFile(p, "w") as z:
            for n, data in members.items():
                z.writestr(n, data)
        return p

    def test_path_traversal_member_refused(self, tmp_path):
        p = self._mini_wheel(tmp_path, {
            "../evil.py": b"x",
            "ok/dist-info/METADATA": "Metadata-Version: 2.1\nName: x\nVersion: 1\n"})
        r = lib.safe_inspect_wheel(p)
        assert r["ok"] is False
        assert "../evil.py" in r["unsafe_members"]

    def test_absolute_path_member_refused(self, tmp_path):
        p = self._mini_wheel(tmp_path, {"/abs/evil": b"x"})
        r = lib.safe_inspect_wheel(p)
        assert r["ok"] is False
        assert any(n.startswith("/") or ":" in n for n in r["unsafe_members"])

    def test_valid_mini_wheel_inspection(self, tmp_path):
        dll = (b"padding\x00" * 8
               + b"3.6.3.25f28906\x00"
               + lib.gp_lib.FIX_MARKER + lib.gp_lib.FIX_MARKER
               + b"\x00" * 16)
        p = self._mini_wheel(tmp_path, {
            "_rocm_sdk_libraries/bin/MIOpen.dll": dll,
            "test-1.0.dist-info/METADATA":
                "Metadata-Version: 2.1\nName: test\nVersion: 1.0\n"
                "Requires-Python: >=3.10\n\nRequires-Dist: torch (>=2.10)\n"})
        r = lib.safe_inspect_wheel(p, expect_name="test")
        assert r["ok"] is True, r["errors"]
        assert r["metadata"]["name"] == "test"
        assert r["metadata"]["requires_python"] == ">=3.10"
        assert r["miopen_dll"]["marker_miopen_initializer_list"] == 2
        assert r["miopen_dll"]["build_commit"] == "25f28906"
        assert len(r["miopen_dll"]["sha256"]) == 64

    def test_corrupt_zip_reported(self, tmp_path):
        p = tmp_path / "bad.whl"
        p.write_bytes(b"not a zip at all")
        r = lib.safe_inspect_wheel(p)
        assert r["ok"] is False
        assert any("zip" in e.lower() for e in r["errors"])


# --- 14. unverified source -----------------------------------------------------
class TestUnverifiedSource:
    def test_non_official_host_rejected_by_audit(self):
        import importlib
        audit_mod = load_module("r22a5a_audit", R22A5A / "audit_wheel_provenance.py")
        assert audit_mod.official_wheel_url(
            "stable", "https://evil.example.com/rocm/whl-next/x.whl") is False
        assert audit_mod.official_wheel_url(
            "stable",
            "https://stable.repo.amd.com/rocm/whl-next/x.whl") is True
        # channel confusion: dev URL is not the stable channel
        assert audit_mod.official_wheel_url(
            "stable", "https://dev.repo.amd.com/rocm/whl-next/x.whl") is False

    def test_pypi_lookalike_is_not_official(self):
        assert gp_lib.url_is_official_amd(
            "https://pypi.org/project/torch/") is False


# --- 15/16. channel labeling discipline ----------------------------------------
class TestChannelLabeling:
    def test_nightly_cannot_be_labeled_stable(self):
        p = lib.classify_installation_plan("nightly",
                                           "PRE_RELEASE_CANDIDATE", True, True)
        assert p["tier"] == "OFFICIAL_DEV"
        assert p["tier"] != "OFFICIAL_STABLE"

    def test_rc_ceiling_is_rc(self):
        p = lib.classify_installation_plan("rc", "PRE_RELEASE_CANDIDATE",
                                           True, True)
        assert p["tier"] == "OFFICIAL_RC"

    def test_dev_channel_artifact_never_becomes_stable_candidate(self):
        c = lib.classify_channel_artifact(
            "dev", "rocm-sdk-libraries", "10.3.0.dev0+abc",
            audit={"marker_miopen_initializer_list": 2,
                   "ancestry_status": "ahead", "ancestry_behind_by": 0})
        assert c["classification"] == "PRE_RELEASE_CANDIDATE"

    def test_dev_evidence_not_reused_as_stable(self):
        # the frozen DEV acceptance verdicts live under a DEV ceiling; the
        # R22A.5A classifier has NO input that could promote them
        stable_cls = lib.classify_channel_artifact(
            "stable", "rocm-sdk-libraries", "10.1.0")
        assert stable_cls["classification"] == "OFFICIAL_PRE_FIX"
        dev_cls = lib.classify_channel_artifact(
            "dev", "rocm-sdk-libraries", "10.3.0.dev0+abc")
        assert "STABLE" not in dev_cls["classification"]

    def test_unqualified_plan_emits_no_commands(self):
        p = lib.classify_installation_plan(
            "stable", "OFFICIAL_PRE_FIX", True, True)
        assert p["tier"] == "UNQUALIFIED"
        assert p["emit_commands"] is False
        assert plan_mod.render_commands("stable", [], False) == []


# --- 18. no GPU dependence ------------------------------------------------------
class TestNoGpuDependence:
    def test_lib_never_imports_torch(self):
        src = (R22A5A / "r22a5a_lib.py").read_text(encoding="utf-8")
        assert "import torch" not in src

    def test_g9_verdict_ignores_gpu_availability(self):
        # BLOCKED_RELEASE is about package inputs; a GPU being present or
        # absent cannot flip it (fixture: qualified=False regardless)
        gate = lib.g9_gate(False)
        assert gate["status"] == "BLOCKED_RELEASE"
        gate2 = lib.g9_gate(True)
        assert gate2["status"] == "PROCEED_CANDIDATE"

    def test_nostl_design_static_check_executes_without_gpu(self, tmp_path):
        r = g9.check_nostl_design()
        assert r["all_elements_present"] is True
        assert len(r["elements"]) >= 10


# --- 19/20. plan honesty ---------------------------------------------------------
class TestPlanHonesty:
    def test_unqualified_presented_as_ready_is_refused(self):
        rows = [r for r in stable_fix_confirmed_rows()]
        # poison the sdk verdict
        rows[0] = dict(rows[0], classification="OFFICIAL_PRE_FIX")
        ev = plan_mod.evaluate_channel("stable", rows, "gfx1100", "cp312")
        assert ev["plan"]["tier"] == "UNQUALIFIED"
        assert ev["plan"]["emit_commands"] is False
        assert plan_mod.render_commands("stable", ev["selected_rows"],
                                        ev["plan"]["emit_commands"]) == []

    def test_network_outage_channel_not_silent_success(self):
        rows = [dict(r, classification="BLOCKED_NETWORK")
                for r in stable_fix_confirmed_rows()]
        ev = plan_mod.evaluate_channel("stable", rows, "gfx1100", "cp312")
        assert ev["plan"]["emit_commands"] is False


# --- version ordering / frontier guards ----------------------------------------
class TestVersionOrdering:
    def test_order_dev_alpha_rc_final(self):
        k = lib.version_sort_key
        assert k("10.3.0.dev0+sha") < k("10.3.0a20261115")
        assert k("10.3.0a20261115") < k("10.3.0b1")
        assert k("10.3.0b1") < k("10.3.0rc2")
        assert k("10.3.0rc2") < k("10.3.0")
        assert k("10.1.0") < k("10.2.0")

    def test_set_version_extraction(self):
        assert lib.rocm_set_version("torch", "2.14.0+rocm10.1.0") == "10.1.0"
        assert lib.rocm_set_version("torch", "2.15.0+rocm10.2.0rc2") == "10.2.0rc2"
        assert lib.rocm_set_version("rocm-sdk-libraries", "10.1.0") == "10.1.0"
        assert lib.rocm_set_version("torch", "2.16.0a0+gitdeadbeef"
                                    ".devrocm10.3.0.dev0.abc") == "10.3.0.dev0"
        assert lib.rocm_set_version("numpy", "1.0.0") is None

    def test_older_family_listing_dominated_by_frontier(self):
        c = lib.classify_channel_artifact("stable", "torch",
                                          "2.12.0+rocm10.0.0")
        assert c["classification"] == "NO_NEW_ARTIFACT"

    def test_release_cut_inheritance_not_for_dev_locals(self):
        assert lib._is_release_cut("torch", "2.15.0+rocm10.2.0rc2") is True
        assert lib._is_release_cut("torch", "2.16.0a0+gitabcd"
                                   ".devrocm10.3.0.dev0.x") is False

    def test_url_encoded_versions_decode(self):
        c = lib.classify_channel_artifact(
            "stable", "rocm-sdk-libraries", "10.1.0%2Bnothing")
        assert lib.decode_version("10.3.0.dev0%2Bff576965") == \
            "10.3.0.dev0+ff576965"


# --- G9 hidden-requirement scanner ----------------------------------------------
class TestHiddenRequirements:
    def test_dev_workaround_instructions_flagged(self):
        text = ("pip install torch --index-url https://repo.amd.com/rocm/whl-multi-arch/\n"
                "set HIPRTC_COMPILE_OPTIONS_APPEND=-IC:/vs/Include\n"
                "set VCToolsInstallDir=C:/BuildTools\n")
        hits = lib.scan_hidden_requirements(text)
        codes = {h["code"] for h in hits}
        assert "HIPRTC_ENV" in codes
        assert "VCTOOLS_REDIRECT" in codes

    def test_private_index_flagged(self):
        hits = lib.scan_hidden_requirements(
            "pip install torch --index-url https://my-mirror.example.com/x/")
        assert any(h["code"] == "PRIVATE_INDEX" for h in hits)

    def test_clean_official_instructions_pass(self):
        hits = lib.scan_hidden_requirements(
            "pip install torch --index-url https://repo.amd.com/rocm/whl-multi-arch/\n"
            "pip install ultralytics==8.4.214\n")
        assert hits == []

    def test_env_leakage_scan(self):
        hits = lib.scan_hidden_env({
            "HIPRTC_COMPILE_OPTIONS_APPEND": "-Ix",
            "MIOPEN_FIND_MODE": "3",
            "PATH": "C:\\Windows", "VCToolsInstallDir": "C:/x"})
        codes = {h["code"] for h in hits}
        assert codes == {"HIPRTC_ENV", "MIOPEN_OVERRIDE", "VCTOOLS_REDIRECT"}

    def test_committed_instruction_files_have_no_undisclosed_reliance(self):
        r = g9.check_instruction_files()
        # while BLOCKED_RELEASE stands, disclosed pre-fix workarounds are
        # allowed; an UNDISCLOSED reliance is a contract violation
        assert r["undisclosed_reliance_present"] is False, json.dumps(
            [f for f in r["files"] if any(not h.get("disclosed")
                                          for h in f.get("hits", []))], indent=1)


# --- committed artifacts integration --------------------------------------------
class TestCommittedArtifacts:
    def test_candidates_file_parses_and_classified(self):
        p = REPO_ROOT / "release-provenance" / "r22a5a" / \
            "latest_official_windows_candidates.json"
        if not p.is_file():
            pytest.skip("candidate inventory not generated yet")
        d = json.loads(p.read_text(encoding="utf-8"))
        assert "envelope" in d and "candidates" in d
        assert d["envelope"]["merged_fix_commit"] == lib.MERGED_FIX_COMMIT
        cls = {c["classification"] for c in d["candidates"]}
        assert cls <= set(lib.RELEASE_CLASSIFICATIONS)

    def test_install_plans_currently_block_stable(self):
        for gfx in ("gfx1100", "gfx1151"):
            p = REPO_ROOT / "release-provenance" / "r22a5a" / \
                f"install_plan_{gfx}.json"
            if not p.is_file():
                pytest.skip(f"install plan {gfx} not generated yet")
            d = json.loads(p.read_text(encoding="utf-8"))
            assert d["channels"]["stable"]["plan"]["emit_commands"] is False
            assert d["channels"]["stable"]["plan"]["tier"] == "UNQUALIFIED"
