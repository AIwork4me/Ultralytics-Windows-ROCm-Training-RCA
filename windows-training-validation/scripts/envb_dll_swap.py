"""Swap the source-built patched MIOpen.dll into the disposable env-B, or restore it.

Actions:
  swap-in    b58m build output MIOpen.dll (SOURCE_BUILT_PATCHED, sha ed7c67a9...) -> env-B bin
  restore    env-B MIOpen.dll.official.bak (OFFICIAL, sha e97891df...)            -> env-B bin

Every step hash-verifies before and after; refuses to touch anything whose
hash doesn't match expectations. State transition is recorded as JSON.

    python scripts/envb_dll_swap.py --action swap-in|restore --state-file ../environment/ENVB_DLL_STATE.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PATCHED_DLL = Path(r"C:\b58m\bin\MIOpen.dll")
PATCHED_SHA256 = "ed7c67a909307b211bbda260eeda7f6bce17cc7d097b6b1f74f8270456e6179a"
OFFICIAL_SHA256 = "e97891df7ea0ba2b6eda703bd69499521dc9a38300fe626f412b5544dec647bc"
ENVB_BIN = Path(r"C:\Users\rocm\miniconda3\envs\pm13437_merged\Lib\site-packages\_rocm_sdk_libraries\bin")
TARGET = ENVB_BIN / "MIOpen.dll"
BACKUP = ENVB_BIN / "MIOpen.dll.official.bak"


def fail(msg: str) -> None:
    print(f"SWAP-FAIL: {msg}", file=sys.stderr)
    sys.exit(2)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=["swap-in", "restore"], required=True)
    parser.add_argument("--state-file", required=True)
    args = parser.parse_args()

    if sha(PATCHED_DLL) != PATCHED_SHA256:
        fail(f"source-built DLL identity changed: {PATCHED_DLL}")
    if sha(BACKUP) != OFFICIAL_SHA256:
        fail(f"official backup identity changed: {BACKUP}")

    before = sha(TARGET)
    if args.action == "swap-in":
        if before != OFFICIAL_SHA256:
            fail(f"env-B target is not at official baseline ({before}); refusing to swap")
        shutil.copy2(PATCHED_DLL, TARGET)
    else:
        if before != PATCHED_SHA256 and before != OFFICIAL_SHA256:
            fail(f"env-B target in unknown state ({before}); refusing to restore")
        shutil.copy2(BACKUP, TARGET)
    after = sha(TARGET)
    expected = PATCHED_SHA256 if args.action == "swap-in" else OFFICIAL_SHA256
    if after != expected:
        fail(f"post-action hash mismatch: got {after}, expected {expected}")

    state = {"action": args.action, "utc": datetime.now(timezone.utc).isoformat(),
             "before_sha256": before, "after_sha256": after,
             "env_b_dll_now": "SOURCE_BUILT_PATCHED" if args.action == "swap-in" else "OFFICIAL_WHEEL",
             "target": str(TARGET)}
    sf = Path(args.state_file)
    sf.parent.mkdir(parents=True, exist_ok=True)
    # append transition history (audit fix A-F2: the file previously held only the
    # latest action, so the swap-in record survived only via a git commit)
    history = []
    if sf.is_file():
        try:
            prev = json.loads(sf.read_text(encoding="utf-8"))
            history = prev.get("history", [])
            if prev.get("action"):          # legacy single-action record
                history = history + [prev]
        except json.JSONDecodeError:
            pass
    state["history"] = history[-19:]        # cap the chain, newest last
    sf.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
