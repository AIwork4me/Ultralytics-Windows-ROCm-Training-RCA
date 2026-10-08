"""Phase 5.1 (P5.1-CANDIDATE-R1) - adapted from the validated Phase-5
script by mechanical path/identity substitution only (source tree, build
dir, evidence dir, schema/gate names). Logic unchanged.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

Y = Path(r"C:\Users\rocm\Desktop\YOLO_AMD")
TEST = Y / "phase5_1_build" / "ci_test" / "bin" / "test_hiprtc_selfcontained.exe"
UNP = Y / "rocm-libraries-phase5-pristine"
PAT = Y / "rocm-libraries-phase5.1-candidate"
CORE = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core")
HIPRTC_DLL = CORE / "bin" / "hiprtc0714.dll"
OUT = Y / "Ultralytics-Windows-ROCm-Training-RCA" / "evidence" / "phase5_1" / "ci"
MSVC_INC = Path(r"C:\BuildTools\VC\Tools\MSVC\14.44.35207\include")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def run_cell(name: str, tree: Path, mode: str, extra: list | None = None,
             extra_env: dict | None = None, kernels_dir: Path | None = None) -> dict:
    env = dict(os.environ)
    env["PATH"] = str(CORE / "bin") + os.pathsep + env.get("PATH", "")
    env.pop("CPATH", None)
    if extra_env:
        env.update(extra_env)
    kd = kernels_dir if kernels_dir is not None else (tree / "projects/miopen/src/kernels")
    # the test now rejects duplicate option arguments (P508 F3 hardening);
    # an explicit --arch/--mode in extra replaces the default instead of
    # appending a second copy.
    extra = extra or []
    if not any(a.startswith("--arch=") for a in extra):
        extra = ["--arch=gfx1151"] + extra
    cmd = [str(TEST), str(kd), f"--mode={mode}"] + extra
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
    return {
        "cell": name,
        "cmd": [Path(cmd[0]).name] + cmd[1:],
        "mode": mode,
        "tree": str(tree),
        "tree_git": git(tree, "rev-parse", "HEAD") if tree.exists() else None,
        "exit_code": p.returncode,
        "stdout": p.stdout[-4000:],
        "stderr": p.stderr[-16000:],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cells = [
        # --- core matrix ---
        run_cell("ordinary/unpatched", UNP, "ordinary"),
        run_cell("ordinary/patched", PAT, "ordinary"),
        run_cell("positive/unpatched (expected FAIL exit1)", UNP, "positive"),
        run_cell("positive/patched", PAT, "positive"),
        run_cell("negative/unpatched (exact signature)", UNP, "negative"),
        run_cell("negative/patched (must reject expectation)", PAT, "negative"),
        run_cell("with-stl/unpatched", UNP, "with-stl"),
        run_cell("with-stl/patched", PAT, "with-stl"),
        # --- adversarial controls (patched tree) ---
        run_cell("adv: missing kernels dir", PAT, "positive",
                 kernels_dir=Y / "no_such_dir"),
        run_cell("adv: wrong include dir (src/, not kernels/)", PAT, "positive",
                 kernels_dir=PAT / "projects/miopen/src"),
        run_cell("adv: bad arch", PAT, "positive", extra=["--arch=gfx9999"]),
        run_cell("adv: bad mode", PAT, "no-such-mode"),
        run_cell("adv: STL reachable via CPATH -> INCONCLUSIVE", PAT, "positive",
                 extra_env={"CPATH": str(MSVC_INC)}),
    ]

    def expect(c: dict) -> str:
        n, e = c["cell"], c["exit_code"]
        if n.startswith("ordinary") or n.startswith("positive/patched") or \
           n.startswith("with-stl") or n.startswith("negative/unpatched"):
            return "PASS" if e == 0 else "FAIL"
        if n == "positive/unpatched (expected FAIL exit1)":
            return "PASS" if e == 1 else "FAIL"
        if n == "negative/patched (must reject expectation)":
            # exit 1 = FAIL "unexpectedly succeeded" = correctly rejected
            return "PASS" if e == 1 else "FAIL"
        if n.startswith("adv: missing") or n.startswith("adv: wrong") or n == "adv: bad mode":
            return "PASS" if e == 2 else "FAIL"
        if n == "adv: bad arch":
            return "PASS" if e == 1 else "FAIL"
        if n.startswith("adv: STL reachable"):
            return "PASS" if e == 4 else "FAIL"
        return "UNJUDGED"

    verdicts = {c["cell"]: expect(c) for c in cells}
    test_src = PAT / "projects/miopen/test/hiprtc_selfcontained.cpp"
    record = {
        "schema": "phase5_1_ci_matrix_v1",
        "gate": "P51-08",
        "timestamp": datetime.now().isoformat(),
        "test_source": str(test_src),
        "test_source_sha256": sha256(test_src),
        "test_binary": str(TEST),
        "test_binary_sha256": sha256(TEST),
        "hiprtc_dll": str(HIPRTC_DLL),
        "hiprtc_dll_sha256": sha256(HIPRTC_DLL),
        "unpatched_tree_sha": git(UNP, "rev-parse", "HEAD"),
        "patched_tree_sha": git(PAT, "rev-parse", "HEAD"),
        "patch_id": "P5.1-CANDIDATE-R1",
        "arch": "gfx1151",
        "hip_version_macro_src": "HIP_PACKAGE_VERSION_FLAT derived from linked hiprtc (>=7000000000 arm exercised)",
        "cells": cells,
        "verdicts": verdicts,
        "overall": "PASS" if all(v == "PASS" for v in verdicts.values()) else "FAIL",
    }
    dest = OUT / "ci_matrix_phase5_1.json"
    dest.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    for c in cells:
        print(f"{verdicts[c['cell']]:4s}  exit={c['exit_code']}  {c['cell']}")
    print("OVERALL:", record["overall"])
    return 0 if record["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
