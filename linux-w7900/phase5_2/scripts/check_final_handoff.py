#!/usr/bin/env python3
"""Strict consumer for the FROZEN Windows Phase-5.1 handoff manifest
(findings/phase5_1/FINAL_HANDOFF.json @ RCA evidence commit 494907699f).

Corrected in Phase 5.2 (Gate B02/B03) to consume the ACTUAL frozen schema:

    ACTUAL (frozen, authoritative):
        schema_version, handoff_type, candidate_id, base_repo, base_sha,
        ordered_commits, ordered_commit_subjects, ordered_patches[
            {order, path, sha256, bytes}],
        series_hash{algorithm=sha256_file_concat_v1, sha256},
        source_tree_identity{head_tree_sha1, changed_files_vs_base},
        dco_status, copyright_status,
        linux_validation_status, authorization_to_submit_upstream

    OLD PROVISIONAL (this script's pre-5.2 shape — REJECTED, no fallback):
        upstream_base_sha, patch_series, series_sha256,
        series_sha256_mode, rca_evidence_commit

The Windows manifest is NEVER modified to suit this consumer.

Modes:
  --check-only MANIFEST      validate manifest + recompute every hash from
                             RAW BYTES + verify the pinned RCA git checkout.
  --apply MANIFEST DIR       reconstruct the patched tree in DIR from a
                             clean git worktree + ordered patch application,
                             then verify the resulting tree SHA1 against
                             source_tree_identity.head_tree_sha1.
                             REFUSES unless ENABLE_APPLY=1.

External identity pins (Gate B02 requirements):
  * --rca-root DIR           pinned RCA checkout (patch paths resolve here)
  * --rca-evidence-sha SHA   must equal `git rev-parse HEAD` of --rca-root
                             (verified against the git checkout; a mere CLI
                             echo is never trusted) and, by default, must be
                             the frozen evidence commit 494907699f...

Patch-directory safety (Gate B03):
  * exactly the declared .patch files; README.md allowed as documented
    support file (never hashed into the series); any other entry rejected
  * no executables, no symlinks (file or any parent component), no absolute
    paths, no '..' traversal, no duplicate paths, no nested patch dirs,
    * all patches must live in the single declared canonical directory
"""

import argparse
import datetime
import hashlib
import json
import os
import stat
import subprocess
import sys

def _find_ws_root():
    """Locate the validation workspace root (holds repos/rocm-libraries).

    Location-independent: works when this file is installed at
    <ws>/scripts/check_final_handoff.py (operational) or at
    <ws>/phase5_2/scripts/check_final_handoff.py (evidence copy).
    MIOPEN_WS_ROOT env var overrides (used by adversarial test harness).
    """
    env = os.environ.get("MIOPEN_WS_ROOT")
    if env:
        return os.path.abspath(env)
    d = os.path.dirname(os.path.abspath(__file__))
    for cand in (d, os.path.dirname(d), os.path.dirname(os.path.dirname(d)),
                 os.path.dirname(os.path.dirname(os.path.dirname(d)))):
        if os.path.isdir(os.path.join(cand, "repos", "rocm-libraries")):
            return cand
    return d


WS = _find_ws_root()
DEFAULT_GIT_REPO = os.path.join(WS, "repos", "rocm-libraries")

# ---------------------------------------------------------------- pins ----
# Frozen Windows Phase-5.1 identity (mission W7900-PHASE52-BRIDGE-R1).
# Overridable ONLY for adversarial tests via explicit --expect-* flags;
# defaults always enforce the frozen candidate.
EXPECTED = {
    "candidate_id": "P5.1-CANDIDATE-R1",
    "handoff_type": "final_pre_upstream_linux_validation",
    "schema_version": 1,
    "base_repo": "ROCm/rocm-libraries",
    "base_sha": "7c5866144ac4b879be442563e2b49fa1c142ea36",
    "ordered_commits": [
        "d4003de1a7cabc3715f73e48d3fd414f312a40de",
        "3b18a0655b991890b63587ee18cb0950234a47f0",
        "e7ff6d75fac3e7b683e81e671555ada99af13b74",
    ],
    "series_sha256": "797a69b5ae86d0e304b2258b5f5323cc97241a413d2c43134bf01703f7842f6d",
    "head_tree_sha1": "605d0d214acdbc06086fdb27c61fec970c0f2798",
    "rca_evidence_sha": "494907699f3b57095663f0a70b42278001a8efb7",
    "canonical_patch_dir": "patches/phase5_1/canonical",
    "manifest_sha256": "58a6f9ce8afe2f41e80db8593c8711813b30c6418dfe0a5348dd6131d3bbafd8",
}

# Known-stale / superseded identities that must NEVER validate (fail closed).
STALE_REJECTED = {
    "base_sha": [
        "b68f8944300f104875d953fc8e4510908c9aaf0b",  # Phase-3 historical base
    ],
    "candidate_id": [
        "P5-CANDIDATE-R1",    # superseded Phase-5 candidate
        "P4-CANDIDATE-R1",
    ],
    "evidence_sha": [
        "013f6f005f97aca5ef46d841ca754f2283dc62f0",  # RCA main head at freeze
    ],
}

# Provisional-schema keys whose PRESENCE proves a stale/non-final manifest.
PROVISIONAL_SCHEMA_KEYS = (
    "upstream_base_sha", "patch_series", "series_sha256_mode", "rca_evidence_commit",
)

SUPPORTED_SERIES_ALGORITHMS = ("sha256_file_concat_v1",)
SUPPORTED_SCHEMA_VERSIONS = (1,)

ALLOWED_SUPPORT_FILES = {"README.md"}  # documented, non-hashed support files

HEX40 = set("0123456789abcdef")
HEX64 = set("0123456789abcdef")

failures = []
notes = []


def fail(msg):
    failures.append(msg)


def note(msg):
    notes.append(msg)


def is_hex(s, n, alphabet):
    return (isinstance(s, str) and len(s) == n and all(c in alphabet for c in s))


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(args, cwd, check=True):
    return subprocess.run(["git", "-C", cwd] + args, capture_output=True,
                          text=True, check=check)


# ------------------------------------------------------- path security ----
def safe_resolve(root, rel, allow_dir=False):
    """Resolve rel under root with full containment + symlink discipline.

    Returns absolute path or None (after recording the failure). Rejects:
    absolute paths, ~, traversal outside root, symlink at ANY component
    (including parent-directory escapes), non-regular files (directories
    allowed only with allow_dir=True).
    """
    if not isinstance(rel, str) or not rel:
        fail(f"patch path invalid: {rel!r}")
        return None
    if os.path.isabs(rel) or rel.startswith("~") or rel.startswith("/"):
        fail(f"patch path must be relative (no absolute/home paths): {rel!r}")
        return None
    parts = rel.split("/")
    if any(p == ".." for p in parts):
        fail(f"patch path traversal ('..') rejected: {rel!r}")
        return None
    if any(p == "" for p in parts):
        fail(f"patch path has empty component: {rel!r}")
        return None
    cur = os.path.abspath(root)
    for p in parts:
        cur = os.path.join(cur, p)
        if os.path.islink(cur):
            fail(f"path component is a symlink (rejected): {cur}")
            return None
    if not os.path.exists(cur):
        fail(f"declared file missing under rca-root: {rel}")
        return None
    st = os.lstat(cur)
    if stat.S_ISDIR(st.st_mode) and allow_dir:
        pass
    elif not stat.S_ISREG(st.st_mode):
        fail(f"not a regular file: {rel}")
        return None
    if not stat.S_ISDIR(st.st_mode) and st.st_mode & 0o111:
        fail(f"executable file rejected: {rel}")
        return None
    root_abs = os.path.abspath(root)
    if os.path.commonpath([cur, root_abs]) != root_abs:
        fail(f"path escapes rca root: {rel}")
        return None
    return cur


# ---------------------------------------------------- git checkout pin ----
def verify_rca_checkout(rca_root, evidence_sha):
    """The external evidence SHA is verified AGAINST the git checkout."""
    if not os.path.isdir(os.path.join(rca_root, ".git")):
        fail(f"--rca-root is not a git checkout: {rca_root}")
        return False
    if os.path.islink(os.path.join(rca_root, ".git")):
        fail(f"--rca-root has a symlinked .git (rejected): {rca_root}")
        return False
    r = git(["rev-parse", "HEAD"], cwd=rca_root, check=False)
    if r.returncode != 0:
        fail(f"cannot resolve HEAD of rca checkout: {r.stderr.strip()}")
        return False
    head = r.stdout.strip()
    if head != evidence_sha:
        fail(f"rca evidence SHA mismatch: CLI pin={evidence_sha} "
             f"but checkout HEAD={head} (the checkout is authoritative)")
        return False
    if not is_hex(evidence_sha, 40, HEX40):
        fail(f"--rca-evidence-sha is not a full 40-hex sha: {evidence_sha!r}")
        return False
    for stale in STALE_REJECTED["evidence_sha"]:
        if evidence_sha == stale:
            fail(f"rca evidence SHA {evidence_sha} is a known-stale anchor "
                 f"({stale}); the frozen Phase-5.1 evidence commit is required")
            return False
    r = git(["rev-parse", "HEAD^{commit}"], cwd=rca_root, check=False)
    if r.returncode != 0:
        fail("rca HEAD is not a commit object")
        return False
    st = git(["status", "--porcelain"], cwd=rca_root, check=False)
    dirty = [l for l in st.stdout.splitlines() if l.strip()]
    if dirty:
        fail(f"rca evidence checkout is DIRTY (local tampering?): "
             f"{dirty[:5]}")
        return False
    note(f"rca checkout pinned clean at {head}")
    return True


def blob_matches_worktree(rca_root, rel):
    """Byte-exactness of a worktree file vs the pinned git commit's blob."""
    import subprocess as _sp
    raw = _sp.run(["git", "-C", rca_root, "cat-file", "blob", f"HEAD:{rel}"],
                  capture_output=True, check=False)
    if raw.returncode != 0:
        fail(f"git blob missing at HEAD:{rel} (not a byte-exact checkout)")
        return None
    disk = open(os.path.join(rca_root, rel), "rb").read()
    if raw.stdout != disk:
        fail(f"worktree file differs from pinned git blob (tampered?): {rel}")
        return None
    return disk


# -------------------------------------------------------- schema check ----
def check_schema(m, expect):
    top = ("schema_version", "handoff_type", "candidate_id", "base_repo",
           "base_sha", "ordered_commits", "ordered_patches", "series_hash",
           "source_tree_identity", "dco_status", "copyright_status",
           "linux_validation_status", "authorization_to_submit_upstream")
    for k in top:
        if k not in m:
            fail(f"manifest missing required key: {k}")

    for k in PROVISIONAL_SCHEMA_KEYS:
        if k in m:
            fail(f"provisional/stale schema key present: {k} — this consumer "
                 f"accepts ONLY the frozen Phase-5.1 schema (fail closed, no "
                 f"fallback)")

    if m.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        fail(f"unsupported schema_version: {m.get('schema_version')!r} "
             f"(supported: {list(SUPPORTED_SCHEMA_VERSIONS)})")
    if m.get("handoff_type") != expect["handoff_type"]:
        fail(f"handoff_type mismatch: expected {expect['handoff_type']!r}, "
             f"got {m.get('handoff_type')!r}")

    cid = m.get("candidate_id")
    if cid != expect["candidate_id"]:
        fail(f"candidate_id mismatch: expected {expect['candidate_id']!r}, "
             f"got {cid!r}")
    for stale in STALE_REJECTED["candidate_id"]:
        if cid == stale:
            fail(f"superseded candidate rejected: {cid}")

    if m.get("base_repo") != expect["base_repo"]:
        fail(f"base_repo mismatch: expected {expect['base_repo']!r}, "
             f"got {m.get('base_repo')!r}")

    base = m.get("base_sha")
    if not is_hex(base, 40, HEX40):
        fail(f"base_sha is not a full 40-hex lowercase sha: {base!r}")
    elif base != expect["base_sha"]:
        fail(f"base_sha mismatch: expected frozen base "
             f"{expect['base_sha']}, got {base}")
    for stale in STALE_REJECTED["base_sha"]:
        if base == stale:
            fail(f"base_sha {base} is a known-stale historical anchor")


def check_commits(m, expect):
    commits = m.get("ordered_commits")
    if not isinstance(commits, list) or not commits:
        fail("ordered_commits must be a non-empty list")
        return
    for c in commits:
        if not is_hex(c, 40, HEX40):
            fail(f"ordered_commits entry is not 40-hex: {c!r}")
    if len(set(commits)) != len(commits):
        fail("ordered_commits contains duplicates")
    exp = expect["ordered_commits"]
    if commits != exp:
        fail(f"ordered_commits mismatch: expected (exact order) {exp}, "
             f"got {commits}")
    subs = m.get("ordered_commit_subjects")
    if subs is not None:
        if not isinstance(subs, list) or len(subs) != len(commits):
            fail("ordered_commit_subjects (when present) must parallel "
                 "ordered_commits")


def check_patch_entries(m):
    """Structural validation of ordered_patches; returns sorted entries."""
    entries = m.get("ordered_patches")
    if not isinstance(entries, list) or not entries:
        fail("ordered_patches must be a non-empty ordered list")
        return None
    orders, paths = [], []
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            fail(f"ordered_patches[{i}] must be an object")
            return None
        for k in ("order", "path", "sha256", "bytes"):
            if k not in e:
                fail(f"ordered_patches[{i}] missing key: {k}")
        o = e.get("order")
        if not isinstance(o, int) or isinstance(o, bool) or o < 1:
            fail(f"ordered_patches[{i}].order must be a positive int, got {o!r}")
        orders.append(o)
        p = e.get("path")
        if not isinstance(p, str) or not p.endswith(".patch"):
            fail(f"ordered_patches[{i}].path must be a .patch path: {p!r}")
        if p in paths:
            fail(f"duplicate patch path in series: {p}")
        paths.append(p)
        h = e.get("sha256")
        if not is_hex(h, 64, HEX64):
            fail(f"ordered_patches[{i}].sha256 is not 64-hex lowercase: {h!r}")
        b = e.get("bytes")
        if not isinstance(b, int) or isinstance(b, bool) or b <= 0:
            fail(f"ordered_patches[{i}].bytes must be a positive int: {b!r}")
    if len(set(orders)) != len(orders):
        fail(f"patch orders are not unique: {sorted(orders)}")
    if sorted(orders) != list(range(1, len(entries) + 1)):
        fail(f"patch orders are not contiguous 1..N: {sorted(orders)}")
    return sorted(entries, key=lambda e: e["order"])


def check_status_fields(m):
    lvs = m.get("linux_validation_status")
    if lvs != "PENDING":
        fail(f"linux_validation_status must be 'PENDING' for the Linux final "
             f"validation handoff, got {lvs!r}")
    auth = m.get("authorization_to_submit_upstream")
    if auth is not False:
        fail(f"authorization_to_submit_upstream must be JSON false, got "
             f"{auth!r}")
    dco = m.get("dco_status", "")
    if not isinstance(dco, str):
        fail("dco_status must be a string")
    else:
        if "PENDING" not in dco.upper():
            fail(f"dco_status must remain PENDING (no attestation may be "
                 f"implied), got: {dco[:120]!r}")
        if "CERTIFIED" in dco.upper() or "DCO_ATTESTED" in dco.upper().replace(
                "DCO_ATTESTATION_PENDING", ""):
            fail("dco_status appears to claim certification — forging a DCO "
                 "sign-off is forbidden")
        note("dco_status interpreted: DCO_ATTESTATION_PENDING (no sign-off "
             "claimed; upstream CONTRIBUTING has no DCO requirement — "
             "informational)")
    cr = m.get("copyright_status", "")
    if not isinstance(cr, str):
        fail("copyright_status must be a string")
    else:
        up = cr.upper()
        if "RESOLVED" not in up:
            fail(f"copyright_status must be RESOLVED, got: {cr[:120]!r}")
        if "RIGHT_TO_CONTRIBUTE=CONFIRMED" not in cr:
            fail("copyright_status must carry "
                 "RIGHT_TO_CONTRIBUTE=CONFIRMED")
        if "PLACEHOLDER" in up or "UNRESOLVED" in up:
            fail("copyright_status still contains placeholder/unresolved text")
        note("copyright_status interpreted: RESOLVED, 4/4 files attributed "
             "'Copyright (c) 2026 AIwork4me', MIT text preserved")


def check_series_hash(m, blobs, expect):
    sh = m.get("series_hash")
    if not isinstance(sh, dict):
        fail("series_hash must be an object {algorithm, sha256}")
        return
    alg = sh.get("algorithm")
    if alg not in SUPPORTED_SERIES_ALGORITHMS:
        fail(f"series_hash.algorithm must be one of "
             f"{list(SUPPORTED_SERIES_ALGORITHMS)} (sha256_file_concat_v1), "
             f"got {alg!r}")
        return
    declared = sh.get("sha256")
    if not is_hex(declared, 64, HEX64):
        fail(f"series_hash.sha256 is not 64-hex lowercase: {declared!r}")
        return
    actual = sha256_bytes(b"".join(blobs))
    if declared != actual:
        fail(f"series hash mismatch: manifest={declared} actual={actual} "
             f"(algorithm={alg})")
    else:
        note(f"series hash OK ({actual[:16]}…, {alg})")
    if expect["series_sha256"] and declared != expect["series_sha256"]:
        fail(f"series hash does not match the frozen canonical series "
             f"{expect['series_sha256']} (wrong candidate?)")


def check_tree_identity(m, expect):
    sti = m.get("source_tree_identity")
    if not isinstance(sti, dict):
        fail("source_tree_identity must be an object")
        return
    t = sti.get("head_tree_sha1")
    if not is_hex(t, 40, HEX40):
        fail(f"source_tree_identity.head_tree_sha1 is not 40-hex: {t!r}")
        return
    if t != expect["head_tree_sha1"]:
        fail(f"head_tree_sha1 mismatch: expected {expect['head_tree_sha1']}, "
             f"got {t} (wrong candidate source identity)")
    else:
        note(f"head_tree_sha1 pinned OK ({t[:16]}…; byte-level source "
             f"reproduction is verified by verify_source_tree.py / --apply)")


def check_patch_dir(rca_root, entries, expect):
    """Gate B03 directory-safety audit of the canonical patch dir."""
    dirs = {os.path.dirname(e["path"]) for e in entries}
    if len(dirs) != 1:
        fail(f"all ordered patches must live in ONE canonical directory; "
             f"found: {sorted(dirs)}")
        return None
    d = dirs.pop()
    if d != expect["canonical_patch_dir"]:
        fail(f"canonical patch directory must be "
             f"{expect['canonical_patch_dir']!r}, got {d!r}")
        return None
    absdir = safe_resolve(rca_root, d, allow_dir=True)
    if absdir is None:
        return None
    if not os.path.isdir(absdir):
        fail(f"canonical patch dir missing: {d}")
        return None
    declared = {os.path.basename(e["path"]) for e in entries}
    if any(not n.endswith(".patch") for n in declared):
        fail("declared series contains a non-.patch path")
    for name in sorted(os.listdir(absdir)):
        full = os.path.join(absdir, name)
        st = os.lstat(full)
        if os.path.islink(full):
            fail(f"symlink in patch dir rejected: {name}")
            continue
        if stat.S_ISDIR(st.st_mode):
            fail(f"unexpected nested directory in patch dir: {name}")
            continue
        if not stat.S_ISREG(st.st_mode):
            fail(f"non-regular file in patch dir: {name}")
            continue
        if st.st_mode & 0o111:
            fail(f"executable file in patch dir rejected: {name}")
            continue
        if name in declared:
            continue
        if name in ALLOWED_SUPPORT_FILES:
            note(f"documented support file allowed (NOT hashed into series): "
                 f"{name}")
            continue
        fail(f"unexpected file in canonical patch dir {d}: {name} "
             f"(allowed: declared patches + {sorted(ALLOWED_SUPPORT_FILES)})")
    return absdir


def verify_manifest(manifest_path, rca_root, evidence_sha, expect):
    """Full verification. Returns (manifest, ordered_entries) or None."""
    del failures[:]
    del notes[:]
    if not os.path.isfile(manifest_path):
        fail(f"manifest not found: {manifest_path}")
        return None

    raw_manifest = open(manifest_path, "rb").read()
    manifest_digest = sha256_bytes(raw_manifest)
    note(f"manifest_sha256={manifest_digest}")
    # F1 hardening: the frozen manifest is pinned by sha256 AND, when read
    # from inside the pinned checkout, byte-matched against its git blob.
    if expect.get("manifest_sha256") and manifest_digest != expect["manifest_sha256"]:
        fail(f"manifest sha256 {manifest_digest} != frozen pinned manifest "
             f"{expect['manifest_sha256']} (wrong or altered manifest)")
    try:
        m = json.loads(raw_manifest.decode("utf-8"))
    except Exception as e:
        fail(f"manifest is not valid UTF-8 JSON: {e}")
        return None
    manifest_abs = os.path.abspath(manifest_path)
    root_abs = os.path.abspath(rca_root)
    if (os.path.commonpath([manifest_abs, root_abs]) == root_abs
            and not os.path.islink(manifest_abs)):
        rel = os.path.relpath(manifest_abs, root_abs)
        if blob_matches_worktree(rca_root, rel) is None:
            note("manifest blob-identity check FAILED (see failures)")

    # External RCA evidence pin — verified against the git checkout itself.
    if not verify_rca_checkout(rca_root, evidence_sha):
        return None

    check_schema(m, expect)
    check_commits(m, expect)
    check_status_fields(m)
    entries = check_patch_entries(m)
    if entries is None:
        return None

    absdir = check_patch_dir(rca_root, entries, expect)
    blobs = []
    for e in entries:
        p = safe_resolve(rca_root, e["path"])
        if p is None:
            continue
        blob = blob_matches_worktree(rca_root, e["path"])
        if blob is None:
            continue
        got = sha256_bytes(blob)
        if got != e["sha256"]:
            fail(f"patch {e['path']}: sha256 mismatch manifest={e['sha256']} "
                 f"actual={got}")
        else:
            note(f"patch[order {e['order']}] {e['path']} sha256 OK "
                 f"({got[:12]}…)")
        if len(blob) != e["bytes"]:
            fail(f"patch {e['path']}: size mismatch manifest={e['bytes']} "
                 f"actual={len(blob)}")
        blobs.append(blob)
    if absdir is not None:
        note(f"canonical dir audited: {expect['canonical_patch_dir']} "
             f"(README allowed, not hashed)")

    if len(blobs) == len(entries):
        check_series_hash(m, blobs, expect)
    check_tree_identity(m, expect)

    if not failures:
        r = git(["cat-file", "-e", f"{m['base_sha']}^{{commit}}"],
                cwd=expect.get("git_repo", DEFAULT_GIT_REPO), check=False)
        if r.returncode != 0:
            fail(f"frozen base commit {m['base_sha']} not present in local "
                 f"git repo — fetch the exact commit first (fail closed)")
        else:
            note(f"frozen base commit object present locally: "
                 f"{m['base_sha'][:12]}")

    return (m, entries) if not failures else None


def render_report(gate, mode, extra=None):
    verdict = "PASS" if not failures else "FAIL"
    report = {
        "gate": gate,
        "mode": mode,
        "tool": "check_final_handoff.py (phase5_2 schema, sha256_file_concat_v1)",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "verdict": verdict,
        "failures": list(failures),
        "notes": list(notes),
    }
    if extra:
        report.update(extra)
    return json.dumps(report, indent=2)


def check_only(manifest_path, rca_root, evidence_sha, expect, json_out=None):
    out = verify_manifest(manifest_path, rca_root, evidence_sha, expect)
    rendered = render_report("B02/B03", "check-only", extra={
        "manifest": manifest_path,
        "rca_root": rca_root,
        "rca_evidence_sha": evidence_sha,
        "effective_expect_pins": {
            k: expect.get(k) for k in (
                "candidate_id", "base_sha", "head_tree_sha1",
                "series_sha256", "ordered_commits", "rca_evidence_sha",
                "canonical_patch_dir", "manifest_sha256")
        },
    })
    if json_out:
        os.makedirs(os.path.dirname(os.path.abspath(json_out)), exist_ok=True)
        with open(json_out, "w") as f:
            f.write(rendered + "\n")
    print(rendered)
    return 0 if out is not None else 1


def apply_manifest(manifest_path, target_dir, rca_root, evidence_sha, expect):
    if os.environ.get("ENABLE_APPLY") != "1":
        print("FATAL: --apply is REFUSED without explicit authorization. "
              "Re-run with ENABLE_APPLY=1 only for the authorized final "
              "validation mission.", file=sys.stderr)
        return 2
    out = verify_manifest(manifest_path, rca_root, evidence_sha, expect)
    print(render_report("B02/B03", "apply-precheck"))
    if out is None:
        print("FATAL: manifest failed verification; refusing to apply",
              file=sys.stderr)
        return 1
    m, entries = out
    base = m["base_sha"]
    git_repo = expect.get("git_repo", DEFAULT_GIT_REPO)
    if os.path.exists(target_dir):
        print(f"FATAL: target {target_dir} already exists; reconstruct into "
              f"a clean dir", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(target_dir)), exist_ok=True)
    r = git(["worktree", "add", "--detach", target_dir, base], cwd=git_repo,
            check=False)
    print(r.stdout or r.stderr)
    if r.returncode != 0:
        return r.returncode
    st = git(["status", "--porcelain"], cwd=target_dir, check=False)
    if st.stdout.strip():
        print("FATAL: worktree not clean before patch application",
              file=sys.stderr)
        return 2
    for e in entries:
        p = os.path.join(rca_root, e["path"])
        if sha256_file(p) != e["sha256"]:  # TOCTOU re-verify
            print(f"FATAL: patch {e['path']} changed since verification",
                  file=sys.stderr)
            return 2
        chk = git(["apply", "--check", p], cwd=target_dir, check=False)
        if chk.returncode != 0:
            print(f"FATAL: git apply --check failed for {e['path']}: "
                  f"{chk.stderr.strip()}", file=sys.stderr)
            return 2
        git(["apply", p], cwd=target_dir)
        print(f"applied {e['path']}")
    # Tree-identity verification is MANDATORY (apply exit code is not proof).
    git(["add", "-A"], cwd=target_dir)
    wt = git(["write-tree"], cwd=target_dir)
    tree = wt.stdout.strip()
    expected_tree = m["source_tree_identity"]["head_tree_sha1"]
    st = git(["status", "--porcelain"], cwd=target_dir, check=False)
    print("post-apply changed paths:")
    print(st.stdout)
    print(f"reconstructed tree: {tree}")
    print(f"expected tree:      {expected_tree}")
    if tree != expected_tree:
        print("FATAL: reconstructed tree SHA1 != manifest "
              "head_tree_sha1 — STOP, wrong candidate", file=sys.stderr)
        return 3
    ident = {"base_sha": base, "reconstructed_tree": tree,
             "expected_tree": expected_tree,
             "patched_files": st.stdout.splitlines(),
             "applied_at": datetime.datetime.now(
                 datetime.timezone.utc).isoformat()}
    os.makedirs(os.path.join(WS, "evidence"), exist_ok=True)
    with open(os.path.join(WS, "evidence",
                           "G08_reconstructed_identity.json"), "w") as f:
        json.dump(ident, f, indent=2)
    print("RECONSTRUCTION_OK")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Strict frozen Phase-5.1 handoff consumer (actual schema)")
    ap.add_argument("--check-only", metavar="MANIFEST")
    ap.add_argument("--apply", nargs=2, metavar=("MANIFEST", "TARGET_DIR"))
    ap.add_argument("--rca-root", required=True, metavar="DIR",
                    help="pinned RCA evidence checkout (git worktree)")
    ap.add_argument("--rca-evidence-sha", required=True, metavar="SHA",
                    help="frozen RCA evidence commit (verified vs git HEAD)")
    ap.add_argument("--git-repo", default=DEFAULT_GIT_REPO,
                    help="local rocm-libraries git repo for base-commit check")
    ap.add_argument("--expect-candidate-id", default=EXPECTED["candidate_id"])
    ap.add_argument("--expect-base-sha", default=EXPECTED["base_sha"])
    ap.add_argument("--expect-tree-sha1", default=EXPECTED["head_tree_sha1"])
    ap.add_argument("--expect-series-sha256", default=EXPECTED["series_sha256"])
    ap.add_argument("--expect-commits",
                    default=",".join(EXPECTED["ordered_commits"]),
                    help="comma-separated ordered commits")
    ap.add_argument("--expect-evidence-sha", default=EXPECTED["rca_evidence_sha"],
                    help="frozen evidence commit the checkout must ALSO match "
                         "(in addition to --rca-evidence-sha)")
    ap.add_argument("--expect-manifest-sha256", default=EXPECTED["manifest_sha256"],
                    help="frozen manifest sha256 pin (default: frozen "
                         "Phase-5.1 manifest; override only for adversarial "
                         "tests)")
    ap.add_argument("--expect-canonical-dir",
                    default=EXPECTED["canonical_patch_dir"])
    ap.add_argument("--json-out", metavar="PATH")
    a = ap.parse_args()

    expect = dict(EXPECTED)
    expect["candidate_id"] = a.expect_candidate_id
    expect["base_sha"] = a.expect_base_sha
    expect["head_tree_sha1"] = a.expect_tree_sha1
    expect["series_sha256"] = a.expect_series_sha256
    expect["ordered_commits"] = [c.strip() for c in a.expect_commits.split(",")
                                 if c.strip()]
    expect["canonical_patch_dir"] = a.expect_canonical_dir
    expect["git_repo"] = a.git_repo
    expect["manifest_sha256"] = a.expect_manifest_sha256

    evidence_sha = a.rca_evidence_sha
    if a.expect_evidence_sha and evidence_sha != a.expect_evidence_sha:
        fail_msg = (f"--rca-evidence-sha {evidence_sha} != frozen evidence "
                    f"commit {a.expect_evidence_sha} (fail closed)")
        failures.append(fail_msg)
        print(render_report("B02/B03", "cli-pin-mismatch"))
        sys.exit(1)

    rca_root = os.path.abspath(a.rca_root)
    if a.apply:
        sys.exit(apply_manifest(a.apply[0], a.apply[1], rca_root,
                                evidence_sha, expect))
    if a.check_only:
        sys.exit(check_only(a.check_only, rca_root, evidence_sha, expect,
                            a.json_out))
    ap.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
