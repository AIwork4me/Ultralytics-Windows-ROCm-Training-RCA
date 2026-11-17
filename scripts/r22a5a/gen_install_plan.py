# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""R22A.5A Phase C — Stable installation-plan generator.

Layers channel classification (Phase A/B outputs) over the EXISTING
compatibility rules (windows-golden-path/compatibility-matrix.yaml,
enforced by resolve_package_set.py) and emits, per channel, an
installation plan classified:

  OFFICIAL_STABLE | OFFICIAL_RC | OFFICIAL_DEV | UNQUALIFIED

Commands are emitted ONLY for an independently coherent, fix-confirmed
candidate set (mission §6.2). An UNQUALIFIED candidate is never rendered
as a production-ready installation instruction. The historical
golden-path/requirements-lock.txt is NEVER modified; a separate candidate
lock TEMPLATE is produced for the future repaired Stable build.

    python scripts/r22a5a/gen_install_plan.py \
        --candidates release-provenance/r22a5a/latest_official_windows_candidates.json \
        --gfx gfx1100 --python-tag cp312 \
        --out release-provenance/r22a5a/install_plan.json \
        --lock-template release-provenance/r22a5a/candidate_lock_template.json

Exit 0 = plan generated (plans may be UNQUALIFIED — that is a RESULT).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import r22a5a_lib as lib  # noqa: E402
import gp_lib  # noqa: E402

# Set members required for a coherent Windows install per channel layout
# (from compatibility-matrix.yaml rules; device-wheel-required and
# torchvision-device-wheel entries)
SET_MEMBERS_WHLNEXT = [
    "torch", "torchvision", "rocm-sdk-core", "rocm-sdk-libraries",
]
SET_MEMBERS_MULTIARCH = [
    "torch", "torchvision", "rocm-sdk-core", "rocm-sdk-libraries",
]


def required_device_packages(channel: str, gfx: str) -> list[str]:
    if channel == "multi-arch":  # 7.x layout: amd-torch-device-* family
        return [f"amd-torch-device-{gfx}", f"amd-torchvision-device-{gfx}",
                "amd-torch-device-gfx110x"]
    return [f"rocm-sdk-device-{gfx}"]  # whl-next 10.x layout


def set_versions(rows: list[dict], channel: str) -> dict[str, list[dict]]:
    """package → candidate rows on this channel."""
    out: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("channel") == channel and r.get("package"):
            out.setdefault(r["package"], []).append(r)
    return out


def evaluate_channel(channel: str, rows: list[dict], gfx: str,
                     python_tag: str) -> dict:
    """Coherence evaluation for one channel (pure; offline-testable)."""
    by_pkg = set_versions(rows, channel)
    members = SET_MEMBERS_WHLNEXT if channel != "multi-arch" else SET_MEMBERS_MULTIARCH
    required = members + required_device_packages(channel, gfx)

    present, missing, not_listed, abi_blocked, conflicts = [], [], [], [], []

    def set_of(pkg, r):
        return lib.rocm_set_version(pkg, r.get("version") or "") \
            or str(r.get("version"))

    # the sdk-libraries frontier row anchors the channel's release SET
    sdk_tag_rows = []
    for pkg in required:
        cand_rows = by_pkg.get(pkg) or []
        sdk_tag_rows = [r for r in cand_rows
                        if r["package"] == "rocm-sdk-libraries"
                        and (r.get("python_tag") in (None, "?", python_tag)
                             or (r.get("python_tag") or "").startswith("py3"))]
        if sdk_tag_rows:
            break
    anchor_set = set_of("rocm-sdk-libraries", sdk_tag_rows[0]) if sdk_tag_rows \
        else None

    for pkg in required:
        cand_rows = by_pkg.get(pkg) or []
        if not cand_rows:
            missing.append(pkg)
            continue
        tag_rows = [r for r in cand_rows
                    if r.get("python_tag") in (None, "?", python_tag)
                    or python_tag in (r.get("python_tag") or "")
                    or (r.get("python_tag") or "").startswith("py3")]
        if not tag_rows:
            # wheels exist but NONE matches the requested ABI — an ABI
            # blocker, not a silent fallback to whatever is listed
            abi_blocked.append({"package": pkg,
                                "available_tags": sorted({r.get("python_tag")
                                                          for r in cand_rows})})
            continue
        # multiple set versions for one package+ABI: disambiguate by the
        # channel's sdk-libraries release SET (moving channels legitimately
        # retain older same-public-version builds); only a genuine
        # ambiguity within the SAME set remains a conflict
        set_vs = sorted({set_of(pkg, r) for r in tag_rows})
        if len(set_vs) > 1 and anchor_set:
            matched = [r for r in tag_rows if set_of(pkg, r) == anchor_set]
            if len({set_of(pkg, r) for r in matched}) == 1 and matched:
                tag_rows = matched
                set_vs = sorted({set_of(pkg, r) for r in tag_rows})
        if len(set_vs) > 1:
            conflicts.append({"package": pkg, "rocm_set_versions": set_vs,
                              "versions": sorted(str(r.get("version"))
                                                 for r in tag_rows)})
        row = max(tag_rows, key=lambda r: (lib.version_sort_key(r.get("version")),
                                           r.get("wheel_filename") or ""))
        if row.get("classification") in ("BLOCKED_NETWORK", "BLOCKED_METADATA"):
            not_listed.append(pkg)
        else:
            present.append(row)

    # fix confirmation: every fix-bearing member must be fix-confirmed
    # (sdk-libraries anchors the set verdict; torch vendor check applies)
    sdk_rows = [r for r in present if r["package"] == "rocm-sdk-libraries"]
    sdk_cls = sdk_rows[0]["classification"] if sdk_rows else "NEW_ARTIFACT_PROVENANCE_PENDING"
    fix_confirmed = sdk_cls in ("STABLE_CANDIDATE_PENDING_GPU_VALIDATION",
                                "PRE_RELEASE_CANDIDATE")

    # family coherence across the set
    fams = set()
    for r in present:
        fam = gp_lib.rocm_family_of(r["package"], r.get("version") or "")
        if fam:
            fams.add(fam)
    fam_ok = len(fams) <= 1

    # torch vendor: AMD HIP build from the exact official channel
    torch_rows = [r for r in present if r["package"] == "torch"]
    torch_ok = bool(torch_rows) and all(
        gp_lib.torch_wheel_is_amd_hip(r.get("version") or "",
                                      r.get("wheel_url")) for r in torch_rows)

    set_complete = not missing and not not_listed and not abi_blocked
    dep_coherent = fam_ok and torch_ok and not conflicts
    plan = lib.classify_installation_plan(channel, sdk_cls, set_complete,
                                          dep_coherent)
    if abi_blocked:
        plan["blockers"] = plan["blockers"] + [
            f"python ABI {python_tag}: {b['package']} only offers "
            f"{b['available_tags']}" for b in abi_blocked]
        plan["emit_commands"] = False
    if conflicts:
        plan["blockers"] = plan["blockers"] + [
            f"conflicting versions for {c['package']}: {c['versions']}"
            for c in conflicts]
        plan["emit_commands"] = False
    return {
        "channel": channel,
        "channel_index": gp_lib.OFFICIAL_CHANNELS[channel],
        "required_packages": required,
        "missing_packages": missing,
        "unreachable_packages": not_listed,
        "abi_blocked": abi_blocked,
        "set_complete": set_complete,
        "rocm_families": sorted(fams),
        "family_coherent": fam_ok,
        "torch_is_amd_hip": torch_ok,
        "dep_coherent": dep_coherent,
        "sdk_libraries_classification": sdk_cls,
        "fix_confirmed": fix_confirmed,
        "plan": plan,
        "selected_rows": [{k: r.get(k) for k in
                           ("package", "version", "python_tag", "wheel_filename",
                            "wheel_url", "classification")} for r in present],
    }


def render_commands(channel: str, selected: list[dict], emit: bool) -> list[str]:
    if not emit:
        return []
    idx = gp_lib.OFFICIAL_CHANNELS[channel]
    pins = " ".join(f'"{r["package"]}=={r["version"]}"' for r in selected
                    if r.get("version"))
    return [
        f"python -m pip install --index-url {idx} {pins}",
        "python -m pip install ultralytics  # released PyPI package",
        "# then: python scripts/r22a5a/g9_preflight.py --channel "
        f"{channel}  (provenance + G9 preflight before ANY training)",
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--gfx", default="gfx1100", choices=["gfx1100", "gfx1151"])
    ap.add_argument("--python-tag", default="cp312")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lock-template", default=None)
    args = ap.parse_args()

    data = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    rows = data["candidates"]
    stamp = lib.now_utc()

    channels = {}
    for ch in sorted(gp_lib.OFFICIAL_CHANNELS):
        ev = evaluate_channel(ch, rows, args.gfx, args.python_tag)
        ev["commands"] = render_commands(ch, ev["selected_rows"],
                                         ev["plan"]["emit_commands"])
        channels[ch] = ev

    qualified = [c for c, ev in channels.items()
                 if ev["plan"]["emit_commands"]]
    stable_qualified = [c for c in qualified if channels[c]["plan"]["tier"]
                        == "OFFICIAL_STABLE"]
    if stable_qualified:
        overall = ("STABLE_CANDIDATE_FOUND_PENDING_PHYSICAL_VALIDATION")
    elif qualified:
        overall = ("PRE_RELEASE_ONLY_CANDIDATES_OFFICIAL_STABLE_BLOCKED_RELEASE")
    else:
        overall = "BLOCKED_RELEASE"
    plan_doc = {
        "run_id": f"R22A5A-INSTALL-PLAN-{stamp[:10]}",
        "mission": "R22A.5A",
        "generated_utc": stamp,
        "gfx_target": args.gfx,
        "python_tag": args.python_tag,
        "candidates_source": str(Path(args.candidates).name),
        "channels": channels,
        "overall": overall,
        "semantics": {
            "OFFICIAL_STABLE": "stable/GA channel, fix-confirmed coherent set — "
                               "install candidate ONLY; training PASS requires "
                               "R22A.5B physical gates",
            "OFFICIAL_RC": "RC channel candidate — pre-release, never labeled Stable",
            "OFFICIAL_DEV": "dev/nightly candidate — development channel",
            "UNQUALIFIED": "no installation commands may be emitted",
            "BLOCKED_RELEASE": "no qualified official Windows artifact "
                               "(rocm-libraries#15862)",
        },
        "note": "golden-path/requirements-lock.txt is historical (MODE B, "
                "2026-11-15) and is intentionally NOT modified by this tool",
    }
    lib.dump_json(plan_doc, Path(args.out))

    if args.lock_template:
        q = channels[qualified[0]] if qualified else None
        lib.dump_json({
            "template_for": "future repaired official Stable build",
            "generated_utc": stamp,
            "usage": "when a fix-confirmed stable candidate appears, run "
                     "windows-golden-path/scripts/resolve_package_set.py with "
                     "--channel stable to produce the REAL hash-pinned lock; "
                     "this template only pre-shapes the fields",
            "example_fields": {
                "set_name": q and f"stable-{q['selected_rows'][0]['version']}"
                                  f"-{args.python_tag}" or None,
                "channel": qualified[0] if qualified else "stable",
                "gfx_target": args.gfx,
                "packages_hint": [r["package"] for r in
                                  (q["selected_rows"] if q else [])] or
                                 SET_MEMBERS_WHLNEXT +
                                 required_device_packages("stable", args.gfx),
                "hash_policy": "every gpu-stack wheel SHA256-pinned "
                               "(resolve_package_set) — never install unpinned",
            },
            "forbidden": "do NOT hand-edit golden-path/requirements-lock.txt "
                         "to pretend a future build exists",
        }, Path(args.lock_template))

    print(f"[OK] {args.out}")
    for ch, ev in channels.items():
        print(f"  {ch:10} tier={ev['plan']['tier']:16} "
              f"emit={ev['plan']['emit_commands']} "
              f"sdk={ev['sdk_libraries_classification']}")
    print(f"overall: {overall}")


if __name__ == "__main__":
    main()
