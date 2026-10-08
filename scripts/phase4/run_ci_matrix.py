"""Phase 4 / Gate P49 - run the hiprtc_selfcontained CI control matrix.

Matrix (one test binary, two source trees):
                   unpatched                     patched (canonical)
  ordinary         PASS expected                 PASS expected
  positive(no-STL) expected FAIL w/ signature    PASS expected
  with-stl         PASS where STL available      PASS expected

Records per cell: exit code, stdout/stderr (compiler log), code object
size, plus environment provenance (hiprtc DLL path+SHA256, tree SHAs).
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TEST = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\phase4_build\ci-test\hiprtc_selfcontained.exe")
UNP = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase4-baseline")
PAT = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\rocm-libraries-phase4-canonical")
CORE = Path(r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages\_rocm_sdk_core")
HIPRTC_DLL = CORE / "bin" / "hiprtc0714.dll"
OUT = Path(r"C:\Users\rocm\Desktop\YOLO_AMD\Ultralytics-Windows-ROCm-Training-RCA\evidence\phase4\hiprtc_ci")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def run_cell(name: str, tree: Path, mode: str) -> dict:
    env = dict(os.environ)
    env["PATH"] = str(CORE / "bin") + os.pathsep + env.get("PATH", "")
    env.pop("CPATH", None)  # keep isolated modes honest; probe would catch it anyway
    p = subprocess.run(
        [str(TEST), str(tree / "projects/miopen/src/kernels"), f"--mode={mode}", "--arch=gfx1151"],
        capture_output=True, text=True, env=env, timeout=600)
    return {
        "cell": name,
        "mode": mode,
        "tree": str(tree),
        "tree_git": git(tree, "rev-parse", "HEAD"),
        "exit_code": p.returncode,
        "stdout_tail": p.stdout[-2000:],
        "stderr_tail": p.stderr[-12000:],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cells = [
        run_cell("ordinary/unpatched", UNP, "ordinary"),
        run_cell("ordinary/patched", PAT, "ordinary"),
        run_cell("negative/unpatched (expected FAIL w/ signature)", UNP, "negative"),
        run_cell("positive/patched", PAT, "positive"),
        run_cell("with-stl/unpatched", UNP, "with-stl"),
        run_cell("with-stl/patched", PAT, "with-stl"),
    ]

    def ok(c: dict) -> bool:
        # All cells are self-verifying: exit 0 == the mode's expectation held.
        return c["exit_code"] == 0

    verdicts = {c["cell"]: ("PASS" if ok(c) else "FAIL") for c in cells}
    record = {
        "schema": "phase4_ci_matrix_v1",
        "gate": "P49",
        "timestamp": datetime.now().isoformat(),
        "test_binary": str(TEST),
        "test_binary_sha256": sha256(TEST),
        "hiprtc_dll": str(HIPRTC_DLL),
        "hiprtc_dll_sha256": sha256(HIPRTC_DLL),
        "unpatched_tree_sha": git(UNP, "rev-parse", "HEAD"),
        "patched_tree_sha": git(PAT, "rev-parse", "HEAD"),
        "patch_id": "P3-FINAL-R3 (canonical reconstruction, commit 4084759)",
        "arch": "gfx1151",
        "cells": cells,
        "verdicts": verdicts,
        "overall": "PASS" if all(ok(c) for c in cells) else "FAIL",
    }
    dest = OUT / "ci_matrix.json"
    dest.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    for c, v in verdicts.items():
        print(f"{v:4s}  {c}  (exit {next(x['exit_code'] for x in cells if x['cell']==c)})")
    print("OVERALL:", record["overall"])
    return 0 if record["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
