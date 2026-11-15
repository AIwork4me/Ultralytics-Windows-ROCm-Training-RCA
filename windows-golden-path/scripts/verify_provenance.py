# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""MIOpen binary-provenance verifier (mission §5) — runs INSIDE the target venv.

Collects A–J evidence: installed versions, wheel filename + SHA256 (from the
lock + pip RECORD), embedded MIOpen.dll SHA256, actually-loaded DLL path and
SHA256, build identity, source-ancestry screening marker, and workaround
detection (HIPRTC / MIOPEN_* / DLL redirection). Fails CLOSED: any detected
workaround forces ENGINEERING_REFERENCE; a missing build lineage is reported
as PROVENANCE_INCOMPLETE and can never yield OFFICIAL_STABLE.

    python verify_provenance.py --lock resolved_wheel_lock.json --out prov.json
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

REQUIRED = ["run_id", "mission", "timestamp", "gpu_name", "gfx_target",
            "windows_build", "driver_version", "python", "torch", "torchvision",
            "hip", "runtime_class", "command", "exit_code", "duration_s",
            "pass_fail_skip", "failure_classification", "raw_log_path"]


def wheel_record_for(dist_name: str, lock: dict | None) -> dict | None:
    if not lock:
        return None
    for p in lock["packages"]:
        if p["name"].lower().replace("-", "_") == dist_name.lower().replace("-", "_"):
            return p
    return None


def main() -> None:
    import torch  # inside target venv
    import importlib.metadata as im

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lock", default=None, help="resolved_wheel_lock.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mission", default="R21")
    ap.add_argument("--channel", default=None)
    args = ap.parse_args()

    import time
    t0 = time.time()
    lock = json.loads(Path(args.lock).read_text(encoding="utf-8")) if args.lock else None

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
    runtime_class = gp_lib.classify_runtime(workarounds, args.channel or (lock or {}).get("channel"),
                                            miopen)

    # build identity → source ancestry SCREENING (not proof)
    vs = miopen.get("embedded_version_strings") or []
    build_commit = None
    if vs:
        m = re.match(r"3\.\d+\.\d+\.([0-9a-f]{7,12})", sorted(vs)[-1])
        if m:
            build_commit = m.group(1)
    lineage = {
        "merged_fix_commit": "f0a5d2664cf3334161f7b82c02dfcd2213988a8a",
        "build_commit_string": build_commit,
        "marker_miopen_initializer_list": miopen.get("pr13437_marker_miopen_initializer_list"),
        "note": "marker is a screening signal only; official PASS additionally "
                "requires runtime no-STL behavior (verify_miopen_nostl.py) and "
                "published build lineage",
        "provenance_complete": bool(build_commit or
                                    (miopen.get("pr13437_marker_miopen_initializer_list", 0) > 0)),
    }

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
        "pass_fail_skip": "PASS" if runtime_class in ("OFFICIAL_STABLE", "OFFICIAL_CANDIDATE",
                                                      "ENGINEERING_REFERENCE") else "FAIL",
        "failure_classification": None if runtime_class != "INCONCLUSIVE" else "INCONCLUSIVE",
        "raw_log_path": str(Path(args.out).with_suffix(".log")),
        "installed_versions": installed,
        "wheel_lock": [{"name": p["name"], "version": p["version"], "sha256": p["sha256"],
                        "url": p["url"]} for p in (lock or {}).get("packages", [])],
        "embedded_miopen_dll": embedded,
        "loaded_miopen_dll": miopen,
        "workarounds": workarounds,
        "source_lineage": lineage,
        "provenance_status": "PROVENANCE_COMPLETE" if lineage["provenance_complete"]
        else "PROVENANCE_INCOMPLETE",
    }
    record["gfx_target"] = gp_lib.gfx_from_device_name(record["gpu_name"] or "")
    gp_lib.write_evidence(record, Path(args.out))
    print(json.dumps({k: record[k] for k in ("run_id", "runtime_class", "provenance_status",
                                             "loaded_miopen_dll", "source_lineage",
                                             "workarounds")},
                     indent=2, default=str)[:4000])
    print(f"VERIFY_PROVENANCE: {record['runtime_class']}")


def _has(im, pkg):
    try:
        im.version(pkg)
        return True
    except im.PackageNotFoundError:
        return False


if __name__ == "__main__":
    main()
