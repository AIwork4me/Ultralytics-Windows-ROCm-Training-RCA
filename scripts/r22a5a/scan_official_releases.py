# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5A Phase A — multi-channel official Windows release scanner.

REUSES the R21 discovery layer unchanged (windows-golden-path/scripts/
discover_official_wheels.py::scan_channel) for the five AMD channel indexes,
then adds the layers it lacked:

  1. TheRock release tags (gh api, metadata only) + rocm-libraries submodule
     ancestry vs merged fix commit f0a5d266 (never date inference);
  2. download.pytorch.org torch index ROCm-Windows appearance check;
  3. mission §4.3 classification of EVERY discovered artifact via
     r22a5a_lib.classify_channel_artifact (frozen-anchor reuse for already
     audited bytes; NEW artifacts stay NEW_ARTIFACT_PROVENANCE_PENDING);
  4. deterministic machine-readable output separating the observation
     envelope (timestamps, tool identity, channel errors) from the sorted,
     normalized candidate list.

    python scripts/r22a5a/scan_official_releases.py \
        --out release-provenance/r22a5a/latest_official_windows_candidates.json

Exit 0 = scan completed (channel outages are recorded, they do not fail the
scan — BLOCKED_NETWORK is a per-channel fact). Exit 2 = usage/IO error.
This is the LIVE integration layer: unit tests exercise the pure classifier
with fixtures and never touch the network.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import r22a5a_lib as lib  # noqa: E402

sys.path.insert(0, str(_HERE.parent.parent / "windows-golden-path" / "scripts"))
import discover_official_wheels as dow  # noqa: E402  (R21 layer, reused)
import gp_lib  # noqa: E402

PYTORCH_TORCH_INDEX = "https://download.pytorch.org/whl/torch/"
THEROCK_REPO = "ROCm/TheRock"
ROCM_LIBRARIES_REPO = "ROCm/rocm-libraries"
MAX_THEROCK_TAGS = 5   # bounded metadata evaluation (latest releases first)
GH_TIMEOUT_S = 45


def gh_api(endpoint: str, retries: int = 2) -> tuple[dict | list | None, str | None]:
    """Bounded `gh api` call with explicit error recording (no silent retry)."""
    cmd = ["gh", "api", endpoint]
    for attempt in range(retries + 1):
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=GH_TIMEOUT_S,
                               encoding="utf-8", errors="replace")
            if r.returncode == 0:
                return json.loads(r.stdout), None
            err = f"gh exit {r.returncode}: {r.stderr.strip()[-300:]}"
        except subprocess.TimeoutExpired:
            err = f"gh api timeout after {GH_TIMEOUT_S}s"
        except Exception as e:  # noqa: BLE001 — recorded as a source fact
            err = f"{type(e).__name__}: {e}"
        if attempt < retries:
            continue
    return None, err


def scan_therock_releases() -> dict:
    """TheRock release tags + per-tag rocm-libraries ancestry vs the fix.

    Metadata only; every failure is recorded and fail-closed (UNKNOWN, never
    a date-based guess)."""
    out: dict = {"repo": THEROCK_REPO, "tags": [], "errors": []}
    rel, err = gh_api(f"repos/{THEROCK_REPO}/releases?per_page={MAX_THEROCK_TAGS}")
    if err or not isinstance(rel, list):
        out["errors"].append({"step": "releases", "error": err or "empty response"})
        return out
    for r in rel:
        tag = {"tag_name": r.get("tag_name"),
               "published_at": r.get("published_at"),
               "prerelease": bool(r.get("prerelease")),
               "url": r.get("html_url")}
        # submodule pointer at the tag
        sub, serr = gh_api(f"repos/{THEROCK_REPO}/contents/rocm-libraries"
                           f"?ref={tag['tag_name']}")
        if serr or not isinstance(sub, dict):
            tag["submodule_error"] = serr or "unexpected contents response"
            out["tags"].append(lib.therock_tag_fix_facts(tag))
            continue
        pointer = sub.get("sha") if sub.get("type") == "submodule" else sub.get("sha")
        tag["submodule_pointer"] = pointer
        if pointer:
            cmp_, cerr = gh_api(
                f"repos/{ROCM_LIBRARIES_REPO}/compare/"
                f"{lib.MERGED_FIX_COMMIT}...{pointer}")
            if cerr or not isinstance(cmp_, dict):
                tag["compare_error"] = cerr or "unexpected compare response"
            else:
                tag["compare"] = {"status": cmp_.get("status"),
                                  "ahead_by": cmp_.get("ahead_by"),
                                  "behind_by": cmp_.get("behind_by")}
        out["tags"].append(lib.therock_tag_fix_facts(tag))
    return out


def scan_pytorch_official_index() -> dict:
    """download.pytorch.org torch index: any ROCm WINDOWS wheel? (R20 audit
    note A-F6 — a future appearance is a new channel to classify.)"""
    code, html, err = dow.fetch(PYTORCH_TORCH_INDEX, timeout=60)
    hrefs = dow.parse_index_hrefs(html) if html else []
    rocm_win = [h.rsplit("/", 1)[-1] for h in hrefs
                if "rocm" in h.lower() and "win_amd64" in h]
    return {"index": PYTORCH_TORCH_INDEX, "status": code,
            "error": err,
            "rocm_windows_wheels": sorted(set(rocm_win))[:20],
            "verdict": ("NEW_ROCM_WINDOWS_CHANNEL" if rocm_win else
                        "NO_ROCM_WINDOWS_WHEELS" if not err else "BLOCKED_NETWORK")}


def normalize_candidates(discovery: dict, audits: dict | None) -> list[dict]:
    """Deterministic normalized candidate rows.

    Emission rule: one row per NEWEST wheel of each (channel, package,
    python_tag) group — the classified FRONTIER — plus a compact
    all_win_versions summary per (channel, package). Historical listings
    below the frontier are summarized, not enumerated (the full inventory
    stays in the optional --full dump). Envelope timestamps live in the
    envelope only."""
    audits = audits or {}
    rows: list[dict] = []
    for ch_name, ch in sorted(discovery.get("channels", {}).items()):
        reachable = ch.get("root_status") == 200
        for pkg, entry in sorted(ch.get("packages", {}).items()):
            wheels = entry.get("windows_wheels") or []
            all_vers = sorted({lib.decode_version(w["version"]) for w in wheels})
            if not wheels:
                rows.append({
                    "channel": ch_name, "package": pkg, "version": None,
                    "python_tag": None,
                    "classification": ("BLOCKED_NETWORK" if not reachable else
                                       "NO_NEW_ARTIFACT"),
                    "reason": ("channel index unreachable" if not reachable else
                               "package not listed for win_amd64 on this channel"),
                    "index_url": ch.get("base_url"),
                    "all_win_versions": [],
                })
                continue
            # frontier: newest wheel per python tag (decode for ordering)
            groups: dict[str, dict] = {}
            for w in wheels:
                tag = w.get("python_tag") or "?"
                cur = groups.get(tag)
                if cur is None or (lib.version_sort_key(w["version"]),
                                   w["filename"]) > \
                        (lib.version_sort_key(cur["version"]), cur["filename"]):
                    groups[tag] = w
            for tag in sorted(groups):
                w = groups[tag]
                parsed = gp_lib.parse_wheel_filename(w["filename"])
                audit = audits.get((ch_name, gp_lib.dist_key(pkg),
                                    lib.decode_version(w["version"])))
                cls = lib.classify_channel_artifact(
                    ch_name, pkg, w["version"], audit=audit,
                    channel_reachable=reachable,
                    metadata_ok=bool(parsed and parsed.get("version")),
                    wheel_sha256=(audit or {}).get("wheel_sha256"))
                rows.append({
                    "channel": ch_name,
                    "package": pkg,
                    "version": lib.decode_version(w["version"]),
                    "wheel_filename": w["filename"],
                    "python_tag": tag,
                    "platform": "win_amd64",
                    "wheel_url": w.get("wheel_url"),
                    "page_url": w.get("page_url"),
                    "classification": cls["classification"],
                    "reason": cls.get("reason"),
                    "anchor": cls.get("anchor"),
                    "fix_screening_marker": (audit or {}).get(
                        "marker_miopen_initializer_list") if audit else None,
                    "requires_provenance_work": cls["classification"] in (
                        "NEW_ARTIFACT_PROVENANCE_PENDING",
                        "BINARY_PROVENANCE_INCONCLUSIVE"),
                    "gpu_arch_coverage": ("gfx1100+gfx1151"
                                          if pkg in ("rocm-sdk-device-gfx1100",
                                                     "rocm-sdk-device-gfx1151",
                                                     "amd-torch-device-gfx1100",
                                                     "amd-torch-device-gfx1151",
                                                     "amd-torchvision-device-gfx1100",
                                                     "amd-torchvision-device-gfx1151")
                                          else None),
                    "all_win_versions": all_vers if tag == sorted(groups)[0] else None,
                })
    return sorted(rows, key=lambda r: (r["channel"], r["package"],
                                       str(r["version"]), str(r.get("wheel_filename"))))


def load_audits(paths: list[str]) -> dict:
    """Fold audit_wheel_provenance outputs into a lookup keyed by
    (channel, package, decoded version) → fresh-audit facts."""
    audits: dict = {}
    for p in paths:
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 — recorded, never fatal
            print(f"[warn] audit file {p} unreadable: {e}", file=sys.stderr)
            continue
        for a in d.get("audits", []):
            dll = a.get("miopen_dll") or {}
            anc = a.get("ancestry") or {}
            audits[(a.get("channel"), gp_lib.dist_key(a.get("package") or ""),
                    lib.decode_version(a.get("wheel_version") or ""))] = {
                "marker_miopen_initializer_list": dll.get(
                    "marker_miopen_initializer_list"),
                "ancestry_status": anc.get("status"),
                "ancestry_behind_by": anc.get("behind_by"),
                "wheel_sha256": a.get("wheel_sha256"),
                "miopen_dll_sha256": dll.get("sha256"),
                "audit_source": str(p),
            }
    return audits


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--channels", default=",".join(gp_lib.OFFICIAL_CHANNELS))
    ap.add_argument("--skip-therock", action="store_true",
                    help="skip TheRock github metadata (offline CI use)")
    ap.add_argument("--full", default=None,
                    help="optional path for the full wheel_discovery.json dump")
    ap.add_argument("--audit", action="append", default=[],
                    help="audit_wheel_provenance output to fold into "
                         "classification (repeatable)")
    args = ap.parse_args()

    stamp = lib.now_utc()
    discovery: dict = {"channels": {}}
    scan_errors: list[dict] = []
    for ch_name in [c.strip() for c in args.channels.split(",") if c.strip()]:
        base = gp_lib.OFFICIAL_CHANNELS[ch_name]
        print(f"[scan] {ch_name}: {base}", flush=True)
        discovery["channels"][ch_name] = dow.scan_channel(
            ch_name, base, gp_lib.DISCOVERY_PACKAGES)
    if args.full:
        lib.dump_json(discovery, Path(args.full))

    therock = {"skipped": True, "note": "--skip-therock"} if args.skip_therock \
        else scan_therock_releases()
    pytorch_org = scan_pytorch_official_index()

    candidates = normalize_candidates(discovery, audits=load_audits(args.audit))
    envelope = {
        "run_id": f"R22A5A-RELEASE-SCAN-{stamp[:10]}",
        "mission": "R22A.5A",
        "scanned_utc": stamp,
        "tool": "scripts/r22a5a/scan_official_releases.py (reuses "
                "discover_official_wheels.scan_channel unchanged)",
        "fresh_audits_folded_in": args.audit or [],
        "merged_fix_commit": lib.MERGED_FIX_COMMIT,
        "channel_indexes": {c: gp_lib.OFFICIAL_CHANNELS[c]
                            for c in discovery["channels"]},
        "channel_root_status": {c: ch.get("root_status")
                                for c, ch in discovery["channels"].items()},
        "scan_errors": scan_errors,
        "therock_releases": therock,
        "pytorch_official_index": pytorch_org,
        "classification_vocabulary": lib.RELEASE_CLASSIFICATIONS,
        "notes": [
            "observation envelope: timestamps + channel errors live HERE; the "
            "candidates[] array is deterministic and sorted",
            "classifications are fail-closed: frozen-audit anchors are reused "
            "by wheel/dll identity; NEW artifacts remain "
            "NEW_ARTIFACT_PROVENANCE_PENDING until audit_wheel_provenance.py",
            "no classification is a physical GPU PASS (R22A.5B gates decide)",
        ],
    }
    out = lib.dump_json({"envelope": envelope, "candidates": candidates},
                        Path(args.out))
    n_cls: dict[str, int] = {}
    for c in candidates:
        n_cls[c["classification"]] = n_cls.get(c["classification"], 0) + 1
    print(f"[OK] {out} ({len(candidates)} candidates)")
    print(json.dumps(n_cls, indent=1, sort_keys=True))
    print(f"[pytorch.org] {pytorch_org['verdict']}")
    if not args.skip_therock:
        for t in therock.get("tags", []):
            print(f"[therock] {t.get('tag_name')}: {t.get('verdict')}")


if __name__ == "__main__":
    main()
