# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5A Phase H — one-command CPU release preflight.

Integrates the EXISTING components (no second verification framework):

  1. repo baseline        — git HEAD + verifier (scripts/verify_release_closure.py)
  2. discovery            --live: scan_official_releases.py; --offline: committed inventory
  3. classification       — committed candidates file (fail-closed vocabulary)
  4. provenance           — committed audit JSONs parse + merged-fix commit pin
  5. compatibility        — gen_install_plan.py for gfx1100 + gfx1151
  6. golden-path prep     — g9_preflight static checks (no GPU, no torch)
  7. Stable contract      — R22A.5A contract docs + acceptance-contract.json present
  8. CPU tests            — pytest windows-golden-path/tests (+ compileall)

    python scripts/r22a5a/release_preflight.py --offline
    python scripts/r22a5a/release_preflight.py --live --scan-dir release-provenance/r22a5a

Offline mode NEVER touches the network. Live mode never initializes a GPU
and never installs packages. Result semantics (two INDEPENDENT questions):

  engineering: R22A5A_CPU_PREFLIGHT_READY          (exit 0)
               R22A5A_CPU_PREFLIGHT_FAILED         (exit 1)
  release:     OFFICIAL_STABLE_BLOCKED_RELEASE | CANDIDATE_FOUND_PENDING_PHYSICAL_VALIDATION
               (reported, never auto-promoted; R22A.5B is NEVER launched here)
"""
from __future__ import annotations

import argparse
import compileall
import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import r22a5a_lib as lib  # noqa: E402

REPO = _HERE.parent.parent
CANDIDATES_DEFAULT = REPO / "release-provenance" / "r22a5a" / \
    "latest_official_windows_candidates.json"
CONTRACT_DOCS = [
    "docs/release-closure/R22A5A_INITIAL_GAP_MATRIX.md",
    "docs/release-closure/R22A5A_BINARY_PROVENANCE_CONTRACT.md",
    "docs/release-closure/R22A5A_PACKAGE_COMPATIBILITY_MATRIX.md",
    "docs/release-closure/R22A5A_G9_PREFLIGHT.md",
    "docs/release-closure/R22A5A_STABLE_GPU_ACCEPTANCE_CONTRACT.md",
    "docs/release-closure/R22A5A_RELEASE_ENGINEERING_HANDOFF.md",
    "golden-path/STABLE_ACCEPTANCE_GUIDE.md",
]


def step(name: str):
    print(f"\n=== [{name}] ===", flush=True)


def run_cmd(cmd: list[str], timeout: int = 1200) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=str(REPO),
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def check_baseline(results: dict) -> None:
    step("1/8 repo baseline")
    head = run_cmd(["git", "rev-parse", "HEAD"])
    results["git_head"] = head[1].strip() if head[0] == 0 else None
    results["git_head_ok"] = head[0] == 0
    # raw-evidence untouched: the verifier's git-tree audit enforces every
    # manifest entry against committed blobs — run it as the baseline gate
    code, out = run_cmd([sys.executable, "scripts/verify_release_closure.py",
                         "--json-only"])
    results["verifier_exit"] = code
    try:
        results["verifier_summary"] = json.loads(out.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        results["verifier_summary"] = {"parse_error": out[-400:]}
    print(f"git HEAD: {results['git_head']}")
    print(f"verifier exit={code} "
          f"checks={results['verifier_summary'].get('n_checks')} "
          f"violations={results['verifier_summary'].get('n_violations')}")


def check_discovery(results: dict, live: bool, scan_dir: Path) -> None:
    step("2/8 official discovery")
    if live:
        code, out = run_cmd([sys.executable,
                             str(_HERE / "scan_official_releases.py"),
                             "--out", str(scan_dir / "latest_official_windows_candidates.json"),
                             "--audit", str(scan_dir / "nightly_wheel_audit_20261117.json")])
        results["live_scan_exit"] = code
        print(out[-600:])
    cand = scan_dir / "latest_official_windows_candidates.json"
    results["candidates_file"] = str(cand.relative_to(REPO))
    results["candidates_present"] = cand.is_file()


def check_classification(results: dict, scan_dir: Path) -> None:
    step("3/8 release classification")
    cand = scan_dir / "latest_official_windows_candidates.json"
    if not cand.is_file():
        results["classification_ok"] = False
        return
    d = json.loads(cand.read_text(encoding="utf-8"))
    cls: dict[str, int] = {}
    for c in d["candidates"]:
        cls[c["classification"]] = cls.get(c["classification"], 0) + 1
    vocab_ok = set(cls) <= set(lib.RELEASE_CLASSIFICATIONS)
    results["classification_counts"] = cls
    results["classification_ok"] = vocab_ok
    results["scan_utc"] = d["envelope"]["scanned_utc"]
    results["therock_tags"] = [
        {"tag": t.get("tag_name"), "verdict": t.get("verdict")}
        for t in d["envelope"].get("therock_releases", {}).get("tags", [])]
    results["pytorch_org"] = d["envelope"].get("pytorch_official_index", {}) \
        .get("verdict")
    print(json.dumps(cls, indent=1, sort_keys=True))


def check_provenance(results: dict, scan_dir: Path) -> None:
    step("4/8 binary provenance")
    audits = sorted(scan_dir.glob("*wheel_audit*.json"))
    results["audit_files"] = [str(a.relative_to(REPO)) for a in audits]
    ok = True
    parsed = []
    for a in audits:
        try:
            d = json.loads(a.read_text(encoding="utf-8"))
            assert d["merged_fix_commit"] == lib.MERGED_FIX_COMMIT
            parsed.append({"file": a.name,
                           "verdicts": [e.get("verdict") for e in d["audits"]]})
        except Exception as e:  # noqa: BLE001
            ok = False
            parsed.append({"file": a.name, "error": str(e)})
    results["provenance_audits"] = parsed
    results["provenance_ok"] = ok and bool(audits)
    for p in parsed:
        print(p)


def check_compatibility(results: dict, scan_dir: Path) -> None:
    step("5/8 package compatibility (both architectures)")
    plans = {}
    ok = True
    for gfx, tag in (("gfx1100", "cp312"), ("gfx1151", "cp313")):
        outp = scan_dir / f"install_plan_{gfx}.json"
        cmd = [sys.executable, str(_HERE / "gen_install_plan.py"),
               "--candidates", str(scan_dir / "latest_official_windows_candidates.json"),
               "--gfx", gfx, "--python-tag", tag,
               "--out", str(outp)]
        if gfx == "gfx1100":
            cmd += ["--lock-template",
                    str(scan_dir / "candidate_lock_template.json")]
        code, out = run_cmd(cmd)
        if code != 0:
            ok = False
            print(out[-400:])
            continue
        d = json.loads(outp.read_text(encoding="utf-8"))
        plans[gfx] = {"overall": d["overall"],
                      "stable_tier": d["channels"]["stable"]["plan"]["tier"],
                      "stable_emit": d["channels"]["stable"]["plan"]["emit_commands"]}
        print(f"{gfx}: {d['overall']}")
    results["install_plans"] = plans
    results["compatibility_ok"] = ok and all(
        p["stable_tier"] == "UNQUALIFIED" or p["stable_emit"] is False
        for p in plans.values())


def check_golden_path(results: dict) -> None:
    step("6/8 golden-path G9 preflight (static)")
    sys.path.insert(0, str(_HERE))
    import g9_preflight  # noqa: E402 — local import keeps offline ordering
    nostl = g9_preflight.check_nostl_design()
    instr = g9_preflight.check_instruction_files()
    gp = g9_preflight.check_golden_path_readiness()
    results["g9_static"] = {
        "nostl_design_complete": nostl["all_elements_present"],
        "undisclosed_reliance": instr["undisclosed_reliance_present"],
        "golden_path_compile": gp["compile_ok"],
        "golden_path_missing": gp["missing_files"],
        "manifests_parse": gp["manifests_parse"],
    }
    print(json.dumps(results["g9_static"], indent=1))
    results["golden_path_ok"] = (nostl["all_elements_present"]
                                 and not instr["undisclosed_reliance_present"]
                                 and gp["compile_ok"] and not gp["missing_files"]
                                 and gp["manifests_parse"])


def check_stable_contract(results: dict) -> None:
    step("7/8 Stable acceptance contract completeness")
    missing = [d for d in CONTRACT_DOCS if not (REPO / d).is_file()]
    ac = REPO / "windows-golden-path" / "acceptance-contract.json"
    gates_ok = False
    if ac.is_file():
        try:
            d = json.loads(ac.read_text(encoding="utf-8"))
            gates_ok = set(d.get("gates", {})) >= {
                "G0_provenance", "G1_miopen_nostl", "G2_torch_torchvision_gpu",
                "G3_ultralytics_cli", "G4_optimizer_update",
                "G5_checkpoint_resume", "G8_reliability", "G9_clean_windows"}
        except Exception:  # noqa: BLE001
            gates_ok = False
    results["stable_contract"] = {"missing_docs": missing,
                                  "acceptance_gates_present": gates_ok}
    results["stable_contract_ok"] = not missing and gates_ok
    print(json.dumps(results["stable_contract"], indent=1))


def check_cpu_tests(results: dict, skip_tests: bool) -> None:
    step("8/8 CPU contract tests + compileall")
    comp = compileall.compile_dir(str(REPO / "windows-golden-path"), quiet=2,
                                  force=True)
    comp2 = compileall.compile_dir(str(_HERE), quiet=2, force=True)
    results["compileall_ok"] = bool(comp and comp2)
    if skip_tests:
        results["cpu_tests"] = {"skipped": True}
        results["cpu_tests_ok"] = None
        print("skipped (--skip-tests)")
        return
    code, out = run_cmd([sys.executable, "-m", "pytest",
                         "windows-golden-path/tests", "-q"], timeout=1200)
    tail = out.strip().splitlines()[-1] if out.strip() else ""
    results["cpu_tests"] = {"exit": code, "tail": tail}
    results["cpu_tests_ok"] = code == 0
    print(tail)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline", action="store_true",
                      help="NO network: use committed inventory")
    mode.add_argument("--live", action="store_true",
                      help="network discovery allowed (never GPU/install)")
    ap.add_argument("--scan-dir",
                    default=str(REPO / "release-provenance" / "r22a5a"))
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    scan_dir = Path(args.scan_dir)

    results: dict = {"run_id": f"R22A5A-PREFLIGHT-{lib.now_utc()}",
                     "mode": "live" if args.live else "offline",
                     "timestamp": lib.now_utc()}

    check_baseline(results)
    check_discovery(results, args.live, scan_dir)
    check_classification(results, scan_dir)
    check_provenance(results, scan_dir)
    check_compatibility(results, scan_dir)
    check_golden_path(results)
    check_stable_contract(results)
    check_cpu_tests(results, args.skip_tests)

    gates = {
        "baseline": results.get("git_head_ok") and results.get("verifier_exit") == 0,
        "discovery": results.get("candidates_present"),
        "classification": results.get("classification_ok"),
        "provenance": results.get("provenance_ok"),
        "compatibility": results.get("compatibility_ok"),
        "golden_path": results.get("golden_path_ok"),
        "stable_contract": results.get("stable_contract_ok"),
        "cpu_tests": results.get("cpu_tests_ok") is not False
                     and results.get("compileall_ok", False),
    }
    engineering = "R22A5A_CPU_PREFLIGHT_READY" if all(gates.values()) \
        else "R22A5A_CPU_PREFLIGHT_FAILED"

    # release verdict: stable-qualified candidate anywhere?
    plans = results.get("install_plans") or {}
    stable_ready = any(p.get("stable_emit") for p in plans.values())
    release = ("CANDIDATE_FOUND_PENDING_PHYSICAL_VALIDATION" if stable_ready
               else "OFFICIAL_STABLE_BLOCKED_RELEASE")
    results["gates"] = gates
    results["engineering_verdict"] = engineering
    results["release_verdict"] = release
    results["combined"] = f"{engineering} / {release}"
    results["note"] = ("a completed CPU preflight does NOT remove the "
                       "external publication blocker; this tool never "
                       "launches R22A.5B")

    if args.out:
        lib.dump_json(results, Path(args.out))
    print("\n" + "=" * 60)
    print(json.dumps({"gates": gates,
                      "engineering": engineering,
                      "release": release}, indent=1))
    sys.exit(0 if engineering == "R22A5A_CPU_PREFLIGHT_READY" else 1)


if __name__ == "__main__":
    main()
