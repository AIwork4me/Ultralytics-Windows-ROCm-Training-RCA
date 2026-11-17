# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Archive R21/R22-candidate evidence from the workspace into the RCA repo.

Copies evidence JSONs + raw logs, extends evidence/manifest.json (append-only),
writes SHA256SUMS per evidence dir. Never touches existing P13-P19B entries.

    python scripts/r21/archive_evidence.py --repo <rca-root> \
        --workspace C:/RadeonYOLO [--skip-r22dev]
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "windows-golden-path" / "scripts"))
import gp_lib  # noqa: E402

R21_JSONS = [
    "R21_ENVIRONMENT_BASELINE.json", "r21A_provenance.json", "r21A2_torch_gates.json",
    "r21D1_nostl_official.json", "r21D2_nostl_engref.json", "r21E1_train_cli.json",
    "r21E2_optimizer.json", "r21E3_resume.json", "r21F_stability.json",
    "r21-engref-lock.json",
]
R22DEV_JSONS = [
    "r22cA_provenance.json", "r22cB_torch_gates.json", "r22cC_nostl.json",
    "r22cD_train_cli.json", "r22cE_optimizer.json", "r22cF_resume.json",
    "r22cG_stability.json", "r22cG2_stability_cold.json",
    # clean (shim-stripped) rerun set — the authoritative candidate evidence
    "r22cA2_provenance_clean.json", "r22cB2_torch_gates_clean.json",
    "r22cD2_train_cli_clean.json", "r22cE2_optimizer_clean.json",
    "r22cF2_resume_clean.json", "r22cG3_stability_clean_cold.json",
    "r22_channel_binary_audit.json",
]
KEY_LOGS = {
    "r21E1_train_cli.json": ["logs/r21E1_train.log"],
    "r21E3_resume.json": ["logs/r21E3.log"],
    "r22cC_nostl.json": ["logs/r22cC.log"],
    "r22cD_train_cli.json": ["logs/r22cD.log"],
}
# raw scratch logs worth keeping verbatim (full training stdout etc.)
RAW_COPIES = [
    ("scratch/train-R21E1f/train_stdout.log", "r21E1_train_stdout.log"),
    ("scratch/train-R21E1f/checkpoints.json", "r21E1_checkpoints.json"),
]


def manifest_entry(repo_rel: str, src: Path, command: str) -> dict:
    return {"path": repo_rel,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "command": command,
            "sha256": gp_lib.sha256_file(src),
            "size_bytes": src.stat().st_size}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--workspace", default="C:/RadeonYOLO")
    ap.add_argument("--skip-r22dev", action="store_true")
    args = ap.parse_args()
    repo = Path(args.repo)
    ws = Path(args.workspace)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    targets = [("evidence/raw/r21", ws / "evidence/r21", R21_JSONS)]
    if not args.skip_r22dev:
        targets.append(("evidence/raw/r22-dev", ws / "evidence/r22-dev", R22DEV_JSONS))

    new_entries = []
    for repo_dir, src_dir, names in targets:
        dst = repo / repo_dir
        dst.mkdir(parents=True, exist_ok=True)
        for name in names:
            src = src_dir / name
            if not src.is_file():
                print(f"[warn] missing (skipped): {src}")
                continue
            shutil.copy2(src, dst / name)
            new_entries.append(manifest_entry(f"{repo_dir}/{name}", src,
                                              f"archived {stamp} (R21 mission)"))
        # channel scan artifacts (r21)
        scan = ws / "evidence/r21/wheel-scan"
        if scan.is_dir() and repo_dir.endswith("r21"):
            sdst = dst / "wheel-scan"
            sdst.mkdir(exist_ok=True)
            for f in scan.glob("*.json"):
                shutil.copy2(f, sdst / f.name)
                new_entries.append(manifest_entry(f"{repo_dir}/wheel-scan/{f.name}", f,
                                                  "discover_official_wheels.py (R21)"))
        # key logs
        for jname, logs in KEY_LOGS.items():
            for lrel in logs:
                lsrc = ws / lrel
                if lsrc.is_file():
                    ldst = dst / (Path(jname).stem + ".log")
                    shutil.copy2(lsrc, ldst)
                    new_entries.append(manifest_entry(f"{repo_dir}/{ldst.name}", lsrc,
                                                      "raw log companion"))
        # SHA256SUMS per dir (only files we archived there)
        sums = []
        for f in sorted(dst.rglob("*")):
            if f.is_file() and f.name != "SHA256SUMS.txt":
                sums.append(f"{gp_lib.sha256_file(f)}  {f.relative_to(dst)}")
        (dst / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

    for src_rel, dst_name in RAW_COPIES:
        src = ws / src_rel
        if src.is_file():
            dst = repo / "evidence/raw/r21" / dst_name
            shutil.copy2(src, dst)
            new_entries.append(manifest_entry(f"evidence/raw/r21/{dst_name}", src,
                                              "R21 raw scratch copy"))

    # append-only manifest extension
    mpath = repo / "evidence/manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    known = {e["path"] for e in manifest}
    added = 0
    for e in new_entries:
        if e["path"] not in known:
            manifest.append(e)
            known.add(e["path"])
            added += 1
    mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] archived {added} new manifest entries (total {len(manifest)})")


if __name__ == "__main__":
    main()
