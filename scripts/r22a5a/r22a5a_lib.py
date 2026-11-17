# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Shared library for R22A.5A — CPU-only Stable release preflight.

Every rule here is PURE and unit-testable offline (no network, no GPU, no
torch import). Scripts in this folder import r22a5a_lib so classification,
wheel inspection and plan generation behave identically everywhere:

  - FROZEN_CHANNEL_ANCHORS: binary-audit anchors from the immutable R22
    evidence packs (evidence/raw/r22-dev, r22a-gfx1151; P14/P16 audits).
    An anchor identity (wheel SHA256 or channel+package+version with a
    recorded DLL SHA256) lets a re-scan reuse a FROZEN verdict without
    re-downloading — the anchor bytes were already audited.
  - classify_channel_artifact(): mission §4.3 classification, fail-closed.
    A version number NEVER implies fix presence (rc 10.2.0rc2 precedent:
    post-merge build date, pre-fix source, behind_by=92).
  - safe_inspect_wheel(): bounded ZIP inspection WITHOUT installation or
    extraction — metadata parse, embedded MIOpen.dll hash/marker/build
    commit, archive path-traversal detection. Never executes archive code.
  - classify_installation_plan(): OFFICIAL_STABLE / OFFICIAL_RC /
    OFFICIAL_DEV / UNQUALIFIED tiers; commands are emitted ONLY for a
    coherent qualified candidate set (mission §6.2).
  - scan_hidden_requirements(): G9 clean-install contract scanner — flags
    VS Build Tools / host-STL / HIPRTC_* / MIOPEN_* / private-index /
    editable-checkout / dev-path dependencies in instructions or a live env.

Nothing here may invent a PASS: a positive screening marker alone never
yields a fix-confirmed classification, and no classification is ever a
physical GPU PASS (that requires R22A.5B runtime gates G1..G9).
"""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

import sys

_HERE = Path(__file__).resolve().parent
_WGP = _HERE.parent.parent / "windows-golden-path" / "scripts"
if str(_WGP) not in sys.path:
    sys.path.insert(0, str(_WGP))
import gp_lib  # noqa: E402  (shared golden-path library, reused unchanged)

MERGED_FIX_COMMIT = "f0a5d2664cf3334161f7b82c02dfcd2213988a8a"

# Mission §4.3 classification vocabulary (never convertible to GPU PASS)
RELEASE_CLASSIFICATIONS = [
    "NO_NEW_ARTIFACT",
    "OFFICIAL_PRE_FIX",
    "NEW_ARTIFACT_PROVENANCE_PENDING",
    "SOURCE_LINEAGE_CONFIRMED",
    "BINARY_PROVENANCE_INCONCLUSIVE",
    "PRE_RELEASE_CANDIDATE",
    "STABLE_CANDIDATE_PENDING_GPU_VALIDATION",
    "BLOCKED_NETWORK",
    "BLOCKED_METADATA",
]

# Installation-plan tiers (mission §6.2). An UNQUALIFIED candidate must
# never be emitted as a production-ready installation instruction.
PLAN_TIERS = ["OFFICIAL_STABLE", "OFFICIAL_RC", "OFFICIAL_DEV", "UNQUALIFIED"]

# Channel → plan tier ceiling. The channel is a FACT of where the artifact
# is published (observed index host), not a label the caller may choose.
CHANNEL_TIER = {
    "stable": "OFFICIAL_STABLE",
    "rc": "OFFICIAL_RC",
    "nightly": "OFFICIAL_DEV",   # nightly is a development channel
    "dev": "OFFICIAL_DEV",
    "multi-arch": "OFFICIAL_STABLE",  # GA channel; still requires anchors
}

# Frozen binary-audit anchors (immutable R22 evidence; NEVER mutated here).
# Identity keys: wheel_sha256 preferred; else channel+package+version with
# embedded DLL sha256 recorded by the frozen audit.
FROZEN_CHANNEL_ANCHORS = {
    ("stable", "rocm-sdk-libraries", "10.1.0"): {
        "wheel_filename": "rocm_sdk_libraries-10.1.0-py3-none-win_amd64.whl",
        "wheel_sha256": "0c34bafbb4aa626cc710d8b130bb314f591194c3d79eeb5892b755ea0be06159",
        "miopen_dll_sha256": "266d716bab4aaf4ec3bb7492d35f6b65473982bc38f22b14235863a15c1429b4",
        "build_commit": "39d8d603",
        "marker_miopen_initializer_list": 0,
        "ancestry_behind_by": None,   # not comparable: pre-fix build id
        "fix_present": False,
        "evidence": "P14/P15/P16 triple byte-identical re-audit (2026-11-15); "
                    "docs/release-closure/P16_OFFICIAL_WHEEL_BINARY_AUDIT.md",
    },
    ("rc", "rocm-sdk-libraries", "10.2.0rc2"): {
        "wheel_filename": "rocm_sdk_libraries-10.2.0rc2-py3-none-win_amd64.whl",
        "wheel_sha256": "ffbf6c7760ea221851dbdbba6955546d0494034b64b238d25411335434ece25a",
        "miopen_dll_sha256": "2a3a026c088a873738b6ebfa8524b2f01b463331bde5f90e6e7f02c2e5fa6859",
        "build_commit": "8faffed0f",
        "marker_miopen_initializer_list": 0,
        "ancestry_behind_by": 92,     # diverged: branch cut BEFORE the merge
        "fix_present": False,
        "evidence": "evidence/raw/r22-dev/r22_channel_binary_audit.json (2026-11-15)",
    },
    ("nightly", "rocm-sdk-libraries", "10.3.0a20261115"): {
        "wheel_filename": "rocm_sdk_libraries-10.3.0a20261115-py3-none-win_amd64.whl",
        "wheel_sha256": "33f5ea8ab0ba03054fb4029b6fa46600be8a6cc793fa7af3396c06fa40fd465c",
        "build_commit": "9ea8cfc5",
        "marker_miopen_initializer_list": 2,
        "ancestry_behind_by": 0,      # ahead_by=1011: fix is an ancestor
        "fix_present": True,
        "evidence": "evidence/raw/r22-dev/r22_channel_binary_audit.json (2026-11-15)",
    },
    ("dev", "rocm-sdk-libraries", "10.3.0.dev0+ff5769655eeb1b91a46bce9edc16d87ca0efe7b6"): {
        "wheel_filename": None,       # arch-specific URL-encoded names vary
        "wheel_sha256": "dac27df54d5f659e50e8b098fd751386930b08c607f9272c5d25c3c27f0b7d56",
        "miopen_dll_sha256": "47a2e32c7401af2581860bc4a9e9fbb5b3f80be1e68c951b4ff3058f48683b91",
        "build_commit": "4e7d93e3",
        "marker_miopen_initializer_list": 2,
        "ancestry_behind_by": 0,
        "fix_present": True,
        "evidence": "evidence/raw/r22a-gfx1151/r22a_channel_binary_audit_gfx1151.json "
                    "(2026-11-16); gfx1100 dev set audited in evidence/raw/r22-dev",
    },
    ("multi-arch", "rocm-sdk-libraries", "7.14.1"): {
        "wheel_filename": "rocm_sdk_libraries-7.14.1-py3-none-win_amd64.whl",
        "wheel_sha256": None,         # not re-downloaded in P14/P16; DLL anchor below
        "miopen_dll_sha256": "e97891df7ea0ba2b6eda703bd69499521dc9a38300fe626f412b5544dec647bc",
        "build_commit": "cd957402",
        "marker_miopen_initializer_list": 0,
        "ancestry_behind_by": None,
        "fix_present": False,
        "evidence": "P14 installed-payload audit + R21-D1 live no-STL EXPECTED_FAIL "
                    "(release-provenance/BINARY_PROVENANCE.json, windows-golden-path/README.md)",
    },
}


def now_utc() -> str:
    return gp_lib.now_utc()


def sha256_file(p: Path) -> str:
    return gp_lib.sha256_file(p)


def decode_version(v: str | None) -> str | None:
    """Index hrefs carry URL-encoded local versions (%2B == '+')."""
    from urllib.parse import unquote
    return unquote(v) if v else v


_PRE_ORDER = {"dev": 0, "a": 1, "alpha": 1, "b": 2, "beta": 2,
              "rc": 3, "c": 3, "pre": 3, "preview": 3, "post": 4}


def version_sort_key(v: str | None):
    """PEP-440-ish ordering key sufficient for the observed AMD version forms
    (10.1.0 / 7.14.1 / 10.2.0rc2 / 10.3.0a20261115 / 10.3.0.dev0+sha /
    2.15.0+git…devrocm10.2.0.dev0.…). dev < a < b < rc < final < post;
    local segment participates as a tiebreak only."""
    from urllib.parse import unquote
    public = (unquote(v or "")).split("+")[0]
    epoch = 0
    m = re.match(r"^(\d+)!(.+)$", public)
    if m:
        epoch, public = int(m.group(1)), m.group(2)
    key: list[tuple[int, int, str]] = []
    for t in re.findall(r"\d+|[a-zA-Z]+", public):
        if t.isdigit():
            key.append((1, int(t), ""))
        else:
            key.append((0, _PRE_ORDER.get(t.lower(), 5), t.lower()))
    # final-release sentinel: a version with NO trailing pre-release token
    # sorts ABOVE the same version with one (PEP 440: 10.3.0rc2 < 10.3.0)
    if key and key[-1][0] == 1 or not key:
        key.append((2, 0, ""))
    local = (unquote(v or "")).split("+")[1] if "+" in (v or "") else ""
    return (epoch, key, local)


# --- audited family frontiers -------------------------------------------------
# Per (channel, ROCm family): the NEWEST frozen-audited artifact, keyed by
# its ROCm SET version (the version the channel cuts the whole SDK set at:
# the +rocmX.Y.Z local segment for torch/torchvision/device wheels, the
# public version for rocm-sdk* packages). A wheel whose SET version is
# BELOW its channel+family frontier is dominated by an audit that already
# covered newer bytes of the fix-bearing lineage (rocm-sdk-libraries).
# Backports legitimately raise the version number, so an older listing can
# never be a newer fix carrier (disclosed assumption, enforced fail-closed).

_RELEASE_CUT_CHANNELS = ("multi-arch", "stable", "rc")  # versioned release cuts


def rocm_set_version(package: str, version: str | None) -> str | None:
    """The ROCm set version a wheel belongs to, from the version string:
    torch 2.14.0+rocm10.1.0 → '10.1.0'; torch 2.15.0+rocm10.2.0rc2 →
    '10.2.0rc2' (trailing rc/a/b/dev suffix KEPT so release cuts do not
    collide with their pre-releases); rocm-sdk-libraries 10.1.0 → '10.1.0';
    torch 2.16.0a0+git…devrocm10.3.0.dev0.… → '10.3.0.dev0'. None when the
    version carries no identifiable ROCm segment."""
    v = decode_version(version) or ""
    local = v.split("+", 1)[1] if "+" in v else ""
    m = re.search(r"(?:^|[.\-_])[a-z0-9]*rocm(\d+(?:\.\d+){0,2})", local,
                  re.IGNORECASE)
    if m:
        set_v = m.group(1)
        # keep an immediately-following pre-release / dev suffix (observed:
        # rc2, a20261115, .dev0) so 10.2.0rc2 != 10.2.0
        m2 = re.match(r"(rc\d+|a\d+|b\d+|\.dev\d+(?:\.\d+)*)", local[m.end():])
        if m2:
            set_v += m2.group(1)
        return set_v
    name = gp_lib.dist_key(package or "")
    if name == "rocm" or name.startswith("rocm-sdk"):
        pub = v.split("+")[0]
        return pub or None
    return None


def _is_release_cut(package: str, version: str | None) -> bool:
    """Release-cut identity: non-dev channels AND a version without dev/git
    local segments (a dated alpha or a +git…dev local version identifies a
    MOVING build, never a stable cut whose set members may inherit)."""
    v = decode_version(version) or ""
    if ".dev" in v or "git" in v.split("+")[-1]:
        return False
    return True


def audited_family_frontiers() -> dict:
    out: dict = {}
    for (ch, pkg, ver), a in FROZEN_CHANNEL_ANCHORS.items():
        set_ver = rocm_set_version(pkg, ver)
        fam = gp_lib.rocm_family_of(pkg, decode_version(ver) or "")
        if not set_ver or not fam:
            continue
        cur = out.get((ch, fam))
        if cur is None or version_sort_key(set_ver) > cur["key"]:
            out[(ch, fam)] = {"key": version_sort_key(set_ver),
                              "set_version": set_ver, "package": pkg,
                              "wheel_version": decode_version(ver),
                              "fix_present": a["fix_present"],
                              "evidence": a["evidence"]}
    return out




def extract_build_commit(version_strings: list[str]) -> str | None:
    """Build-commit identity from embedded MIOpen version strings
    (e.g. '3.6.3.9ea8cfc5' → '9ea8cfc5'). Same convention as the frozen
    audits and verify_provenance.evaluate_lineage."""
    if not version_strings:
        return None
    m = re.match(r"3\.\d+\.\d+\.([0-9a-f]{7,12})", sorted(version_strings)[-1])
    return m.group(1) if m else None


# --- mission §4.3 channel-artifact classification (pure, fail-closed) --------

def classify_channel_artifact(channel: str | None, package: str | None,
                              version: str | None,
                              audit: dict | None = None,
                              channel_reachable: bool = True,
                              metadata_ok: bool = True,
                              wheel_sha256: str | None = None) -> dict:
    """Classify ONE observed channel artifact.

    Precedence (fail-closed at every step):
      1. channel unreachable                     → BLOCKED_NETWORK
      2. metadata incomplete                     → BLOCKED_METADATA
      3. identity == frozen anchor               → anchor verdict reused
         (OFFICIAL_PRE_FIX for audited pre-fix anchors; SOURCE_LINEAGE_CONFIRMED
          family for audited post-fix anchors)
      4. no fresh audit for a NEW artifact       → NEW_ARTIFACT_PROVENANCE_PENDING
      5. audit fix-absent proof (marker 0 OR ancestry behind/diverged)
                                                 → OFFICIAL_PRE_FIX
      6. marker>0 but ancestry unproven/absent   → BINARY_PROVENANCE_INCONCLUSIVE
      7. marker>0 AND ancestry behind_by==0      → SOURCE_LINEAGE_CONFIRMED,
         then channel promotion:
           stable → STABLE_CANDIDATE_PENDING_GPU_VALIDATION
           rc/nightly/dev → PRE_RELEASE_CANDIDATE
      multi-arch GA channel follows the stable rule (it is a GA channel),
      EXCEPT its known anchors are pre-fix.

    `audit` (optional, fresh): {marker_miopen_initializer_list,
    ancestry_behind_by, ancestry_status, fix_present, ...}. Serialized
    verdict strings are never consulted — only the embedded facts.
    """
    out = {"channel": channel, "package": package, "version": decode_version(version)}
    if not channel_reachable:
        out["classification"] = "BLOCKED_NETWORK"
        out["reason"] = "channel index unreachable at scan time (recorded honestly; " \
                        "a network outage is NOT a no-release verdict)"
        return out
    if not metadata_ok or not version or not package:
        out["classification"] = "BLOCKED_METADATA"
        out["reason"] = "index response lacked parseable package/version metadata"
        return out

    # 3. frozen-anchor identity reuse (byte identity → frozen verdict)
    key = (channel, gp_lib.dist_key(package),
           gp_lib.dist_key(decode_version(version)))
    anchor = FROZEN_CHANNEL_ANCHORS.get(key)
    if anchor is None and wheel_sha256:
        for (ch, pkg, _ver), a in FROZEN_CHANNEL_ANCHORS.items():
            if ch == channel and pkg == gp_lib.dist_key(package) \
                    and a.get("wheel_sha256") \
                    and a["wheel_sha256"].lower() == str(wheel_sha256).lower():
                anchor, key = a, (ch, pkg, _ver)
                break
    # negative control: same (channel, package, version) but a DIFFERENT
    # wheel SHA256 than the audited anchor = renamed/modified artifact —
    # the frozen verdict must NOT be reused (fail to pending/inconclusive)
    if anchor is not None and wheel_sha256 and anchor.get("wheel_sha256") \
            and str(wheel_sha256).lower() != anchor["wheel_sha256"].lower():
        out["classification"] = ("BINARY_PROVENANCE_INCONCLUSIVE"
                                 if (audit or {}).get(
                                     "marker_miopen_initializer_list")
                                 else "NEW_ARTIFACT_PROVENANCE_PENDING")
        out["reason"] = (f"wheel SHA256 {str(wheel_sha256)[:12]}… != audited "
                         f"anchor {anchor['wheel_sha256'][:12]}… for the same "
                         "version — correctly-named artifact with wrong hash "
                         "is NOT the audited bytes")
        return out
    if anchor is not None:
        ident = ("wheel_sha256" if wheel_sha256 and anchor.get("wheel_sha256")
                 and str(wheel_sha256).lower() == anchor["wheel_sha256"].lower()
                 else "channel+package+version")
        out["anchor"] = {"identity": ident, "evidence": anchor["evidence"]}
        if anchor["fix_present"]:
            out["classification"] = ("STABLE_CANDIDATE_PENDING_GPU_VALIDATION"
                                     if channel in ("stable", "multi-arch")
                                     else "PRE_RELEASE_CANDIDATE")
            out["reason"] = ("frozen R22 binary audit proves fix present "
                             f"(marker={anchor['marker_miopen_initializer_list']}, "
                             f"ancestry behind_by={anchor['ancestry_behind_by']}); "
                             "physical GPU validation still required (R22A.5B)")
        else:
            out["classification"] = "OFFICIAL_PRE_FIX"
            out["reason"] = ("frozen R22 binary audit proves fix ABSENT "
                             f"(marker={anchor['marker_miopen_initializer_list']}"
                             + (f", ancestry behind_by={anchor['ancestry_behind_by']}"
                                if anchor.get("ancestry_behind_by") else "") + ")")
        return out

    # 3b. set-member inheritance (release-cut channels only): a wheel whose
    #     (channel, ROCm set version) equals an audited anchor's belongs to
    #     the SAME release cut; it inherits the set's fix verdict with full
    #     disclosure. Per-wheel SHA256 pinning still applies at install time
    #     (resolve_package_set). Moving builds (dev/nightly +git/.dev local
    #     versions) NEVER inherit — each is a distinct build.
    set_ver = rocm_set_version(package, version)
    if set_ver and channel in _RELEASE_CUT_CHANNELS and _is_release_cut(package, version):
        for (ch, pkg, aver), a in FROZEN_CHANNEL_ANCHORS.items():
            if ch == channel and rocm_set_version(pkg, aver) == set_ver \
                    and _is_release_cut(pkg, aver):
                out["classification"] = ("OFFICIAL_PRE_FIX" if not a["fix_present"]
                                         else "STABLE_CANDIDATE_PENDING_GPU_VALIDATION")
                out["reason"] = (f"set-member inheritance: same {channel}-channel "
                                 f"release cut {set_ver} as audited {pkg} "
                                 f"{decode_version(aver)} (fix_present="
                                 f"{a['fix_present']}; {a['evidence']}); "
                                 "install-time per-wheel SHA pinning still applies")
                return out

    # 3c. family-frontier domination: a wheel whose ROCm SET version is
    #     OLDER than the channel's audited frontier of the same family cannot
    #     be a NEWER fix carrier (backports raise version numbers — disclosed
    #     assumption, enforced fail-closed).
    fam = gp_lib.rocm_family_of(gp_lib.dist_key(package),
                                decode_version(version) or "")
    frontier = audited_family_frontiers().get((channel, fam)) if fam else None
    if frontier is not None and set_ver \
            and version_sort_key(set_ver) < frontier["key"]:
        out["classification"] = "NO_NEW_ARTIFACT"
        out["reason"] = (f"ROCm set version {set_ver} is older than the audited "
                         f"{channel}-channel family-{fam} frontier "
                         f"{frontier['set_version']} (fix_present="
                         f"{frontier['fix_present']}; {frontier['evidence']})")
        return out

    # 4-7. fresh-audit evaluation for artifacts NEWER than (or absent from)
    #      the frozen anchors
    if audit is None:
        out["classification"] = "NEW_ARTIFACT_PROVENANCE_PENDING"
        out["reason"] = ("artifact not covered by any frozen audit; binary "
                         "provenance pending audit_wheel_provenance.py — a "
                         "new version number NEVER implies fix presence")
        return out
    marker = int(audit.get("marker_miopen_initializer_list") or 0)
    behind = audit.get("ancestry_behind_by")
    status = audit.get("ancestry_status")
    if marker == 0 or behind not in (0, None) or status not in (None, "ahead"):
        # marker 0 = pre-fix bytes; behind>0 or diverged = source cut before
        # the merge (the rc 10.2.0rc2 case: newer version, older source)
        out["classification"] = "OFFICIAL_PRE_FIX"
        out["reason"] = (f"fresh audit: marker={marker}, ancestry_status={status!r}, "
                         f"behind_by={behind!r} — fix proven ABSENT in this binary")
        return out
    if behind == 0 and status == "ahead":
        out["classification"] = ("STABLE_CANDIDATE_PENDING_GPU_VALIDATION"
                                 if channel in ("stable", "multi-arch")
                                 else "PRE_RELEASE_CANDIDATE")
        out["reason"] = (f"fresh audit: marker={marker}>0 AND merged-fix commit is "
                         "an ancestor (behind_by=0) — source lineage confirmed; "
                         "physical GPU validation still required (R22A.5B)")
        return out
    # marker>0, ancestry unknown/inconclusive → fail-closed
    out["classification"] = "BINARY_PROVENANCE_INCONCLUSIVE"
    out["reason"] = (f"fresh audit: marker={marker}>0 but ancestry unproven "
                     f"(status={status!r}, behind_by={behind!r}) — screening "
                     "signal alone is NOT proof")
    return out


def therock_tag_fix_facts(tag_entry: dict) -> dict:
    """Evaluate one TheRock release tag against the merged fix.

    Input facts (from gh api, live layer): {tag_name, published_at,
    submodule_pointer (rocm-libraries), compare: {status, behind_by}}.
    Pure evaluation — a missing submodule pointer or compare is UNKNOWN,
    never a date-based inference."""
    out = dict(tag_entry)
    if not tag_entry.get("submodule_pointer") or not tag_entry.get("compare"):
        out["contains_merged_fix"] = None  # UNKNOWN — fail-closed
        out["verdict"] = "UNKNOWN (submodule pointer or compare not available)"
        return out
    c = tag_entry["compare"]
    out["contains_merged_fix"] = bool(
        c.get("status") in ("ahead", "diverged") and c.get("behind_by") == 0)
    out["verdict"] = ("FIX_ANCESTOR" if out["contains_merged_fix"]
                      else "PRE_FIX_SOURCE (behind_by=%s)" % c.get("behind_by"))
    return out


# --- safe wheel ZIP inspection (no install, no extraction, no execution) -----

MAX_WHEEL_BYTES = 3 * 1024 * 1024 * 1024  # bound: largest official torch ~2.3 GiB
MAX_MEMBER_READ_BYTES = 768 * 1024 * 1024  # MIOpen.dll observed ≤ ~502 MiB
MIOPEN_DLL_MEMBER_SUFFIXES = ("_rocm_sdk_libraries/bin/MIOpen.dll",
                              "MIOpen.dll")


def _member_is_unsafe(name: str) -> bool:
    """Archive path-traversal / absolute-path / drive-letter detection."""
    if name.startswith(("/", "\\")) or ":" in name.split("/")[0].split("\\")[0]:
        return True
    parts = re.split(r"[/\\]", name)
    return any(p == ".." for p in parts)


def safe_inspect_wheel(path: Path, expect_name: str | None = None,
                       compute_dll: bool = True) -> dict:
    """Bounded, read-only ZIP inspection of a wheel (never installed).

    Returns: {ok, wheel_sha256, size_bytes, metadata{name,version,
    requires_python, requires_dist[]}, miopen_dll{member,sha256,bytes,
    version_strings,build_commit,marker_miopen_initializer_list},
    unsafe_members[], errors[]}.

    - refuses wheels above MAX_WHEEL_BYTES (caller re-verifies anyway);
    - detects path-traversal members WITHOUT extracting anything;
    - parses *.dist-info/METADATA only;
    - streams the embedded MIOpen.dll in bounded chunks for hashing and
      marker counting (fix-marker b'miopen_initializer_list');
    - NEVER executes or imports anything from the archive.
    """
    res: dict = {"ok": False, "unsafe_members": [], "errors": []}
    p = Path(path)
    if not p.is_file():
        res["errors"].append("wheel file not found")
        return res
    size = p.stat().st_size
    res["size_bytes"] = size
    if size > MAX_WHEEL_BYTES:
        res["errors"].append(f"wheel {size} bytes exceeds bound {MAX_WHEEL_BYTES}")
        return res
    res["wheel_sha256"] = sha256_file(p)
    try:
        zf = zipfile.ZipFile(p)
    except zipfile.BadZipFile as e:
        res["errors"].append(f"not a valid zip/wheel: {e}")
        return res
    with zf:
        names = zf.namelist()
        for n in names:
            if _member_is_unsafe(n):
                res["unsafe_members"].append(n)
        if res["unsafe_members"]:
            res["errors"].append("archive contains unsafe (path-traversal / "
                                 "absolute) member names — refusing further use")
            return res
        # METADATA
        meta_files = sorted(n for n in names if n.endswith(".dist-info/METADATA"))
        md = {}
        if meta_files:
            blob = zf.read(meta_files[0])[:262144]
            text = blob.decode("utf-8", errors="replace")
            header, _, body = text.partition("\n\n")
            for line in header.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    md[k.strip().lower().replace("-", "_")] = v.strip()
            rd = [l for l in body.splitlines() if l.lower().startswith("requires-dist:")]
            res["metadata"] = {
                "name": md.get("name"),
                "version": md.get("version"),
                "requires_python": md.get("requires_python"),
                "requires_dist": rd,
            }
        else:
            res["metadata"] = None
            res["errors"].append("no .dist-info/METADATA member")
        if expect_name and res["metadata"] and res["metadata"].get("name") \
                and gp_lib.dist_key(res["metadata"]["name"]) != gp_lib.dist_key(expect_name):
            res["errors"].append(
                f"METADATA name {res['metadata']['name']!r} != expected {expect_name!r}")
        # embedded MIOpen.dll
        if compute_dll:
            member = next((n for n in names if n.endswith(MIOPEN_DLL_MEMBER_SUFFIXES)
                           and not n.endswith("/")), None)
            if member is None:
                res["miopen_dll"] = None
            else:
                info = zf.getinfo(member)
                if info.file_size > MAX_MEMBER_READ_BYTES:
                    res["errors"].append(
                        f"MIOpen.dll member {info.file_size} exceeds read bound")
                    return res
                h = hashlib.sha256()
                versions: set[bytes] = set()
                marker = 0
                leftover = b""
                with zf.open(member) as f:
                    while True:
                        chunk = f.read(1 << 22)
                        if not chunk:
                            break
                        h.update(chunk)
                        marker += chunk.count(gp_lib.FIX_MARKER)
                        versions.update(re.findall(
                            rb"3\.[0-9]+\.[0-9]+\.[0-9a-f]{7,12}", chunk))
                        # a version regex match could straddle chunk borders;
                        # rescan the seam so identity is chunking-invariant
                        seam = leftover[-16:] + chunk[:16]
                        versions.update(re.findall(
                            rb"3\.[0-9]+\.[0-9]+\.[0-9a-f]{7,12}", seam))
                        leftover = chunk
                vs = sorted(v.decode() for v in versions)
                res["miopen_dll"] = {
                    "member": member, "sha256": h.hexdigest(),
                    "bytes": info.file_size, "version_strings": vs,
                    "build_commit": extract_build_commit(vs),
                    "marker_miopen_initializer_list": marker,
                }
    res["ok"] = not res["errors"]
    return res


# --- installation-plan classification (mission §6.2) --------------------------

def classify_installation_plan(channel: str, artifact_class: str,
                               set_complete: bool,
                               dep_coherent: bool) -> dict:
    """Plan tier for a candidate SET. Commands may only be emitted when the
    tier is not UNQUALIFIED AND set_complete AND dep_coherent all hold.

    artifact_class comes from classify_channel_artifact; the channel CEILING
    applies — a nightly artifact can never produce an OFFICIAL_STABLE plan,
    regardless of its binary content (mission: never label nightly Stable)."""
    ceiling = CHANNEL_TIER.get(channel, "UNQUALIFIED")
    fix_confirmed = artifact_class in (
        "STABLE_CANDIDATE_PENDING_GPU_VALIDATION", "PRE_RELEASE_CANDIDATE")
    if not fix_confirmed:
        tier = "UNQUALIFIED"
        reason = f"artifact classification {artifact_class!r} is not fix-confirmed"
    elif ceiling == "OFFICIAL_STABLE":
        tier = "OFFICIAL_STABLE"
        reason = "stable/GA channel artifact with confirmed source lineage"
    elif ceiling == "OFFICIAL_RC":
        tier = "OFFICIAL_RC"
        reason = "RC channel artifact with confirmed lineage — pre-release"
    else:
        tier = "OFFICIAL_DEV"
        reason = "development/nightly channel artifact with confirmed lineage"
    blockers = []
    if not set_complete:
        blockers.append("candidate set incomplete (missing device wheels for "
                        "target gfx / torchvision / core set)")
    if not dep_coherent:
        blockers.append("dependency set incoherent (family mix / ABI / vendor "
                        "origin rules failed)")
    emit_commands = tier != "UNQUALIFIED" and not blockers
    return {"tier": tier, "ceiling": ceiling, "emit_commands": emit_commands,
            "blockers": blockers, "reason": reason,
            "note": "an emitted plan is an INSTALLATION candidate only; it is "
                    "never a training PASS (R22A.5B physical gates decide)"}


# --- G9 clean-install hidden-requirement scanner (mission §7.1) ---------------

HIDDEN_REQUIREMENT_PATTERNS = [
    (r"VCToolsInstallDir", "VCTOOLS_REDIRECT",
     "relies on VCToolsInstallDir redirect (host MSVC STL toolchain)"),
    (r"HIPRTC_COMPILE_OPTIONS_APPEND|HIPRTC_INCLUDE", "HIPRTC_ENV",
     "relies on HIPRTC environment injection"),
    (r"\bMIOPEN_[A-Z_]+\s*=", "MIOPEN_OVERRIDE",
     "sets custom MIOPEN_* environment overrides"),
    (r"Visual Studio|VS Build Tools|Build Tools|MSVC", "MSVC_BUILD_TOOLS",
     "instructs installing MSVC Build Tools / VS C++ toolset (host STL)"),
    (r"C:\\Users\\rocm|/home/\w+|C:\\YOLO|C:\\b58", "DEV_PATH",
     "contains a hardcoded developer-local path"),
    (r"--index-url\s+(?!https://(repo\.amd\.com|stable\.repo\.amd\.com|rc\.repo\.amd\.com|nightly\.repo\.amd\.com|dev\.repo\.amd\.com|pypi\.org))\S+",
     "PRIVATE_INDEX", "uses a non-official package index"),
    (r"-e\s+\S+|editable", "EDITABLE_CHECKOUT",
     "installs an editable/dev checkout instead of a released package"),
    (r"torch\.load.*weights_only=False|verify=False", "UNSAFE_OPTION",
     "disables a safety option"),
]


def scan_hidden_requirements(text: str) -> list[dict]:
    """Scan instruction text for hidden developer-only requirements (pure)."""
    hits = []
    for pat, code, why in HIDDEN_REQUIREMENT_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE if code in ("MSVC_BUILD_TOOLS",)
                      else 0)
        if m:
            hits.append({"code": code, "pattern": pat,
                         "match": m.group(0)[:80], "why": why})
    return hits


def scan_hidden_env(env: dict | None = None) -> list[dict]:
    """Live-environment variant: HIPRTC/MIOPEN/VCTools/PYTHONPATH leakage."""
    import os
    env = env if env is not None else dict(os.environ)
    hits = []
    for var in ("HIPRTC_COMPILE_OPTIONS_APPEND", "HIPRTC_INCLUDE"):
        if env.get(var):
            hits.append({"code": "HIPRTC_ENV", "var": var, "value": env[var][:120]})
    for var in sorted(env):
        if var.startswith("MIOPEN_") and var not in ("MIOPEN_LOG_LEVEL",):
            hits.append({"code": "MIOPEN_OVERRIDE", "var": var,
                         "value": env[var][:120]})
    if env.get("VCToolsInstallDir"):
        hits.append({"code": "VCTOOLS_REDIRECT", "var": "VCToolsInstallDir",
                     "value": env["VCToolsInstallDir"][:120]})
    if env.get("PYTHONPATH"):
        hits.append({"code": "PYTHONPATH_OVERRIDE", "var": "PYTHONPATH",
                     "value": env["PYTHONPATH"][:120]})
    return hits


def allowed_download_hosts() -> set[str]:
    """TLS-verified download allowlist (mission §10.1): official AMD channels
    only. Any other host must be rejected by the live layers."""
    hosts = set()
    for root in gp_lib.OFFICIAL_CHANNELS.values():
        hosts.add(root.split("/")[2])
    return hosts


def url_host(url: str) -> str | None:
    return url.split("/")[2] if "://" in (url or "") else None


def dump_json(obj, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


# --- G9 BLOCKED_RELEASE gate contract -----------------------------------------

def g9_gate(fix_confirmed_stable_available: bool) -> dict:
    """The G9 preflight decision (mission §7.2): stop with BLOCKED_RELEASE
    unless a fix-confirmed OFFICIAL_STABLE/GA candidate exists. Never
    silently proceed with an incompatible wheel."""
    if fix_confirmed_stable_available:
        return {"status": "PROCEED_CANDIDATE",
                "meaning": "qualified candidate exists — continue to provenance "
                           "audit + R22A.5B physical gates"}
    return {"status": "BLOCKED_RELEASE",
            "meaning": "no official Windows artifact containing the merged fix "
                       "is qualified; the golden path must NOT proceed with "
                       "pre-fix wheels (rocm-libraries#15862 remains open)"}
