#!/usr/bin/env python3
"""Adversarial attack matrix for check_final_handoff.py (Gates B03 + B10).

Every attack runs against an INDEPENDENT THROWAWAY COPY of the frozen
evidence (fresh git repo committed in a temp dir); the frozen pinned
checkout is never modified. Each attack records:
    attack_id, mutation, expected_verdict, observed_verdict, exit_code,
    evidence_path, intended_reason, observed_reasons

A negative test only counts as a valid FAIL if the observed failures
contain the INTENDED reason (a rejection for an unrelated reason — e.g.
a missing dependency — is not a valid PASS of the attack).
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

WS = "/workspace/miopen-w7900-validation"
SCRIPT = os.path.join(WS, "phase5_2", "scripts", "check_final_handoff.py")
PINNED = os.path.join(WS, "repos", "rca-evidence")
REAL_GIT_REPO = os.path.join(WS, "repos", "rocm-libraries")
MANIFEST_REL = "findings/phase5_1/FINAL_HANDOFF.json"
CANON_REL = "patches/phase5_1/canonical"
EVID_OUT = os.path.join(WS, "phase5_2", "evidence", "adversarial_matrix.json")
FROZEN_EVIDENCE_SHA = "494907699f3b57095663f0a70b42278001a8efb7"

ATTACKS = []


def attack(attack_id, mutation, expected, intended_reason):
    def deco(fn):
        ATTACKS.append((attack_id, mutation, expected, intended_reason, fn))
        return fn
    return deco


def make_copy(root):
    """Throwaway copy of the frozen evidence tree + fresh git commit."""
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    for rel in (MANIFEST_REL,
                f"{CANON_REL}/0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch",
                f"{CANON_REL}/0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch",
                f"{CANON_REL}/0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch",
                f"{CANON_REL}/README.md"):
        dst = os.path.join(root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(PINNED, rel), dst)
    def g(*a):
        return subprocess.run(["git", "-C", root] + list(a),
                              capture_output=True, text=True)
    g("init", "-q")
    g("config", "user.email", "adv@test.local")
    g("config", "user.name", "adv")
    g("add", "-A")
    g("commit", "-qm", "adv-copy")
    r = g("rev-parse", "HEAD")
    return r.stdout.strip()


def load_manifest(root):
    with open(os.path.join(root, MANIFEST_REL)) as f:
        return json.load(f)


def save_manifest(root, m):
    with open(os.path.join(root, MANIFEST_REL), "w") as f:
        json.dump(m, f, indent=2)


def recommit(root):
    def g(*a):
        return subprocess.run(["git", "-C", root] + list(a),
                              capture_output=True, text=True)
    g("add", "-A")
    g("commit", "-qm", "adv-mutation")
    return g("rev-parse", "HEAD").stdout.strip()


def run_check(root, head, workdir, extra_args=(), git_repo=REAL_GIT_REPO,
              evidence_sha=None, expect_evidence_sha=True):
    evidence_sha = evidence_sha or head
    out = os.path.join(workdir, "result.json")
    if os.path.isfile(out):
        os.remove(out)
    cmd = [sys.executable, SCRIPT,
           "--check-only", os.path.join(root, MANIFEST_REL),
           "--rca-root", root,
           "--rca-evidence-sha", evidence_sha,
           "--git-repo", git_repo,
           "--json-out", out]
    if expect_evidence_sha:
        cmd += ["--expect-evidence-sha", evidence_sha]
    cmd += list(extra_args)
    p = subprocess.run(cmd, capture_output=True, text=True)
    rep = {}
    if os.path.isfile(out):
        rep = json.load(open(out))
    rep["consumer_exit_code"] = p.returncode
    return p.returncode, rep


# ---------------------------------------------------------------- attacks --
@attack("A", "unmodified manifest + correct patches (control)", "PASS", None)
def a(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    rc, rep = run_check(root, head, workdir)
    return rc == 0 and rep.get("verdict") == "PASS", rep


@attack("B", "flip one byte in patch 0001", "FAIL",
        "sha256 mismatch")
def b(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    p1 = os.path.join(root, CANON_REL,
                      "0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch")
    data = bytearray(open(p1, "rb").read())
    data[100] ^= 0x01
    open(p1, "wb").write(bytes(data))
    # NOTE: byte flipped on disk only; manifest untouched -> sha mismatch AND
    # dirty-tree/blob mismatch are BOTH intended consequences of tampering
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and ("sha256 mismatch" in reasons or
                        "differs from pinned git blob" in reasons), rep


@attack("C", "flip one byte in patch 0002", "FAIL",
        "sha256 mismatch")
def c(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    p = os.path.join(root, CANON_REL,
                     "0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch")
    data = bytearray(open(p, "rb").read())
    data[50] ^= 0x01
    open(p, "wb").write(bytes(data))
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and ("sha256 mismatch" in reasons or
                        "differs from pinned git blob" in reasons), rep


@attack("D", "flip one byte in patch 0003", "FAIL",
        "sha256 mismatch")
def d(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    p = os.path.join(root, CANON_REL,
                     "0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch")
    data = bytearray(open(p, "rb").read())
    data[50] ^= 0x01
    open(p, "wb").write(bytes(data))
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and ("sha256 mismatch" in reasons or
                        "differs from pinned git blob" in reasons), rep


@attack("E", "reverse patch order in manifest", "FAIL",
        "series hash mismatch")
def e(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    m = load_manifest(root)
    for entry in m["ordered_patches"]:
        entry["order"] = 4 - entry["order"]
    save_manifest(root, m)
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "series hash mismatch" in reasons, rep


@attack("F", "duplicate patch order in manifest", "FAIL",
        "not contiguous")
def f(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    m = load_manifest(root)
    m["ordered_patches"][1]["order"] = 1
    save_manifest(root, m)
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and ("not contiguous" in reasons or
                        "not unique" in reasons), rep


@attack("G", "inject 0004-malicious.patch into canonical dir", "FAIL",
        "unexpected file in canonical patch dir")
def g(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    open(os.path.join(root, CANON_REL, "0004-malicious.patch"), "w").write(
        "From 0000000000000000000000000000000000000000 Mon Sep 17 00:00:00 2001\n"
        "From: Evil <evil@evil>\nSubject: [PATCH 4/4] exfiltrate\n\n---\n")
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "unexpected file in canonical patch dir" in reasons, rep


@attack("H", "replace patch 0001 with a symlink to original", "FAIL",
        "symlink")
def h(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    p1 = os.path.join(root, CANON_REL,
                      "0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch")
    real = os.path.join(PINNED, CANON_REL,
                        "0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch")
    os.remove(p1)
    os.symlink(real, p1)
    head = recommit(root)  # git stores symlink target, not content
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "symlink" in reasons, rep


@attack("I", "manifest patch path with ../ traversal", "FAIL",
        "traversal")
def i(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    m = load_manifest(root)
    m["ordered_patches"][0]["path"] = (
        "../../patches/phase5_1/canonical/"
        "0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch")
    save_manifest(root, m)
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "traversal" in reasons, rep


@attack("J", "manifest patch path absolute", "FAIL",
        "absolute")
def j(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    m = load_manifest(root)
    m["ordered_patches"][0]["path"] = (
        "/etc/passwd/0001-MIOpen-keep-RTC-type-traits-self-contained-"
        "when-no-h.patch")
    save_manifest(root, m)
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "absolute" in reasons, rep


@attack("K", "tamper series SHA256 in manifest", "FAIL",
        "series hash mismatch")
def k(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    m = load_manifest(root)
    m["series_hash"]["sha256"] = "0" * 64
    save_manifest(root, m)
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "series hash mismatch" in reasons, rep


@attack("L", "tamper frozen base SHA in manifest", "FAIL",
        "base_sha mismatch")
def l(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    m = load_manifest(root)
    m["base_sha"] = "b68f8944300f104875d953fc8e4510908c9aaf0b"
    save_manifest(root, m)
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and ("base_sha mismatch" in reasons or
                        "known-stale historical anchor" in reasons), rep


@attack("M", "tamper expected source tree SHA1 in manifest", "FAIL",
        "head_tree_sha1 mismatch")
def m_(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    man = load_manifest(root)
    man["source_tree_identity"]["head_tree_sha1"] = "1" * 40
    save_manifest(root, man)
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "head_tree_sha1 mismatch" in reasons, rep


@attack("N", "old Phase-5 provisional-schema manifest (P5 candidate)", "FAIL",
        "provisional")
def n(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    m = {
        "schema_version": 1,
        "candidate_id": "P5-CANDIDATE-R1",
        "upstream_base_sha": "7c5866144ac4b879be442563e2b49fa1c142ea36",
        "patch_series": [
            {"path": f"{CANON_REL}/0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch",
             "sha256": "14719b8b4ae7b4370afa42249b56c130d7d42b9447701e57a702570eb12ed7e2"},
            {"path": f"{CANON_REL}/0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch",
             "sha256": "7d40c314dcac87085178ba9d0c84bb2eced8f33ba8e9bd3a6151903d6ee4751e"},
            {"path": f"{CANON_REL}/0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch",
             "sha256": "3eb20ec0b4c38035438d317c210847e880ae8be5bf914617fb51f160f46670b4"},
        ],
        "series_sha256": "797a69b5ae86d0e304b2258b5f5323cc97241a413d2c43134bf01703f7842f6d",
        "series_sha256_mode": "concat_bytes",
        "rca_evidence_commit": "013f6f005f97aca5ef46d841ca754f2283dc62f0",
    }
    save_manifest(root, m)
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "provisional/stale schema key" in reasons, rep


@attack("O", "correct series + legitimate README.md present", "PASS", None)
def o(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)  # README.md included by make_copy
    rc, rep = run_check(root, head, workdir)
    readme_ok = any("README.md" in x for x in rep.get("notes", []))
    return rc == 0 and rep.get("verdict") == "PASS" and readme_ok, rep


@attack("P", "wrong candidate_id (P5) with otherwise valid manifest", "FAIL",
        "candidate_id mismatch")
def p(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    m = load_manifest(root)
    m["candidate_id"] = "P5-CANDIDATE-R1"
    save_manifest(root, m)
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "candidate_id mismatch" in reasons, rep


@attack("Q", "wrong evidence commit SHA passed via CLI", "FAIL",
        "evidence SHA mismatch")
def q(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    rc, rep = run_check(root, head, workdir,
                        evidence_sha="013f6f005f97aca5ef46d841ca754f2283dc62f0")
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "evidence SHA mismatch" in reasons, rep


@attack("R", "declared patch file missing from disk", "FAIL",
        "missing")
def r(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    os.remove(os.path.join(root, CANON_REL,
                           "0003-MIOpen-add-HIPRTC-no-host-STL-regression-test.patch"))
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "missing" in reasons, rep


@attack("S", "incomplete local git objects (no frozen base commit)", "FAIL",
        "not present in local git repo")
def s(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    empty_repo = os.path.join(workdir, "empty-repo")
    shutil.rmtree(empty_repo, ignore_errors=True)
    os.makedirs(empty_repo, exist_ok=True)
    subprocess.run(["git", "-C", empty_repo, "init", "-q"], check=True)
    rc, rep = run_check(root, head, workdir, git_repo=empty_repo)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "not present in local git repo" in reasons, rep, rc


@attack("T", "executable bit set on a canonical patch", "FAIL",
        "executable")
def t(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    p = os.path.join(root, CANON_REL,
                     "0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch")
    os.chmod(p, 0o755)
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "executable" in reasons, rep


@attack("U", "nested directory injected into canonical dir", "FAIL",
        "nested directory")
def u(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    os.makedirs(os.path.join(root, CANON_REL, "sneaky"))
    open(os.path.join(root, CANON_REL, "sneaky", "x.patch"), "w").write("x")
    head = recommit(root)
    rc, rep = run_check(root, head, workdir)
    reasons = " ".join(rep.get("failures", []))
    return rc != 0 and "nested directory" in reasons, rep


@attack("V", "--apply without ENABLE_APPLY=1 authorization", "REFUSED", None)
def v(workdir):
    root = os.path.join(workdir, "tree")
    head = make_copy(root)
    target = os.path.join(workdir, "apply-target")
    env = dict(os.environ)
    env.pop("ENABLE_APPLY", None)
    p = subprocess.run(
        [sys.executable, SCRIPT,
         "--apply", os.path.join(root, MANIFEST_REL), target,
         "--rca-root", root, "--rca-evidence-sha", head,
         "--expect-evidence-sha", head,
         "--git-repo", REAL_GIT_REPO],
        capture_output=True, text=True, env=env)
    refused = (p.returncode == 2 and
               "REFUSED" in (p.stderr + p.stdout))
    rep = {"verdict": "REFUSED" if refused else "UNEXPECTED",
           "failures": [p.stderr.strip()[-300:]], "exit_code": p.returncode}
    return refused, rep, p.returncode


def frozen_untouched():
    """Real verification (F4): pinned checkout clean + HEAD unchanged."""
    st = subprocess.run(["git", "-C", PINNED, "status", "--porcelain"],
                        capture_output=True, text=True)
    hd = subprocess.run(["git", "-C", PINNED, "rev-parse", "HEAD"],
                        capture_output=True, text=True)
    return (st.returncode == 0 and not st.stdout.strip() and
            hd.stdout.strip() == FROZEN_EVIDENCE_SHA)


def main():
    base_tmp = "/tmp/opencode/p52-adv"
    os.makedirs(base_tmp, exist_ok=True)
    records = []
    all_ok = True
    for attack_id, mutation, expected, intended_reason, fn in ATTACKS:
        workdir = os.path.join(base_tmp, attack_id)
        os.makedirs(workdir, exist_ok=True)
        res = fn(workdir)
        if expected == "REFUSED" or len(res) == 3:
            ok, rep, rc = res
        else:
            ok, rep = res
            rc = rep.get("consumer_exit_code")
        observed = rep.get("verdict", "?") if rep else "?"
        verdict_ok = (observed == expected) if expected != "REFUSED" else ok
        record = {
            "attack_id": attack_id,
            "mutation": mutation,
            "expected_verdict": expected,
            "observed_verdict": observed,
            "intended_reason": intended_reason,
            "observed_reasons": rep.get("failures", [])[:6] if rep else [],
            "reason_confirmed": bool(ok),
            "exit_code": rc,
            "evidence_path": os.path.join(workdir, "result.json"),
            "overall_ok": bool(verdict_ok and ok),
        }
        if not record["overall_ok"]:
            all_ok = False
        records.append(record)
        print(f"[{attack_id}] expected={expected} observed={observed} "
              f"reason_ok={record['reason_confirmed']} -> "
              f"{'OK' if record['overall_ok'] else 'INVALID'}")

    out = {
        "gate": "B03+B10 adversarial matrix",
        "tool": SCRIPT,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "frozen_evidence_untouched": frozen_untouched(),
        "all_attacks_behaved_as_expected": all_ok,
        "attacks": records,
    }
    with open(EVID_OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nALL_ATTACKS_OK={all_ok}")
    print(f"evidence: {EVID_OUT}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
