# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""MIOpen binary-provenance verifier (mission §5 / R21.1 TASK C) — runs INSIDE
the target venv.

Collects A–J evidence and FAILS CLOSED:
  - official classification requires a resolved lock whose channel URL is the
    EXACT official channel (never a substring), a SHA256 for every gpu-stack
    wheel, and version consistency between lock and installed metadata;
  - a positive #13437 marker is a SCREENING signal only — official PASS
    additionally requires published source ancestry proving the loaded build
    descends from merged fix commit f0a5d266 (--ancestry-evidence);
  - any detected workaround forces ENGINEERING_REFERENCE; a missing lineage is
    PROVENANCE_INCOMPLETE and can never yield OFFICIAL_STABLE.

    python verify_provenance.py --lock resolved_wheel_lock.json \
        --ancestry-evidence r22_channel_binary_audit.json --out prov.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_lib  # noqa: E402

MERGED_FIX_COMMIT = "f0a5d2664cf3334161f7b82c02dfcd2213988a8a"
# packages that make up the AMD gpu stack (vendor-validated)
GPU_STACK_PREFIXES = ("torch", "torchvision", "rocm", "amd-torch")


def wheel_record_for(dist_name: str, lock: dict | None) -> dict | None:
    if not lock:
        return None
    for p in lock["packages"]:
        if p["name"].lower().replace("-", "_") == dist_name.lower().replace("-", "_"):
            return p
    return None


def evaluate_lineage(miopen: dict | None, ancestry_audit: dict | None) -> dict:
    """Source-ancestry evaluation (pure; unit-tested).

    A positive marker NEVER suffices: official classes require an ancestry
    record for the loaded build proving descent from MERGED_FIX_COMMIT with
    behind_by == 0. Returns a status in
      ANCESTRY_VERIFIED | FIX_ABSENT | MARKER_ONLY_LINEAGE_UNPROVEN |
      NO_BUILD_IDENTITY | ANCESTRY_BEHIND | ANCESTRY_BASE_MISMATCH |
      ANCESTRY_FOR_OTHER_BUILD | ANCESTRY_ABSENT
    plus provenance_complete (bool) — True only for ANCESTRY_VERIFIED.
    """
    miopen = miopen or {}
    marker = miopen.get("pr13437_marker_miopen_initializer_list", 0) or 0
    vs = miopen.get("embedded_version_strings") or []
    build_commit = None
    if vs:
        m = re.match(r"3\.\d+\.\d+\.([0-9a-f]{7,12})", sorted(vs)[-1])
        if m:
            build_commit = m.group(1)

    out = {
        "merged_fix_commit": MERGED_FIX_COMMIT,
        "build_commit_string": build_commit,
        "marker_miopen_initializer_list": marker,
        "provenance_complete": False,
        "note": "marker is a screening signal only; official PASS additionally "
                "requires published ancestry (behind_by==0 vs merged fix) and "
                "the runtime no-STL behavioral gate (verify_miopen_nostl.py)",
    }
    if marker == 0:
        out["status"] = "FIX_ABSENT"          # pre-fix bytes identified as such
        return out
    if not build_commit:
        out["status"] = "NO_BUILD_IDENTITY"
        return out
    if not ancestry_audit:
        out["status"] = "ANCESTRY_ABSENT"     # marker>0 but no published lineage
        return out
    base = (ancestry_audit.get("merged_fix_commit") or "").lower()
    if base != MERGED_FIX_COMMIT:
        out["status"] = "ANCESTRY_BASE_MISMATCH"
        return out
    # match the audit entry to THIS build: loaded dll sha256 or build commit
    entries = ancestry_audit.get("audits") or []
    entry = next((e for e in entries
                  if (e.get("miopen_dll", {}).get("sha256") or "").lower()
                  == (miopen.get("sha256") or "").lower()
                  and miopen.get("sha256")), None)
    if entry is None:
        entry = next((e for e in entries
                      if e.get("miopen_dll", {}).get("build_commit")
                      == build_commit
                      or ((e.get("miopen_dll_loaded_in_venv") or {})
                          .get("build_commit") == build_commit)), None)
    if entry is None:
        out["status"] = "ANCESTRY_FOR_OTHER_BUILD"  # audit proves a different wheel
        return out
    anc = entry.get("ancestry") or {}
    if anc.get("behind_by") not in (0, None) and anc.get("behind_by") != 0:
        out["status"] = "ANCESTRY_BEHIND"     # branch cut before the fix merge
        out["ancestry"] = anc
        return out
    if anc.get("status") not in ("ahead", "diverged") or "behind_by" not in anc:
        out["status"] = "ANCESTRY_BEHIND"
        out["ancestry"] = anc
        return out
    out["status"] = "ANCESTRY_VERIFIED"
    out["ancestry"] = anc
    out["provenance_complete"] = True
    return out


def audit_lock(lock: dict | None, installed: dict, channel: str | None) -> dict:
    """Lock-vs-installed consistency + exact-channel + SHA256 audit (TASK C).

    Returns per-check results; `ok` is True only when every check passes.
    Missing lock (None) fails every check (fail-closed).
    """
    res: dict = {"lock_present": bool(lock)}
    if not lock:
        res["ok"] = False
        res["failures"] = ["no resolved wheel lock supplied — official "
                           "classification impossible"]
        return res
    fails: list[str] = []
    chan = channel or lock.get("channel")
    res["channel"] = chan
    res["channel_exact_official"] = (chan in gp_lib.OFFICIAL_CHANNELS
                                     and lock.get("channel_url")
                                     == gp_lib.OFFICIAL_CHANNELS.get(chan))
    if not res["channel_exact_official"]:
        fails.append(f"channel {chan!r}/URL {lock.get('channel_url')!r} is not "
                     "the exact official channel")

    lock_by_name = {p["name"].lower().replace("-", "_"): p
                    for p in lock.get("packages", [])}
    sha_re = re.compile(r"^[0-9a-f]{64}$")
    coverage, mismatches, bad_sha, sha_verified = [], [], [], []
    for name, ver in sorted(installed.items()):
        if not name.startswith(GPU_STACK_PREFIXES):
            continue
        rec = lock_by_name.get(name.replace("-", "_"))
        if rec is None:
            coverage.append({"package": name, "in_lock": False})
            fails.append(f"gpu-stack package {name}=={ver} absent from lock")
            continue
        coverage.append({"package": name, "in_lock": True})
        if str(rec.get("version")) != str(ver):
            mismatches.append({"package": name, "lock": rec.get("version"),
                               "installed": ver})
            fails.append(f"{name}: lock {rec.get('version')} != installed {ver}")
        if not sha_re.match(str(rec.get("sha256") or "")):
            bad_sha.append(name)
            fails.append(f"{name}: lock entry has no valid SHA256")
        lp = rec.get("local_path")
        if lp and Path(lp).is_file():
            actual = gp_lib.sha256_file(Path(lp))
            ok = actual.lower() == str(rec.get("sha256")).lower()
            sha_verified.append({"package": name, "wheel_sha256_matches_lock": ok})
            if not ok:
                fails.append(f"{name}: downloaded wheel SHA256 != lock SHA256")
        else:
            sha_verified.append({"package": name,
                                 "wheel_sha256_matches_lock": None,
                                 "reason": "local wheel file unavailable"})
    res["gpu_stack_coverage"] = coverage
    res["version_consistency"] = mismatches
    res["sha256_recorded"] = bad_sha
    res["wheel_sha256_verification"] = sha_verified
    res["ok"] = not fails
    res["failures"] = fails
    return res


def main() -> None:
    import torch  # inside target venv
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lock", default=None, help="resolved_wheel_lock.json")
    ap.add_argument("--ancestry-evidence", default=None,
                    help="channel binary audit JSON with compare-API ancestry")
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mission", default="R21")
    ap.add_argument("--channel", default=None)
    args = ap.parse_args()

    import time
    t0 = time.time()
    lock = json.loads(Path(args.lock).read_text(encoding="utf-8")) if args.lock else None
    ancestry_audit = None
    if args.ancestry_evidence:
        ap = Path(args.ancestry_evidence)
        if ap.is_file():  # absent file = no published lineage (fail-closed below)
            ancestry_audit = json.loads(ap.read_text(encoding="utf-8"))
    channel = args.channel or (lock or {}).get("channel")

    installed = {}
    for d in im.distributions():
        name = (d.metadata["Name"] or "").lower()
        if name:
            installed[name] = d.version

    # embedded MIOpen.dll in the installed rocm-sdk-libraries dist
    embedded = {}
    lib_dist = None
    for d in im.distributions():
        if (d.metadata["Name"] or "").lower() in ("rocm-sdk-libraries", "rocm_sdk_libraries"):
            lib_dist = d
            break
    if lib_dist is not None:
        f = lib_dist.locate_file("_rocm_sdk_libraries/bin/MIOpen.dll")
        if Path(str(f)).is_file():
            f = Path(str(f))
            embedded = {"path": str(f), "sha256": gp_lib.sha256_file(f)}
            blob = f.read_bytes()
            embedded["version_strings"] = [v.decode() for v in sorted(set(
                re.findall(rb"3\.[0-9]+\.[0-9]+\.[0-9a-f]{7,12}", blob)))]
            embedded["pr13437_marker"] = blob.count(gp_lib.FIX_MARKER)

    # actually-loaded DLL (in this process, after a CUDA op forces MIOpen init)
    x = torch.rand(8, 8, device="cuda")
    (x @ x).sum().item()
    miopen = gp_lib.loaded_miopen_identity()

    workarounds = gp_lib.detect_workarounds()
    lock_audit = audit_lock(lock, installed, channel)
    lineage = evaluate_lineage(miopen, ancestry_audit)

    if workarounds.get("any_workaround_present"):
        runtime_class = "ENGINEERING_REFERENCE"
    elif not miopen.get("loaded"):
        runtime_class = "INCONCLUSIVE"
    elif channel == "stable":
        runtime_class = ("OFFICIAL_STABLE" if lineage["provenance_complete"]
                         else "INCONCLUSIVE")
    elif channel in ("dev", "nightly", "rc"):
        runtime_class = ("OFFICIAL_CANDIDATE" if lineage["provenance_complete"]
                         else "INCONCLUSIVE")
    elif (miopen.get("pr13437_marker_miopen_initializer_list", 0) or 0) == 0:
        runtime_class = "OFFICIAL_PRE_FIX"   # pre-fix bytes on an unlabelled stack
    else:
        runtime_class = "INCONCLUSIVE"       # post-fix marker, unknown channel

    # official classes additionally require the lock audit to be clean
    official = runtime_class in ("OFFICIAL_STABLE", "OFFICIAL_CANDIDATE")
    if official and not lock_audit.get("ok"):
        runtime_class = "INCONCLUSIVE"

    provenance_status = ("PROVENANCE_COMPLETE" if lineage["provenance_complete"]
                         else "PROVENANCE_INCOMPLETE")
    record = {
        "run_id": args.run_id, "mission": args.mission, "timestamp": gp_lib.now_utc(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
        "gfx_target": None, "windows_build": gp_lib.windows_build(),
        "driver_version": gp_lib.gpu_driver_facts().get("DriverVersion"),
        "python": sys.version.split()[0], "torch": torch.__version__,
        "torchvision": im.version("torchvision") if _has(im, "torchvision") else None,
        "hip": torch.version.hip,
        "runtime_class": runtime_class,
        "command": f"python {Path(__file__).name} --lock {args.lock or '-'}",
        "exit_code": 0, "duration_s": round(time.time() - t0, 2),
        "pass_fail_skip": ("PASS" if runtime_class in ("OFFICIAL_STABLE",
                                                       "OFFICIAL_CANDIDATE",
                                                       "ENGINEERING_REFERENCE",
                                                       "OFFICIAL_PRE_FIX")
                           else "FAIL"),
        "failure_classification": (None if runtime_class != "INCONCLUSIVE"
                                   else "INCONCLUSIVE"),
        "raw_log_path": str(Path(args.out).with_suffix(".log")),
        "installed_versions": installed,
        "wheel_lock": [{"name": p["name"], "version": p["version"], "sha256": p["sha256"],
                        "url": p["url"]} for p in (lock or {}).get("packages", [])],
        "lock_audit": lock_audit,
        "ancestry_evidence_file": args.ancestry_evidence,
        "embedded_miopen_dll": embedded,
        "loaded_miopen_dll": miopen,
        "workarounds": workarounds,
        "source_lineage": lineage,
        "provenance_status": provenance_status,
        "behavioral_evidence_required": ("verify_miopen_nostl.py official leg "
                                         "OFFICIAL_*_PASS — G0 alone never proves "
                                         "the fix behaviorally"),
    }
    record["gfx_target"] = gp_lib.gfx_from_device_name(record["gpu_name"] or "")
    gp_lib.write_evidence(record, Path(args.out))
    print(json.dumps({k: record[k] for k in ("run_id", "runtime_class",
                                             "provenance_status", "source_lineage",
                                             "lock_audit", "workarounds", "loaded_miopen_dll")},
                     indent=2, default=str)[:6000])
    print(f"VERIFY_PROVENANCE: {record['runtime_class']}")


def _has(im, pkg):
    try:
        im.version(pkg)
        return True
    except im.PackageNotFoundError:
        return False


if __name__ == "__main__":
    main()
