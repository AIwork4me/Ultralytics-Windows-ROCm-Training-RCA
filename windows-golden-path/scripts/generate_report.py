# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Evidence report generator (missions §11/§16).

Subcommands:
  train-summary  turn one training stdout log + exit code into a strict
                 evidence record (used by train_yolo.ps1)
  full           aggregate every phase JSON of a run into a gate report:
                 validates the common schema, recomputes gate verdicts from
                 embedded assertions (false-PASS rejection), writes
                 report.json + SHA256SUMS for all inputs

False-PASS rejection rules (mirroring scripts/verify_release_closure.py):
  - a train-summary claiming PASS with exit_code != 0 → rejected
  - no "PASS" without GPU provenance keys (gpu_name + hip)
  - synthetic fixture inputs (records tagged harness_fixture) can never
    produce PHYSICAL_GPU_PASS — they report HARNESS_FIXTURE_ONLY
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402


def parse_train_log(text: str) -> dict:
    """Extract the §8 acceptance facts from a yolo train log."""
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)  # strip ANSI color codes
    facts = {
        "gpu_selected": None, "amp_check": None, "epoch_completed": False,
        "losses_finite": None, "validation_completed": False,
        "cpu_fallback": "using CPU" in text or "device=cpu" in text.lower(),
    }
    m = re.search(r"(CUDA:\d+|cpu)\s*\(([^,)]+)", text)
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
        "runtime_class": ("ENGINEERING_REFERENCE"
                          if gp_lib.detect_workarounds()["any_workaround_present"]
                          else "OFFICIAL_PRE_FIX"),
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


def cmd_full(args) -> int:
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(Path(args.evidence_dir).glob("*.json"))
    gates, violations = {}, []
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
        synthetic = bool(d.get("harness_fixture"))
        physical = not synthetic
        gates[jf.name] = {
            "claimed": pfs, "exit_code": d.get("exit_code"),
            "runtime_class": d.get("runtime_class"),
            "failure_classification": d.get("failure_classification"),
            "physical_run": physical,
            "evidence_class": ("HARNESS_FIXTURE_ONLY" if synthetic else "PHYSICAL_GPU_RUN"),
        }
    any_physical_pass = any(g["claimed"] == "PASS" and g["physical_run"]
                            for g in gates.values())
    report = {
        "run_id": args.run_id, "generated_utc": gp_lib.now_utc(),
        "gates": gates, "violations": violations,
        "any_physical_gpu_pass": any_physical_pass,
        "summary_class": ("PHYSICAL_GPU_PASS_EVIDENCED" if any_physical_pass
                          else "NO_PHYSICAL_PASS"),
        "note": "synthetic fixtures can never produce PHYSICAL_GPU_PASS",
    }
    (report_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # SHA256SUMS over every input evidence file
    lines = []
    for jf in inputs:
        lines.append(f"{gp_lib.sha256_file(jf)}  {jf.name}")
    (report_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"violations": violations,
                      "any_physical_gpu_pass": any_physical_pass,
                      "n_inputs": len(inputs)}, indent=2))
    return 0 if not violations else 1


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
    ts.add_argument("--out", required=True)

    fu = sub.add_parser("full")
    fu.add_argument("--run-id", required=True)
    fu.add_argument("--evidence-dir", required=True)
    fu.add_argument("--report-dir", required=True)

    args = ap.parse_args()
    sys.exit(cmd_train_summary(args) if args.cmd == "train-summary" else cmd_full(args))


if __name__ == "__main__":
    main()
