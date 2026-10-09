#!/usr/bin/env python3
"""Strict R2-aware consumer for the FROZEN Windows Phase-5.1-R2 handoff
manifest (findings/phase5_1_r2/FINAL_HANDOFF.json @ RCA evidence commit
c8417161125dc33275b7ac615298b449a81e7cf8).

Derived from the Phase-5.2 consumer (linux-w7900/phase5.2.1/wrappers/
check_final_handoff.py, sha256 cea4f1fe...) with the following R2 migration:

  * EXPECTED pins -> P5.1-CANDIDATE-R2 identities (series 48308f6d...,
    head tree b983cadd..., evidence commit c8417161..., canonical dir
    patches/phase5_1_r2/canonical, manifest sha256 55e88f4c...).
  * base_repo: the ACTUAL R2 schema records a full URL
    (https://github.com/ROCm/rocm-libraries). The R1-era shorthand
    'ROCm/rocm-libraries' is NOT hardcoded — the manifest is authoritative
    for representation; the consumer pins the URL form and also accepts
    the documented shorthand equivalence only via explicit expectation
    override for adversarial tests.
  * STALE_REJECTED extended: R1 candidate P5.1-CANDIDATE-R1, R1 evidence
    commit 494907699f..., R1 series 797a69b5..., R1 head tree 605d0d21...,
    and the R2 ancestor evidence snapshot cd9c36c5... (may be cross-checked
    but must never silently replace the pinned evidence commit).
  * R1 series hash must NOT appear anywhere outside the `supersedes` object.
  * ordered_commit_subjects are cross-checked against the Subject: headers
    of the actual patch bytes (ties manifest commits to patch content).
  * windows_validation_status: all 16 top-level statuses must be PASS-prefixed
    (honest Windows evidence, matches published verify_final_handoff.py).
  * dco_status must remain UNSIGNED / pending; no forged certification.

Modes (identical discipline to Phase 5.2):
  --check-only MANIFEST      validate manifest + recompute every hash from
                             RAW BYTES + verify the pinned RCA git checkout.
  --apply MANIFEST DIR       reconstruct the patched tree in DIR from a
                             clean git worktree + ordered patch application,
                             then verify the resulting tree SHA1 against
                             source_tree_identity.head_tree_sha1.
                             REFUSES unless ENABLE_APPLY=1.

There is NO --skip-verification option and NO permissive missing-hash
behavior. Every hash the manifest carries is recomputed from raw bytes.
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
    env = os.environ.get("MIOPEN_WS_ROOT")
    if env:
        return os.path.abspath(env)
    d = os.path.dirname(os.path.abspath(__file__))
    for cand in (d, os.path.dirname(d), os.path.dirname(os.path.dirname(d)),
                 os.path.dirname(os.path.dirname(os.path.dirname(d))),
                 os.path.dirname(os.path.dirname(os.path.dirname(
                     os.path.dirname(d))))):
        if os.path.isdir(os.path.join(cand, "repos", "rocm-libraries")):
            return cand
    return d


WS = _find_ws_root()
DEFAULT_GIT_REPO = os.path.join(WS, "repos", "rocm-libraries")

# ------------------------------------------------------------- R2 pins ----
EXPECTED = {
    "candidate_id": "P5.1-CANDIDATE-R2",
    "handoff_type": "final_pre_upstream_linux_validation",
    "schema_version": 1,
    "base_repo": "https://github.com/ROCm/rocm-libraries",
    "base_sha": "7c5866144ac4b879be442563e2b49fa1c142ea36",
    "ordered_commits": [
        "01a77dab8c4cf23d1e49273fa3c88bb0bb4fc887",
        "8188b803b8304fc5933caa52ee27a58d01a78b04",
        "f18c4de94b229bbe3e8501d70e3e2461425c69de",
    ],
    "series_sha256": "48308f6dccfd80f099a458ad5033f815d95f86d2ab54dba1a0344c976b5a3f02",
    "head_tree_sha1": "b983caddf9f9f561e7d1b590deadb16267c2de15",
    "rca_evidence_sha": "c8417161125dc33275b7ac615298b449a81e7cf8",
    "canonical_patch_dir": "patches/phase5_1_r2/canonical",
    "manifest_sha256": "55e88f4c2c9bbc0195a2a4b63ceb52786e36d49e4fd0e097808cdf5aab4df393",
}

STALE_REJECTED = {
    "base_sha": [
        "b68f8944300f104875d953fc8e4510908c9aaf0b",  # Phase-3 historical base
    ],
    "candidate_id": [
        "P5.1-CANDIDATE-R1",   # superseded by R2
        "P5-CANDIDATE-R1",
        "P4-CANDIDATE-R1",
    ],
    "evidence_sha": [
        "494907699f3b57095663f0a70b42278001a8efb7",  # R1 evidence commit
        "cd9c36c52a7702eef4a2b4ba899a4e35dfba8b1a",  # R2 ancestor snapshot:
        # may be cross-checked, must never silently replace the pinned
        # evidence commit c8417161 (mission SS1)
        "013f6f005f97aca5ef46d841ca754f2283dc62f0",  # RCA main head at freeze
    ],
    "series_sha256": [
        "797a69b5ae86d0e304b2258b5f5323cc97241a413d2c43134bf01703f7842f6d",  # R1
    ],
    "head_tree_sha1": [
        "605d0d214acdbc06086fdb27c61fec970c0f2798",  # R1 tree
    ],
}

PROVISIONAL_SCHEMA_KEYS = (
    "upstream_base_sha", "patch_series", "series_sha256_mode",
    "rca_evidence_commit",
)

SUPPORTED_SERIES_ALGORITHMS = ("sha256_file_concat_v1",)
SUPPORTED_SCHEMA_VERSIONS = (1,)
ALLOWED_SUPPORT_FILES = {"README.md", ".gitattributes"}
# .gitattributes is tracked in the frozen R2 evidence commit (blob ec1ffa81)
# with exactly this content — it disables git text auto-conversion for the
# patch files, which is what guarantees byte-exact series hashing across
# platforms. Content-pinned here; any other content fails.
EXPECTED_GITATTRIBUTES = "*.patch -text\n"

WINDOWS_STATUS_KEYS = (
    "cmake_configure", "target_build", "ctest_discovery", "ctest_execution",
    "ctest_clean_env_execution", "ci_ab_matrix", "exit_code_fixture",
    "restricted_list_parity", "miopen_dll_build", "dll_load_provenance",
    "hiprtc_dll_provenance", "nostl_runtime", "batchnorm_numerics",
    "yolo_train_amp_false", "yolo_train_amp_default", "wheel_dll_restored",
)

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
            fail(f"rca evidence SHA {evidence_sha} is a known-stale anchor; "
                 f"the pinned Phase-5.1-R2 evidence commit c8417161 is required")
            return False
    r = git(["rev-parse", "HEAD^{commit}"], cwd=rca_root, check=False)
    if r.returncode != 0:
        fail("rca HEAD is not a commit object")
        return False
    st = git(["status", "--porcelain"], cwd=rca_root, check=False)
    dirty = [l for l in st.stdout.splitlines() if l.strip()]
    if dirty:
        fail(f"rca evidence checkout is DIRTY (local tampering?): {dirty[:5]}")
        return False
    note(f"rca checkout pinned clean at {head}")
    return True


def blob_matches_worktree(rca_root, rel):
    raw = subprocess.run(["git", "-C", rca_root, "cat-file", "blob",
                          f"HEAD:{rel}"], capture_output=True, check=False)
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
                 f"accepts ONLY the frozen R2 schema (fail closed, no fallback)")

    if m.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        fail(f"unsupported schema_version: {m.get('schema_version')!r}")
    if m.get("handoff_type") != expect["handoff_type"]:
        fail(f"handoff_type mismatch: expected {expect['handoff_type']!r}, "
             f"got {m.get('handoff_type')!r}")

    cid = m.get("candidate_id")
    if cid != expect["candidate_id"]:
        fail(f"candidate_id mismatch: expected {expect['candidate_id']!r}, got {cid!r}")
    for stale in STALE_REJECTED["candidate_id"]:
        if cid == stale:
            fail(f"superseded candidate rejected: {cid}")

    br = m.get("base_repo")
    if br != expect["base_repo"]:
        fail(f"base_repo mismatch: expected the ACTUAL R2 URL form "
             f"{expect['base_repo']!r}, got {br!r}")

    base = m.get("base_sha")
    if not is_hex(base, 40, HEX40):
        fail(f"base_sha is not a full 40-hex lowercase sha: {base!r}")
    elif base != expect["base_sha"]:
        fail(f"base_sha mismatch: expected frozen base {expect['base_sha']}, got {base}")
    for stale in STALE_REJECTED["base_sha"]:
        if base == stale:
            fail(f"base_sha {base} is a known-stale historical anchor")

    # R1 identity leakage: the R1 series hash may ONLY live in `supersedes`.
    body_no_supersedes = {k: v for k, v in m.items() if k != "supersedes"}
    if any(s in json.dumps(body_no_supersedes)
           for s in STALE_REJECTED["series_sha256"]):
        fail("stale R1 series hash present outside the supersedes record")
    if any(t in json.dumps(body_no_supersedes)
           for t in STALE_REJECTED["head_tree_sha1"]):
        fail("stale R1 head tree SHA present outside the supersedes record")


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
        fail(f"ordered_commits mismatch: expected (exact order) {exp}, got {commits}")
    subs = m.get("ordered_commit_subjects")
    if not isinstance(subs, list) or len(subs) != len(commits):
        fail("ordered_commit_subjects must parallel ordered_commits")


def check_patch_entries(m):
    entries = m.get("ordered_patches")
    if not isinstance(entries, list) or not entries:
        fail("ordered_patches must be a non-empty ordered list")
        return None
    orders, paths = [], []
    structural_fail = False
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            fail(f"ordered_patches[{i}] must be an object")
            return None
        for k in ("order", "path", "sha256", "bytes"):
            if k not in e:
                fail(f"ordered_patches[{i}] missing key: {k}")
                structural_fail = True
        if structural_fail:
            continue
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
    if structural_fail:
        return None
    if len(set(orders)) != len(orders):
        fail(f"patch orders are not unique: {sorted(orders)}")
    if sorted(orders) != list(range(1, len(entries) + 1)):
        fail(f"patch orders are not contiguous 1..N: {sorted(orders)}")
    return sorted(entries, key=lambda e: e["order"])


def check_status_fields(m):
    lvs = m.get("linux_validation_status")
    if lvs != "PENDING":
        fail(f"linux_validation_status must be 'PENDING' in the frozen "
             f"manifest (Linux results are reported separately by the Linux "
             f"validation authority, never by mutating this manifest), got {lvs!r}")
    auth = m.get("authorization_to_submit_upstream")
    if auth is not False:
        fail(f"authorization_to_submit_upstream must be JSON false, got {auth!r}")
    for k in ("upstream_pr_created", "upstream_issue_created",
              "upstream_comment_posted", "internal_pr_created"):
        if m.get(k) is not False:
            fail(f"{k} must be JSON false in the frozen manifest")
    ev = m.get("windows_validation_status")
    if not isinstance(ev, dict):
        fail("windows_validation_status must be an object")
    else:
        for k in WINDOWS_STATUS_KEYS:
            if not str(ev.get(k, "")).startswith("PASS"):
                fail(f"windows_validation_status.{k} is not PASS: {ev.get(k)!r}")
    dco = m.get("dco_status", "")
    if not isinstance(dco, str):
        fail("dco_status must be a string")
    else:
        if "UNSIGNED" not in dco.upper() and "PENDING" not in dco.upper():
            fail(f"dco_status must remain UNSIGNED/pending (no attestation "
                 f"may be implied), got: {dco[:120]!r}")
        if "CERTIFIED" in dco.upper():
            fail("dco_status appears to claim certification — forging a DCO "
                 "sign-off is forbidden")
    cr = m.get("copyright_status", "")
    if not isinstance(cr, str):
        fail("copyright_status must be a string")
    else:
        up = cr.upper()
        if "RESOLVED" not in up:
            fail(f"copyright_status must be RESOLVED, got {cr[:120]!r}")
        if "PLACEHOLDER" in up or "UNRESOLVED" in up:
            fail("copyright_status still contains placeholder/unresolved text")


def check_series_hash(m, blobs, expect):
    sh = m.get("series_hash")
    if not isinstance(sh, dict):
        fail("series_hash must be an object {algorithm, sha256}")
        return
    alg = sh.get("algorithm")
    if alg not in SUPPORTED_SERIES_ALGORITHMS:
        fail(f"series_hash.algorithm must be one of "
             f"{list(SUPPORTED_SERIES_ALGORITHMS)}, got {alg!r}")
        return
    declared = sh.get("sha256")
    if not is_hex(declared, 64, HEX64):
        fail(f"series_hash.sha256 is not 64-hex lowercase: {declared!r}")
        return
    actual = sha256_bytes(b"".join(blobs))
    if declared != actual:
        fail(f"series hash mismatch: manifest={declared} actual={actual} (algorithm={alg})")
    else:
        note(f"series hash OK ({actual[:16]}, {alg})")
    if expect["series_sha256"] and declared != expect["series_sha256"]:
        fail(f"series hash does not match the frozen R2 canonical series "
             f"{expect['series_sha256']} (wrong candidate? / R1 substitution?)")
    for stale in STALE_REJECTED["series_sha256"]:
        if declared == stale:
            fail(f"series hash {declared} is the superseded R1 series")


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
        note(f"head_tree_sha1 pinned OK ({t[:16]}; byte-level source "
             f"reproduction verified by --apply / Gate L03)")
    for stale in STALE_REJECTED["head_tree_sha1"]:
        if t == stale:
            fail(f"head_tree_sha1 {t} is the superseded R1 tree")
    cf = sti.get("changed_files_vs_base")
    if not isinstance(cf, dict) or not cf:
        fail("source_tree_identity.changed_files_vs_base must be a non-empty object")
        return
    for f, rec in cf.items():
        if not isinstance(rec, dict) or "sha256" not in rec or "bytes" not in rec:
            fail(f"changed_files_vs_base[{f!r}] must carry sha256+bytes")


def check_patch_dir(rca_root, entries, expect):
    dirs = {os.path.dirname(e["path"]) for e in entries}
    if len(dirs) != 1:
        fail(f"all ordered patches must live in ONE canonical directory; found: {sorted(dirs)}")
        return None
    d = dirs.pop()
    if d != expect["canonical_patch_dir"]:
        fail(f"canonical patch directory must be {expect['canonical_patch_dir']!r}, got {d!r}")
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
            if name == ".gitattributes":
                ga = open(full, "rb").read().decode("utf-8", "replace")
                if ga != EXPECTED_GITATTRIBUTES:
                    fail(f".gitattributes content differs from frozen pin: {ga!r}")
                    continue
                note("frozen support file .gitattributes content-pinned "
                     "('\''*.patch -text'\'', guards byte-exact patch hashing)")
                continue
            note(f"documented support file allowed (NOT hashed into series): {name}")
            continue
        fail(f"unexpected file in canonical patch dir {d}: {name} "
             f"(allowed: declared patches + {sorted(ALLOWED_SUPPORT_FILES)})")
    return absdir


def patch_subjects_from_bytes(blobs):
    """Extract Subject: header value from each patch's email headers.

    RFC-2822 unfolding: a folded continuation line (' STL is reachable')
    keeps exactly one joining space, matching git mailinfo behavior.
    """
    subjects = []
    for raw in blobs:
        subj = None
        for line in raw.decode("utf-8", "replace").splitlines():
            if line.startswith("Subject:"):
                subj = line[len("Subject:"):].strip()
                if subj.startswith("[PATCH"):
                    subj = subj.split("] ", 1)[-1]
            elif subj is not None and line.startswith(" "):
                subj += " " + line.strip()
            elif subj is not None:
                break
        subjects.append(subj)
    return subjects


def verify_manifest(manifest_path, rca_root, evidence_sha, expect):
    del failures[:]
    del notes[:]
    if not os.path.isfile(manifest_path):
        fail(f"manifest not found: {manifest_path}")
        return None

    raw_manifest = open(manifest_path, "rb").read()
    manifest_digest = sha256_bytes(raw_manifest)
    note(f"manifest_sha256={manifest_digest}")
    if expect.get("manifest_sha256") and manifest_digest != expect["manifest_sha256"]:
        fail(f"manifest sha256 {manifest_digest} != frozen pinned R2 manifest "
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
            fail(f"patch {e['path']}: sha256 mismatch manifest={e['sha256']} actual={got}")
        else:
            note(f"patch[order {e['order']}] {e['path']} sha256 OK ({got[:12]})")
        if len(blob) != e["bytes"]:
            fail(f"patch {e['path']}: size mismatch manifest={e['bytes']} actual={len(blob)}")
        blobs.append(blob)
    if absdir is not None:
        note(f"canonical dir audited: {expect['canonical_patch_dir']} (README allowed, not hashed)")

    if len(blobs) == len(entries):
        check_series_hash(m, blobs, expect)
        # tie manifest commit subjects to actual patch bytes
        subs = m.get("ordered_commit_subjects") or []
        if len(subs) == len(blobs):
            from_bytes = patch_subjects_from_bytes(blobs)
            for i, (a, b) in enumerate(zip(subs, from_bytes), 1):
                if a != b:
                    fail(f"ordered_commit_subjects[{i}] {a!r} != patch Subject header {b!r}")
            else:
                note("commit subjects cross-checked against patch Subject: headers")
    check_tree_identity(m, expect)

    if not failures:
        r = git(["cat-file", "-e", f"{m['base_sha']}^{{commit}}"],
                cwd=expect.get("git_repo", DEFAULT_GIT_REPO), check=False)
        if r.returncode != 0:
            fail(f"frozen base commit {m['base_sha']} not present in local "
                 f"git repo — fetch the exact commit first (fail closed)")
        else:
            note(f"frozen base commit object present locally: {m['base_sha'][:12]}")

    return (m, entries) if not failures else None


def render_report(gate, mode, extra=None):
    verdict = "PASS" if not failures else "FAIL"
    report = {
        "gate": gate,
        "mode": mode,
        "tool": "check_final_handoff_r2.py (phase5_3 R2 schema consumer)",
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
    rendered = render_report("L02", "check-only", extra={
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
              "validation mission (W7900-PHASE53-R2-FINAL-AB).", file=sys.stderr)
        return 2
    out = verify_manifest(manifest_path, rca_root, evidence_sha, expect)
    print(render_report("L02", "apply-precheck"))
    if out is None:
        print("FATAL: manifest failed verification; refusing to apply", file=sys.stderr)
        return 1
    m, entries = out
    base = m["base_sha"]
    git_repo = expect.get("git_repo", DEFAULT_GIT_REPO)
    if os.path.exists(target_dir):
        print(f"FATAL: target {target_dir} already exists; reconstruct into a clean dir",
              file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(target_dir)), exist_ok=True)
    r = git(["worktree", "add", "--detach", target_dir, base], cwd=git_repo, check=False)
    print(r.stdout or r.stderr)
    if r.returncode != 0:
        return r.returncode
    st = git(["status", "--porcelain"], cwd=target_dir, check=False)
    if st.stdout.strip():
        print("FATAL: worktree not clean before patch application", file=sys.stderr)
        return 2
    for e in entries:
        p = os.path.join(rca_root, e["path"])
        if sha256_file(p) != e["sha256"]:  # TOCTOU re-verify
            print(f"FATAL: patch {e['path']} changed since verification", file=sys.stderr)
            return 2
        chk = git(["apply", "--check", p], cwd=target_dir, check=False)
        if chk.returncode != 0:
            print(f"FATAL: git apply --check failed for {e['path']}: {chk.stderr.strip()}",
                  file=sys.stderr)
            return 2
        git(["apply", p], cwd=target_dir)
        print(f"applied {e['path']}")
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
        print("FATAL: reconstructed tree SHA1 != manifest head_tree_sha1 — STOP, "
              "wrong candidate", file=sys.stderr)
        return 3
    print("RECONSTRUCTION_OK")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Strict frozen Phase-5.1-R2 handoff consumer (R2 schema)")
    ap.add_argument("--check-only", metavar="MANIFEST")
    ap.add_argument("--apply", nargs=2, metavar=("MANIFEST", "TARGET_DIR"))
    ap.add_argument("--rca-root", required=True, metavar="DIR")
    ap.add_argument("--rca-evidence-sha", required=True, metavar="SHA")
    ap.add_argument("--git-repo", default=DEFAULT_GIT_REPO)
    ap.add_argument("--expect-candidate-id", default=EXPECTED["candidate_id"])
    ap.add_argument("--expect-base-sha", default=EXPECTED["base_sha"])
    ap.add_argument("--expect-tree-sha1", default=EXPECTED["head_tree_sha1"])
    ap.add_argument("--expect-series-sha256", default=EXPECTED["series_sha256"])
    ap.add_argument("--expect-commits", default=",".join(EXPECTED["ordered_commits"]))
    ap.add_argument("--expect-evidence-sha", default=EXPECTED["rca_evidence_sha"])
    ap.add_argument("--expect-manifest-sha256", default=EXPECTED["manifest_sha256"],
                    help="frozen R2 manifest sha256 pin (override only for "
                         "adversarial tests)")
    ap.add_argument("--expect-base-repo", default=EXPECTED["base_repo"])
    ap.add_argument("--expect-canonical-dir", default=EXPECTED["canonical_patch_dir"])
    ap.add_argument("--json-out", metavar="PATH")
    a = ap.parse_args()

    # Secondary authorization for any non-default expectation override
    # (M1 hardening from the Gate L02 independent audit): identity pins are
    # DEFAULT-enforced; relaxing them requires explicit operator intent.
    override_vals = {
        "--expect-candidate-id": (a.expect_candidate_id, EXPECTED["candidate_id"]),
        "--expect-base-sha": (a.expect_base_sha, EXPECTED["base_sha"]),
        "--expect-tree-sha1": (a.expect_tree_sha1, EXPECTED["head_tree_sha1"]),
        "--expect-series-sha256": (a.expect_series_sha256, EXPECTED["series_sha256"]),
        "--expect-commits": (a.expect_commits, ",".join(EXPECTED["ordered_commits"])),
        "--expect-evidence-sha": (a.expect_evidence_sha, EXPECTED["rca_evidence_sha"]),
        "--expect-manifest-sha256": (a.expect_manifest_sha256, EXPECTED["manifest_sha256"]),
        "--expect-base-repo": (a.expect_base_repo, EXPECTED["base_repo"]),
        "--expect-canonical-dir": (a.expect_canonical_dir, EXPECTED["canonical_patch_dir"]),
    }
    non_default = {k: v for k, (v, d) in override_vals.items() if v != d}
    if non_default and os.environ.get("ALLOW_EXPECT_OVERRIDE") != "1":
        failures.append(
            f"non-default expectation overrides {sorted(non_default)} require "
            f"ALLOW_EXPECT_OVERRIDE=1 (adversarial-test authorization only; "
            f"defaults enforce the frozen R2 candidate)")
        print(render_report("L02", "override-unauthorized"))
        sys.exit(1)
    if not a.expect_manifest_sha256:
        failures.append("--expect-manifest-sha256 must not be empty: the frozen "
                        "manifest digest pin is mandatory (fail closed)")
        print(render_report("L02", "override-empty-pin"))
        sys.exit(1)

    expect = dict(EXPECTED)
    expect["candidate_id"] = a.expect_candidate_id
    expect["base_sha"] = a.expect_base_sha
    expect["head_tree_sha1"] = a.expect_tree_sha1
    expect["series_sha256"] = a.expect_series_sha256
    expect["ordered_commits"] = [c.strip() for c in a.expect_commits.split(",") if c.strip()]
    expect["canonical_patch_dir"] = a.expect_canonical_dir
    expect["git_repo"] = a.git_repo
    expect["manifest_sha256"] = a.expect_manifest_sha256
    expect["base_repo"] = a.expect_base_repo

    evidence_sha = a.rca_evidence_sha
    if a.expect_evidence_sha and evidence_sha != a.expect_evidence_sha:
        failures.append(f"--rca-evidence-sha {evidence_sha} != frozen R2 evidence "
                        f"commit {a.expect_evidence_sha} (fail closed)")
        print(render_report("L02", "cli-pin-mismatch"))
        sys.exit(1)

    rca_root = os.path.abspath(a.rca_root)
    if a.apply:
        sys.exit(apply_manifest(a.apply[0], a.apply[1], rca_root, evidence_sha, expect))
    if a.check_only:
        sys.exit(check_only(a.check_only, rca_root, evidence_sha, expect, a.json_out))
    ap.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
