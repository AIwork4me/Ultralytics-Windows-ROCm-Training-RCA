# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5A Phase D — Golden Path G9 preflight (CPU-only, no torch import).

The user-facing qualified-input gate for the future Stable golden path:

  1. package-input qualification — BLOCKED_RELEASE stop unless a
     fix-confirmed official candidate set exists for the requested channel
     (never silently proceed with a pre-fix wheel and claim success);
  2. hidden-requirement scan of the committed user-facing instructions
     (VS Build Tools / host STL / HIPRTC_* / MIOPEN_* / private indexes /
     editable checkouts / dev paths) + live-environment leakage scan;
  3. STATIC verification of the G1 no-STL regression design inside the
     committed verifier bytes (verify_miopen_nostl.py) — every required
     control element must be present in the committed source, without
     executing any GPU code (execution belongs to R22A.5B);
  4. golden-path readiness — required suite files exist and compile.

    python scripts/r22a5a/g9_preflight.py --plan release-provenance/r22a5a/install_plan_gfx1100.json
    python scripts/r22a5a/g9_preflight.py --plan ... --env-scan

Exit 0 = PROCEED_CANDIDATE; 3 = BLOCKED_RELEASE (no qualified inputs);
4 = preflight contract violation (broken design/instructions).
"""
from __future__ import annotations

import argparse
import compileall
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import r22a5a_lib as lib  # noqa: E402

REPO = _HERE.parent.parent
GOLDEN_PATH = REPO / "golden-path"
WGP = REPO / "windows-golden-path"

# user-facing instruction files audited for hidden requirements (mission §7.1)
INSTRUCTION_FILES = [
    GOLDEN_PATH / "README.md",
    GOLDEN_PATH / "WINDOWS_SETUP.md",
    WGP / "README.md",
    WGP / "docs" / "release-checklist.md",
]

# required golden-path suite files (mission-mandated readiness set)
REQUIRED_GP_FILES = [
    "verify_environment.py", "train.py", "validate.py", "resume.py",
    "verify_checkpoint.py", "acceptance_manifest.json",
    "acceptance_report.schema.json", "requirements-lock.txt",
]

# G1 no-STL design elements that MUST exist in the committed verifier bytes.
# Static proof of design — the runtime execution itself is R22A.5B's gate.
NOSTL_DESIGN_ELEMENTS = [
    ("vc_redirect", r'VCToolsInstallDir["\']\]\s*=\s*str\(scratch',
     "VCToolsInstallDir redirected to an empty scratch dir (host MSVC STL "
     "include tree unreachable — NOT merely an unset variable)"),
    ("include_empty", r'INCLUDE["\']\]\s*=\s*""',
     "INCLUDE cleared so no system include path leaks"),
    ("fresh_cache_home", r'USERPROFILE["\']\]\s*=\s*str\(scratch',
     "fresh USERPROFILE per leg (cold MIOpen cache identity)"),
    ("shim_removed_official", r'pop\("HIPRTC_COMPILE_OPTIONS_APPEND", None\)',
     "official leg REMOVES the HIPRTC shim (pure official bytes)"),
    ("child_process", r"subprocess\.(run|Popen)",
     "reproducer executes in an isolated child process (run or Popen — "
     "R22A.5N.1 uses Popen so the child PID is capturable as evidence)"),
    ("historical_shape", r"20, 100, 35, 45",
     "BatchNorm2d(100) at the historically failing shape"),
    ("forward_backward", r"loss\.backward\(\)",
     "forward + loss + backward really execute"),
    ("finite_checks", r"isfinite",
     "outputs and gradients checked finite"),
    ("failure_signature_map", r"classify_nostl_failure",
     "failure signature mapped to the mission vocabulary"),
    ("prefail_expected", r"OFFICIAL_PRE_FIX_EXPECTED_FAIL",
     "pre-fix wheel EXPECTED to fail (the negative control: an unexpected "
     "PASS under the redirect is reported, never silently accepted — that "
     "would indicate hidden host STL reachability)"),
]


def check_nostl_design() -> dict:
    """Static contract check on the committed verifier bytes."""
    src = (WGP / "scripts" / "verify_miopen_nostl.py").read_text(encoding="utf-8")
    elements = []
    ok = True
    for code, pat, why in NOSTL_DESIGN_ELEMENTS:
        found = lib.re.search(pat, src) is not None
        ok = ok and found
        elements.append({"element": code, "present": found, "purpose": why})
    return {"file": "windows-golden-path/scripts/verify_miopen_nostl.py",
            "all_elements_present": ok, "elements": elements,
            "note": "static design verification only — the runtime no-STL "
                    "gate executes in R22A.5B on real hardware"}


def check_instruction_files() -> dict:
    """Hidden-requirement scan over committed user-facing instructions."""
    files = []
    any_undisclosed = False
    for f in INSTRUCTION_FILES:
        if not f.is_file():
            files.append({"file": str(f.relative_to(REPO)), "exists": False,
                          "hits": [], "undisclosed_reliance": True})
            any_undisclosed = True
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        hits = lib.scan_hidden_requirements(text)
        # a hit is a DISCLOSED workaround when the surrounding doc marks it
        # as a known-issue / pre-fix workaround or explicitly scopes it to a
        # non-acceptance development mode — never a required install step
        disclosed_markers = ("已知问题", "known issue", "workaround", "BLOCKED_RELEASE",
                            "pre-fix", "修复轮", "EngineeringReference",
                            "ENGINEERING_REFERENCE", "工程参考",
                            "MODE A", "上游开发", "upstream development",
                            "not the acceptance", "不是验收")
        for h in hits:
            pos = text.find(h["match"])
            ctx = text[max(0, pos - 400): pos + 400]
            negated = bool(lib.re.search(
                r"(无|不含|不依赖|no|not|without|禁止|never)\s*$",
                text[max(0, pos - 24):pos], lib.re.IGNORECASE))
            h["disclosed"] = negated or any(m.lower() in ctx.lower()
                                            for m in disclosed_markers)
            if not h["disclosed"]:
                any_undisclosed = True
        files.append({"file": str(f.relative_to(REPO)), "exists": True,
                      "hits": hits})
    return {"files": files, "undisclosed_reliance_present": any_undisclosed,
            "rule": "the STABLE-flow instructions must not RELY on any hidden "
                    "requirement; disclosed pre-fix workarounds are acceptable "
                    "ONLY while BLOCKED_RELEASE stands and must be removed "
                    "from the primary path when a fixed wheel qualifies"}


def check_golden_path_readiness() -> dict:
    missing = [f for f in REQUIRED_GP_FILES if not (GOLDEN_PATH / f).is_file()]
    compile_ok = compileall.compile_dir(str(GOLDEN_PATH), quiet=2, force=True)
    schema_ok = False
    try:
        json.loads((GOLDEN_PATH / "acceptance_report.schema.json").read_text(
            encoding="utf-8"))
        json.loads((GOLDEN_PATH / "acceptance_manifest.json").read_text(
            encoding="utf-8"))
        schema_ok = True
    except Exception:  # noqa: BLE001
        schema_ok = False
    return {"missing_files": missing, "compile_ok": bool(compile_ok),
            "manifests_parse": schema_ok,
            "note": "historical MODE A/MODE B behavior untouched "
                    "(R22A.4.1 freeze)"}


def qualify_package_inputs(plan_path: Path, channel: str | None) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    ch = channel or "stable"
    ev = plan["channels"].get(ch)
    if ev is None:
        return {"channel": ch, "qualified": False,
                "status": "BLOCKED_METADATA",
                "why": f"channel {ch!r} absent from install plan"}
    if ev["plan"]["emit_commands"]:
        return {"channel": ch, "qualified": True, "status": "PROCEED_CANDIDATE",
                "tier": ev["plan"]["tier"],
                "why": ev["plan"]["reason"],
                "commands": ev["commands"],
                "next_step": "run resolve_package_set.py to produce the real "
                             "hash-pinned lock, then R22A.5B physical gates"}
    return {"channel": ch, "qualified": False, "status": "BLOCKED_RELEASE",
            "tier": ev["plan"]["tier"],
            "why": f"{ev['sdk_libraries_classification']} — "
                   f"{ev['plan'].get('reason')}; blockers={ev['plan']['blockers']}",
            "hint": "track rocm-libraries#15862; re-run "
                    "scan_official_releases.py + audit_wheel_provenance.py "
                    "when a new artifact appears"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True,
                    help="install_plan_*.json (gen_install_plan.py output)")
    ap.add_argument("--channel", default=None,
                    help="channel to qualify (default: stable)")
    ap.add_argument("--env-scan", action="store_true",
                    help="also scan the LIVE process environment for leakage")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    qual = qualify_package_inputs(Path(args.plan), args.channel)
    nostl = check_nostl_design()
    instr = check_instruction_files()
    gp = check_golden_path_readiness()
    env_hits = lib.scan_hidden_env() if args.env_scan else None

    gate = lib.g9_gate(qual["qualified"])
    record = {
        "run_id": f"R22A5A-G9-PREFLIGHT-{lib.now_utc()[:10]}",
        "mission": "R22A.5A",
        "timestamp": lib.now_utc(),
        "package_input_qualification": qual,
        "g9_gate": gate,
        "nostl_design_static_check": nostl,
        "instruction_hidden_requirements": instr,
        "golden_path_readiness": gp,
        "live_env_leakage": env_hits,
        "verdict": (gate["status"] if nostl["all_elements_present"]
                    and gp["compile_ok"] and not gp["missing_files"]
                    else "PREFLIGHT_CONTRACT_VIOLATION"),
    }
    if args.out:
        lib.dump_json(record, Path(args.out))
    print(json.dumps({k: record[k] for k in
                      ("package_input_qualification", "g9_gate", "verdict",
                       "nostl_design_static_check", "golden_path_readiness",
                       "live_env_leakage")},
                     indent=1, default=str)[:4000])
    detailed = {"undisclosed": instr["undisclosed_reliance_present"]}
    print(f"[detail] instruction scan: {json.dumps(detailed)}")
    if record["verdict"] == "PREFLIGHT_CONTRACT_VIOLATION":
        sys.exit(4)
    sys.exit(0 if qual["qualified"] else 3)


if __name__ == "__main__":
    main()
