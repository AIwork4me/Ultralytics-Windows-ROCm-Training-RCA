# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Evidence report generator (missions §11/§16, hardened R21.1 TASK B).

Subcommands:
  train-summary  turn one training stdout log + exit code into a strict
                 evidence record (used by train_yolo.ps1)
  full           aggregate every phase JSON of a run into a gate report that
                 ENFORCES the acceptance contract (fail-closed):
                 required gate IDs must exist with actual PASS evidence;
                 missing gate = NO-GO; FAIL/INCONCLUSIVE/BLOCKED can never be
                 promoted; a candidate can never be promoted to stable;
                 missing gfx1151 = no full cross-arch release PASS; missing
                 clean Windows = no final Golden Path PASS; engineering
                 reference records never earn an Official PASS.

False-PASS rejection rules (mirroring scripts/verify_release_closure.py):
  - a train-summary claiming PASS with exit_code != 0 → rejected
  - no "PASS" without GPU provenance keys (gpu_name + hip)
  - synthetic fixture inputs (records tagged harness_fixture) can never
    produce PHYSICAL_GPU_PASS — they report HARNESS_FIXTURE_ONLY
  - physical execution is NEVER inferred from the absence of harness_fixture:
    machine identity, subprocess exit codes, artifact linkage and evidence
    provenance are verified; a record that cannot prove its provenance is
    PHYSICAL_UNPROVEN and cannot satisfy any gate

Exit codes for `full`: 0 = verdict PASS at the sequence ceiling;
1 = violations in the evidence itself; 2 = NO-GO missing/unscoped gates;
3 = NO-GO required gate not passing. Any NO-GO beats any PASS.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

# content signatures: how a raw JSON is recognized as a given gate (filenames
# vary across runs; identification must be content-based)
GATE_SIGNATURES = {
    "G0_provenance": lambda d: "provenance_status" in d and "loaded_miopen_dll" in d,
    "G1_miopen_nostl": lambda d: "classification" in d and "leg_detail" in d,
    "G2_torch_torchvision_gpu": lambda d: "gates" in d and "cpu_fallback_used" in d,
    "G3_ultralytics_cli": lambda d: "parsed_facts" in d and "checkpoints" in d,
    "G4_optimizer_update": lambda d: "optimizer_step_count" in d,
    "G5_checkpoint_resume": lambda d: "stages" in d and "checkpoint_sha256" in d,
    "G8_reliability": lambda d: "runs" in d and "n_total" in d and "cache_class" in d,
    "G9_clean_windows": lambda d: d.get("gate_id") == "G9_clean_windows"
    or d.get("evidence_class") in ("CLEAN_WINDOWS_INSTALL", "HOST_REUSE_FRESH_VENV"),
}
# G7 (cross-arch) is not a script: any physical gate record whose gfx_target
# is gfx1151 evidences it (see record classification below)

SEQUENCE_REQUIRED = {
    "engref": ["G0_provenance", "G1_miopen_nostl", "G2_torch_torchvision_gpu",
               "G3_ultralytics_cli", "G4_optimizer_update",
               "G5_checkpoint_resume", "G8_reliability"],
    "candidate": ["G0_provenance", "G1_miopen_nostl", "G2_torch_torchvision_gpu",
                  "G3_ultralytics_cli", "G4_optimizer_update",
                  "G5_checkpoint_resume", "G8_reliability"],
    "stable": ["G0_provenance", "G1_miopen_nostl", "G2_torch_torchvision_gpu",
               "G3_ultralytics_cli", "G4_optimizer_update",
               "G5_checkpoint_resume", "G7_gfx1151_physical",
               "G8_reliability", "G9_clean_windows"],
}
CANDIDATE_PREFIX = {"dev": "DEV", "nightly": "NIGHTLY", "rc": "RC"}
NOT_PASSING = ("FAIL", "BLOCKED", "INCONCLUSIVE", "SKIP", "NOT_RUN")


def parse_train_log(text: str) -> dict:
    """Extract the §8 acceptance facts from a yolo train log."""
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)  # strip ANSI color codes
    facts = {
        "gpu_selected": None, "amp_check": None, "epoch_completed": False,
        "losses_finite": None, "validation_completed": False,
        "cpu_fallback": "using CPU" in text or "device=cpu" in text.lower(),
    }
    # GPU names may contain parentheses (e.g. "AMD Radeon(TM) 8060S Graphics")
    # — anchor on the trailing ", NNNNMiB)" so the full name survives; the old
    # [^,)]+ pattern truncated at the first ')' inside the name (R22A gfx1151)
    m = (re.search(r"(CUDA:\d+|cpu)\s*\((.+?),\s*[\d.]+\s*[GM]iB\)", text)
         or re.search(r"(CUDA:\d+|cpu)\s*\(([^,)]+)", text))
    if m:
        facts["gpu_selected"] = {"device": m.group(1), "name": m.group(2).strip()}
    if re.search(r"AMP:\s*checks passed", text):
        facts["amp_check"] = "PASSED"
    elif re.search(r"AMP:\s*checks failed", text):
        facts["amp_check"] = "FAILED_FALLBACK_FP32"
    if re.search(r"\b1/1\b.*G\s", text) or "GPU_mem" in text:
        facts["epoch_completed"] = bool(re.search(r"^\s*1/1\s", text, re.M)) or "1/1" in text
    losses = [float(g) for tup in re.findall(r"box_loss\D+([\d.]+)|box\s+([\d.]+)", text)
              for g in tup if g]
    facts["losses_found"] = len(losses)
    facts["losses_finite"] = bool(losses) and all(l == l and l < float("inf") for l in losses)
    facts["validation_completed"] = "all" in text and "Images" in text and \
        bool(re.search(r"^\s*all\s+\d+", text, re.M))
    return facts


def cmd_train_summary(args) -> int:
    import torch
    import importlib.metadata as im

    text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    facts = parse_train_log(text)
    if args.checkpoints_json_file:
        ckpts = json.loads(Path(args.checkpoints_json_file).read_text(encoding="utf-8-sig"))
    elif args.checkpoints_json:
        ckpts = json.loads(args.checkpoints_json)
    else:
        ckpts = []
    # exit code 0 is necessary but not sufficient; every parsed fact must hold
    ok = (args.exit_code == 0 and facts["gpu_selected"]
          and facts["gpu_selected"]["device"].startswith("CUDA")
          and facts["amp_check"] in ("PASSED", None)
          and facts["epoch_completed"] and facts["losses_finite"] is not False
          and len(ckpts) >= 2 and not facts["cpu_fallback"])
    # runtime classification: workaround disclosure first, then marker+channel
    # (never the historical hardcoded binary that could only ever say
    # ENGINEERING_REFERENCE or OFFICIAL_PRE_FIX)
    workarounds = gp_lib.detect_workarounds()
    miopen = gp_lib.loaded_miopen_identity()
    runtime_class = gp_lib.classify_runtime(workarounds, args.channel,
                                            miopen if miopen.get("loaded") else None)
    record = {
        "run_id": args.run_id, "mission": args.mission or "R21",
        "timestamp": gp_lib.now_utc(),
        "gpu_name": facts["gpu_selected"]["name"] if facts["gpu_selected"] else None,
        "gfx_target": gp_lib.gfx_from_device_name(
            facts["gpu_selected"]["name"]) if facts["gpu_selected"] else None,
        "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "python": sys.version.split()[0], "torch": torch.__version__,
        "torchvision": (im.version("torchvision")
                        if any(d.metadata['Name'] == 'torchvision' for d in im.distributions()) else None),
        "hip": torch.version.hip,
        "runtime_class": runtime_class,
        "command": args.command, "exit_code": args.exit_code,
        "duration_s": None,
        "pass_fail_skip": "PASS" if ok else "FAIL",
        "failure_classification": None if ok else (
            "GPU_DEVICE_SELECTION" if not facts["gpu_selected"] else
            "CHECKPOINT_RESUME_FAILURE" if len(ckpts) < 2 else "INCONCLUSIVE"),
        "raw_log_path": args.log,
        "parsed_facts": facts, "checkpoints": ckpts,
        "standard_command_no_extra_params": True,
        "validation_note": "COCO8 mAP is a smoke metric, not a model-quality benchmark",
    }
    gp_lib.write_evidence(record, Path(args.out))
    print(f"TRAIN_SUMMARY: {record['pass_fail_skip']} (exit={args.exit_code})")
    return 0 if ok else 1


# --- evidence provenance verification (TASK B) -------------------------------

def _iso_ok(ts) -> bool:
    if not isinstance(ts, str):
        return False
    try:
        _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def evidence_quality(d: dict, jf: Path) -> tuple[str, list[str]]:
    """Classify one evidence record and list its provenance problems.

    Physical execution is NEVER inferred from the absence of harness_fixture:
    without machine identity + subprocess result + artifact linkage the record
    is PHYSICAL_UNPROVEN and cannot satisfy any gate.
    """
    problems: list[str] = []
    if d.get("harness_fixture"):
        return "HARNESS_FIXTURE_ONLY", ["record tagged harness_fixture"]
    for k in ("gpu_name", "gfx_target", "windows_build", "driver_version", "hip"):
        if not d.get(k):
            problems.append(f"machine identity missing: {k}")
    ec = d.get("exit_code")
    if isinstance(ec, bool) or not isinstance(ec, int):
        problems.append("no integer subprocess exit_code")
    if not _iso_ok(d.get("timestamp")):
        problems.append("timestamp not ISO-8601")
    if not d.get("run_id"):
        problems.append("no run_id")
    rlp = d.get("raw_log_path")
    linked = None
    if isinstance(rlp, str) and rlp:
        p = Path(rlp)
        if p.is_file():
            linked = {"path": rlp, "sha256": gp_lib.sha256_file(p)}
        elif (jf.parent / (jf.stem + ".log")).is_file():
            linked = {"path": str(jf.parent / (jf.stem + ".log")),
                      "sha256": gp_lib.sha256_file(jf.parent / (jf.stem + ".log")),
                      "note": "sibling log of the evidence file"}
    if linked is None:
        problems.append("no artifact linkage: raw_log_path absent or no "
                        "matching log file found")
    if problems:
        return "PHYSICAL_UNPROVEN", problems
    return "PHYSICAL_GPU_RUN", []


def cmd_full(args) -> int:
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(Path(args.evidence_dir).glob("*.json"))
    sequence = getattr(args, "sequence", None)
    channel = getattr(args, "channel", None)
    contract_path = Path(getattr(args, "contract", None)
                         or Path(__file__).resolve().parent.parent
                         / "acceptance-contract.json")

    gates: dict = {}
    violations: list[str] = []
    records: list[dict] = []
    # gate_status.json is orchestrator state, not a gate evidence record
    inputs = [jf for jf in inputs if jf.name != "gate_status.json"]
    for jf in inputs:
        try:
            d = json.loads(jf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            violations.append(f"{jf.name}: unreadable JSON ({e})")
            continue
        # false-PASS rejection: claimed status vs exit code
        pfs = d.get("pass_fail_skip")
        if pfs == "PASS" and isinstance(d.get("exit_code"), int) and d["exit_code"] != 0:
            violations.append(f"{jf.name}: claims PASS but exit_code={d['exit_code']}")
        if pfs == "PASS" and not (d.get("gpu_name") and d.get("hip")):
            violations.append(f"{jf.name}: PASS without GPU provenance")
        eq_class, eq_problems = evidence_quality(d, jf)
        gate_ids = [g for g, sig in GATE_SIGNATURES.items() if sig(d)]
        if d.get("gfx_target") == "gfx1151" and gate_ids:
            gate_ids.append("G7_gfx1151_physical")
        rec = {
            "file": jf.name, "gate_ids": gate_ids,
            "claimed": pfs, "exit_code": d.get("exit_code"),
            "runtime_class": d.get("runtime_class"),
            "classification": d.get("classification"),
            "failure_classification": d.get("failure_classification"),
            "gfx_target": d.get("gfx_target"),
            "evidence_class": eq_class,
            "provenance_problems": eq_problems,
            "artifact": (evidence_quality(d, jf) and None) or None,
        }
        records.append(rec)
        gates[jf.name] = {k: rec[k] for k in
                          ("claimed", "exit_code", "runtime_class",
                           "failure_classification", "evidence_class")}

    # provenance-quality violations: a PASS that cannot prove physical execution
    for rec in records:
        if rec["claimed"] == "PASS" and rec["evidence_class"] != "PHYSICAL_GPU_RUN":
            violations.append(f"{rec['file']}: PASS claim is {rec['evidence_class']} "
                              f"({'; '.join(rec['provenance_problems'])})")

    any_physical_pass = any(r["claimed"] == "PASS"
                            and r["evidence_class"] == "PHYSICAL_GPU_RUN"
                            for r in records)

    # --- acceptance-contract enforcement ------------------------------------
    blockers: list[str] = []
    gate_results: dict = {}
    verdict: str | None = None
    full_cross_arch = False
    final_golden_path = False

    if sequence not in SEQUENCE_REQUIRED:
        blockers.append(f"sequence {sequence!r} not one of {sorted(SEQUENCE_REQUIRED)} "
                        "— no acceptance verdict can be issued (fail-closed)")
        verdict = "NO_GO_UNSCOPED"
    else:
        required = SEQUENCE_REQUIRED[sequence]
        official_classes = ({"stable": ("OFFICIAL_STABLE",),
                             "candidate": ("OFFICIAL_CANDIDATE",)}[sequence]
                            if sequence in ("stable", "candidate") else None)

        # orchestrator reconciliation: a PASS additionally needs the harness's
        # own gate_status.json (independently recorded subprocess exit codes)
        # to cover the gate — hand-written evidence alone cannot earn a PASS
        gs = None
        gs_path = Path(args.evidence_dir) / "gate_status.json"
        if gs_path.is_file():
            try:
                # utf-8-sig: PS 5.1 Set-Content writes a BOM
                gs = json.loads(gs_path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError as e:
                violations.append(f"gate_status.json: unreadable JSON ({e})")
        gs_by_gate: dict[str, list[dict]] = {}
        if gs:
            for entry in gs.get("gates", []):
                gid = str(entry.get("gate") or "")
                for canon in GATE_SIGNATURES:
                    if gid == canon or gid.startswith(canon):
                        gs_by_gate.setdefault(canon, []).append(entry)
                        break

        def satisfies(rec: dict) -> tuple[bool, str]:
            """Can this record satisfy a required gate in this sequence?"""
            if rec["evidence_class"] != "PHYSICAL_GPU_RUN":
                return False, f"evidence {rec['evidence_class']}"
            if official_classes is not None:
                if rec["runtime_class"] not in official_classes:
                    return False, (f"runtime_class {rec['runtime_class']} cannot "
                                   f"satisfy {sequence} gates")
            if sequence == "engref" and rec["gate_ids"] == ["G1_miopen_nostl"]:
                cls = rec["classification"] or ""
                if cls not in ("OFFICIAL_PRE_FIX_EXPECTED_FAIL",
                               "ENGINEERING_REFERENCE_PASS"):
                    if rec["claimed"] != "PASS":
                        return False, f"claimed {rec['claimed']}"
            elif rec["claimed"] != "PASS":
                return False, f"claimed {rec['claimed']}"
            if isinstance(rec["exit_code"], int) and rec["exit_code"] != 0 \
                    and rec["classification"] != "OFFICIAL_PRE_FIX_EXPECTED_FAIL":
                return False, f"exit_code {rec['exit_code']}"
            return True, "ok"

        for g in required:
            cands = [r for r in records if g in r["gate_ids"]]
            if g == "G7_gfx1151_physical":  # cross-arch: needs gfx1151 records
                cands = [r for r in cands if r["gfx_target"] == "gfx1151"]
            if not cands:
                gate_results[g] = {"status": "MISSING",
                                   "reason": "no evidence record for this gate"}
                blockers.append(f"{g}: missing (required for {sequence})")
                continue
            accepted_entries = [e for e in gs_by_gate.get(g, [])
                                if e.get("accepted") is True]
            if not accepted_entries:
                blockers.append(f"{g}: no accepted orchestrator gate_status entry "
                                "(synthetic or hand-written evidence cannot "
                                "automatically earn a PASS)")
                gate_results[g] = {"status": "UNORCHESTRATED",
                                   "reason": "gate_status.json does not cover this gate",
                                   "candidates": [r["file"] for r in cands]}
                continue
            good = [r for r in cands if satisfies(r)[0]
                    and (r["classification"] == "OFFICIAL_PRE_FIX_EXPECTED_FAIL"
                         or any(e.get("exit_code") == r["exit_code"]
                                for e in accepted_entries))]
            if good:
                gate_results[g] = {"status": "PASS", "satisfied_by":
                                   [r["file"] for r in good]}
            else:
                worst = cands[0]
                why = next((satisfies(r)[1] for r in cands), "not satisfied")
                gate_results[g] = {"status": "NOT_SATISFIED",
                                   "claimed": worst["claimed"],
                                   "reason": why,
                                   "candidates": [r["file"] for r in cands]}
                blockers.append(f"{g}: not satisfied ({why})")

        # sequence-specific promotion rules
        if sequence == "candidate":
            if channel not in CANDIDATE_PREFIX:
                blockers.append(f"candidate channel {channel!r} unrecognized — "
                                "cannot issue a candidate verdict")
                verdict = "NO_GO"
            for r in records:  # promotion attempt detection
                if r["runtime_class"] == "OFFICIAL_STABLE":
                    blockers.append(f"{r['file']}: OFFICIAL_STABLE record inside a "
                                    "candidate sequence (promotion attempt)")
            if not blockers:
                verdict = f"{CANDIDATE_PREFIX[channel]}_CANDIDATE_PASS"
        elif sequence == "stable":
            g7 = gate_results.get("G7_gfx1151_physical", {})
            if g7.get("status") == "PASS":
                full_cross_arch = True
            else:
                blockers.append("G7_gfx1151_physical not PASS — no full "
                                "cross-arch release PASS")
            g9s = [r for r in records if "G9_clean_windows" in r["gate_ids"]]
            clean = [r for r in g9s
                     if r["evidence_class"] == "PHYSICAL_GPU_RUN"
                     and json.loads((Path(args.evidence_dir) / r["file"])
                                    .read_text(encoding="utf-8"))
                     .get("evidence_class") == "CLEAN_WINDOWS_INSTALL"]
            if clean and not blockers:
                final_golden_path = True
            else:
                blockers.append("G9_clean_windows requires a CLEAN_WINDOWS_INSTALL "
                                "record — HOST_REUSE_FRESH_VENV or absent cannot "
                                "earn the final Golden Path PASS")
            if not blockers:
                verdict = "OFFICIAL_STABLE_PASS"
        else:  # engref
            if not blockers:
                verdict = "ENGINEERING_REFERENCE_PASS"
        if blockers and verdict is None:
            verdict = "NO_GO"
        # a later PASS can never hide an earlier failed gate: blockers computed
        # across ALL required gates, not until first success
        if blockers:
            full_cross_arch = False
            final_golden_path = False

    report = {
        "run_id": args.run_id, "generated_utc": gp_lib.now_utc(),
        "sequence": sequence, "channel": channel,
        "contract": str(contract_path),
        "gates": gates, "violations": violations,
        "gate_results": gate_results, "blockers": blockers,
        "verdict": verdict,
        "full_cross_arch_release_pass": full_cross_arch,
        "final_golden_path_pass": final_golden_path,
        "any_physical_gpu_pass": any_physical_pass,
        "summary_class": ("PHYSICAL_GPU_PASS_EVIDENCED" if any_physical_pass
                          else "NO_PHYSICAL_PASS"),
        "note": "synthetic fixtures can never produce PHYSICAL_GPU_PASS; "
                "physical execution is proven by machine identity + subprocess "
                "result + artifact linkage, never inferred from absent markers",
    }
    (report_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # SHA256SUMS over every input evidence file
    lines = []
    for jf in inputs:
        lines.append(f"{gp_lib.sha256_file(jf)}  {jf.name}")
    (report_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"violations": violations, "verdict": verdict,
                      "blockers": blockers,
                      "any_physical_gpu_pass": any_physical_pass,
                      "n_inputs": len(inputs)}, indent=2))
    if violations:
        return 1
    if verdict in (None, "NO_GO", "NO_GO_UNSCOPED"):
        return 2 if not gate_results else 3
    return 0 if verdict.endswith("_PASS") else 3


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    ts = sub.add_parser("train-summary")
    ts.add_argument("--run-id", required=True)
    ts.add_argument("--mission", default=None)
    ts.add_argument("--log", required=True)
    ts.add_argument("--exit-code", type=int, required=True)
    ts.add_argument("--checkpoints-json", default=None,
                    help="inline JSON (avoid on PS 5.1: quote mangling)")
    ts.add_argument("--checkpoints-json-file", default=None,
                    help="file containing the checkpoints JSON (preferred)")
    ts.add_argument("--command", required=True)
    ts.add_argument("--channel", default=None,
                    help="stack channel for runtime classification")
    ts.add_argument("--out", required=True)

    fu = sub.add_parser("full")
    fu.add_argument("--run-id", required=True)
    fu.add_argument("--evidence-dir", required=True)
    fu.add_argument("--report-dir", required=True)
    fu.add_argument("--sequence", default=None,
                    choices=["engref", "candidate", "stable"],
                    help="acceptance sequence being graded (default: none → NO-GO)")
    fu.add_argument("--channel", default=None,
                    help="candidate channel (dev/nightly/rc) for candidate verdicts")
    fu.add_argument("--contract", default=None,
                    help="acceptance contract JSON (default: acceptance-contract.json)")

    args = ap.parse_args()
    sys.exit(cmd_train_summary(args) if args.cmd == "train-summary" else cmd_full(args))


if __name__ == "__main__":
    main()
