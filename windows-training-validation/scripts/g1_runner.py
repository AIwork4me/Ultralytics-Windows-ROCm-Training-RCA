"""G1 runner — orchestrates primitive-matrix legs with isolated cache homes.

Each leg is an independent process with its own USERPROFILE (fresh MIOpen
cache) and optional host-STL hiding (VCToolsInstallDir redirect + empty
INCLUDE — the technique validated in the C+D mission RCA.md §2). Raw
stdout/stderr are archived; JSON results parsed from the leg's --out file;
subprocess exit codes are checked explicitly and never inferred.

    python scripts/g1_runner.py --python <env-python> --legs legA,legB \
        --mode stl|nostl --repeat 3 --raw-dir ../raw --report-dir ../reports
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def fail(msg: str) -> None:
    print(f"RUNNER-FAIL: {msg}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, help="python executable of env under test")
    parser.add_argument("--legs", required=True, help="comma-separated leg names")
    parser.add_argument("--mode", choices=["stl", "nostl"], default="stl")
    parser.add_argument("--expect-fail", action="store_true",
                        help="run primitives in --expect-stl-fail mode (negative control)")
    parser.add_argument("--repeat", type=int, default=1, help="independent cold runs per leg")
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--script", default=str(Path(__file__).resolve().parent.parent / "tests" / "g1_primitives.py"))
    parser.add_argument("--probe-script", default=str(
        Path(__file__).resolve().parent.parent.parent / "release-provenance" / "scripts" / "probe_loaded_miopen.py"))
    args = parser.parse_args()

    py = Path(args.python)
    if not py.is_file():
        fail(f"python executable not found: {py}")
    script = Path(args.script)
    if not script.is_file():
        fail(f"primitives script not found: {script}")
    raw_dir = Path(args.raw_dir)
    report_dir = Path(args.report_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    leg_names = [s.strip() for s in args.legs.split(",") if s.strip()]
    summary = {"runner": "g1_runner.py", "mode": args.mode,
               "expect_fail": args.expect_fail, "python": str(py),
               "started_utc": datetime.now(timezone.utc).isoformat(),
               "legs": []}

    for leg in leg_names:
        for rep in range(1, args.repeat + 1):
            leg_id = f"{leg}_rep{rep}" if args.repeat > 1 else leg
            cache_home = raw_dir / "cache_homes" / leg_id
            cache_home.mkdir(parents=True, exist_ok=True)
            fakevc = cache_home / "fakevc"
            fakevc.mkdir(exist_ok=True)
            out_json = raw_dir / f"{leg_id}.result.json"
            raw_log = raw_dir / f"{leg_id}.log"

            env = dict(os.environ)
            env["USERPROFILE"] = str(cache_home)   # isolated MIOpen cache home (fresh)
            env["MIOPEN_LOG_LEVEL"] = "3" if args.mode == "stl" else "5"
            if args.mode == "nostl":
                env["VCToolsInstallDir"] = str(fakevc)
                env["INCLUDE"] = ""

            cmd = [str(py), "-I", str(script), "--out", str(out_json)]
            if args.expect_fail:
                cmd.append("--expect-stl-fail")
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                                  encoding="utf-8", errors="replace")
            raw_log.write_text(
                f"# command: {subprocess.list2cmdline(cmd)}\n"
                f"# exit_code: {proc.returncode}\n"
                f"# mode: {args.mode} expect_fail: {args.expect_fail}\n"
                f"# USERPROFILE: {cache_home}\n"
                f"# VCToolsInstallDir: {env.get('VCToolsInstallDir', '(system)')}\n"
                f"# INCLUDE: {env.get('INCLUDE', '(system)')}\n\n"
                f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}\n",
                encoding="utf-8")

            # cache-population evidence (real HIPRTC compiles leave artifacts)
            cache_files = sorted(str(p.relative_to(cache_home)) for p in cache_home.rglob("*")
                                 if p.is_file())[:200]

            entry = {"leg": leg_id, "exit_code": proc.returncode,
                     "cache_home": str(cache_home), "cache_files_created": cache_files,
                     "cache_files_count": len([p for p in cache_home.rglob('*') if p.is_file()])}

            # GPU provenance: in-process loaded-DLL probe (same cache home)
            if not args.expect_fail:
                probe_out = raw_dir / f"{leg_id}.loaddll.json"
                probe = subprocess.run(
                    [str(py), "-I", args.probe_script, "--out", str(probe_out)],
                    capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
                (raw_dir / f"{leg_id}.probe.log").write_text(
                    f"# probe exit: {probe.returncode}\n--- stdout ---\n{probe.stdout}\n--- stderr ---\n{probe.stderr}\n",
                    encoding="utf-8")
                if probe.returncode != 0 or not probe_out.is_file():
                    fail(f"leg {leg_id}: loaded-DLL probe failed (exit={probe.returncode})")
                entry["loaded_dll"] = json.loads(probe_out.read_text(encoding="utf-8"))["miopen_loaded"]

            # In negative-control mode the RuntimeError carries only
            # "miopenStatusUnknownError"; the precise HIPRTC signature is on
            # stderr (captured in the raw log). Re-derive from stderr.
            if args.expect_fail and raw_log.is_file():
                log_text = raw_log.read_text(encoding="utf-8", errors="replace")
                sig = {
                    "hiprtc_compilation_error": "HIPRTC_ERROR_COMPILATION (6)" in log_text
                                                and "hiprtcCompileProgram" in log_text,
                    "type_traits_missing": "'type_traits' file not found" in log_text,
                    "batchnorm_fwd_train_spatial": "MIOpenBatchNormFwdTrainSpatial.cpp" in log_text,
                    "code_object_build_failed": "Code object build failed" in log_text,
                }
                stderr_matched = sig["hiprtc_compilation_error"] and sig["type_traits_missing"] \
                    and sig["batchnorm_fwd_train_spatial"] and sig["code_object_build_failed"]
                entry["stderr_signature"] = sig
                entry["stderr_signature_matched"] = stderr_matched

            if out_json.is_file():
                try:
                    entry["result"] = json.loads(out_json.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    fail(f"leg {leg_id}: result JSON unreadable: {exc}")
            else:
                fail(f"leg {leg_id}: no result JSON produced (exit={proc.returncode}); see {raw_log}")

            summary["legs"].append(entry)
            print(f"[{leg_id}] exit={proc.returncode} "
                  f"result={entry['result'].get('summary', entry['result'].get('expect_stl_fail', {}).get('status', '?'))}")

    # aggregate verdict
    ok = True
    for leg in summary["legs"]:
        if args.expect_fail:
            # EXPECTED_FAIL means the exact #3956 signature reproduced. The
            # Python-side status may read UNEXPECTED_FAIL (exception string is
            # truncated); the stderr signature is authoritative.
            ok = ok and leg.get("stderr_signature_matched", False)
        else:
            st = leg["result"].get("summary", {}).get("status")
            ok = ok and st == "PASS" and leg["exit_code"] == 0
    summary["verdict"] = "PASS" if ok else "FAIL"
    summary["finished_utc"] = datetime.now(timezone.utc).isoformat()

    env_tag = py.stem  # python executable name (pm13437_merged / pm13437_official)
    report = report_dir / ("G1_NEGATIVE_CONTROL.json" if args.expect_fail
                           else f"G1_MATRIX_{env_tag}_{args.mode}.json")
    report.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"verdict={summary['verdict']} report={report}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
