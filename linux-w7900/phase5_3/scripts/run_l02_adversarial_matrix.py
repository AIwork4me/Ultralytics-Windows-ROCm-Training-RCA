#!/usr/bin/env python3
"""Phase 5.3 Gate L02 adversarial matrix for check_final_handoff_r2.py.

16 check-only/apply tests. Each negative test must FAIL for the INTENDED
reason (asserted via expected failure-message substring), not due to a
missing dependency or an unrelated crash. Uses disposable scratch clones
under /tmp; never touches the frozen checkout.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

WS = "/workspace/miopen-w7900-validation"
FROZEN = f"{WS}/repos/rca-evidence"
CONSUMER = f"{WS}/phase5_3/scripts/check_final_handoff_r2.py"
PIN = "c8417161125dc33275b7ac615298b449a81e7cf8"
MANIFEST_REL = "findings/phase5_1_r2/FINAL_HANDOFF.json"
SCRATCH = tempfile.mkdtemp(prefix="p53adv-", dir="/tmp")
results = []


def run_consumer(rca_root, evidence_sha, expect_evidence=None, apply=None,
                 extra=None):
    cmd = [sys.executable, CONSUMER]
    if apply:
        cmd += ["--apply", apply[0], apply[1]]
    else:
        cmd += ["--check-only", os.path.join(rca_root, MANIFEST_REL)]
    cmd += ["--rca-root", rca_root, "--rca-evidence-sha", evidence_sha,
            "--expect-evidence-sha", expect_evidence if expect_evidence is not None else PIN]
    if extra:
        cmd += extra
    env = dict(os.environ, ALLOW_EXPECT_OVERRIDE="1")
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    try:
        report = json.loads(r.stdout)
    except Exception:
        report = {"verdict": "CRASH", "failures": [r.stderr[-400:]]}
    return r.returncode, report


def scratch_clone(name):
    d = os.path.join(SCRATCH, name)
    subprocess.run(["git", "clone", "-q", "--no-hardlinks", FROZEN, d], check=True)
    subprocess.run(["git", "-C", d, "checkout", "-q", PIN], check=True)
    return d


def commit_all(d, msg):
    subprocess.run(["git", "-C", d, "add", "-A"], check=True)
    subprocess.run(["git", "-C", d, "-c", "user.name=adv", "-c",
                    "user.email=adv@test", "commit", "-qm", msg], check=True)
    return subprocess.run(["git", "-C", d, "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def load_manifest(d):
    return json.load(open(os.path.join(d, MANIFEST_REL)))


def save_manifest(d, m):
    with open(os.path.join(d, MANIFEST_REL), "w") as f:
        json.dump(m, f, indent=2)


def record(idx, name, rc, report, expected_verdict, intended_reason, evidence_path=None):
    intended_hit = any(intended_reason in f for f in report.get("failures", []))
    ok = (report.get("verdict") == expected_verdict
          and (expected_verdict == "PASS" or intended_hit)
          and (expected_verdict != "PASS" or rc == 0)
          and (expected_verdict == "PASS" or rc != 0))
    results.append({
        "id": idx, "attack": name,
        "expected": expected_verdict,
        "actual_verdict": report.get("verdict"),
        "exit_code": rc,
        "intended_reason": intended_reason,
        "intended_reason_hit": intended_hit,
        "failures_observed": report.get("failures", [])[:6],
        "PASS": ok,
        "evidence_path": evidence_path,
    })
    print(f"[{'OK ' if ok else 'BAD'}] {idx}: {name} -> {report.get('verdict')} "
          f"(exit {rc}) intended_reason_hit={intended_hit}")
    return ok


def main():
    all_ok = True

    # ---- 1: correct R2 manifest -> PASS --------------------------------
    rc, rep = run_consumer(FROZEN, PIN)
    all_ok &= record(1, "correct R2 manifest", rc, rep, "PASS",
                     "no failure", f"{WS}/phase5_3/evidence/L02_positive_control.json")
    json.dump(rep, open(f"{WS}/phase5_3/evidence/L02_positive_control.json", "w"), indent=2)

    # ---- 2: R1 candidate manifest -> FAIL ------------------------------
    d = scratch_clone("r1cand")
    m = load_manifest(d)
    m["candidate_id"] = "P5.1-CANDIDATE-R1"
    save_manifest(d, m)
    sha = commit_all(d, "adv: r1 candidate")
    rc, rep = run_consumer(d, sha, expect_evidence="")
    all_ok &= record(2, "R1 candidate", rc, rep, "FAIL", "superseded candidate rejected")

    # ---- 2b: actual frozen R1 manifest -> FAIL --------------------------
    d2 = scratch_clone("r1manifest")
    subprocess.run(["git", "-C", d2, "checkout", "-q",
                    "494907699f3b57095663f0a70b42278001a8efb7",
                    "findings/phase5_1/FINAL_HANDOFF.json"], check=False)
    r1m = os.path.join(d2, "findings/phase5_1/FINAL_HANDOFF.json")
    if os.path.exists(r1m):
        cmd = [sys.executable, CONSUMER, "--check-only", r1m,
               "--rca-root", d2, "--rca-evidence-sha", PIN]
        r = subprocess.run(cmd, capture_output=True, text=True)
        try:
            rep2 = json.loads(r.stdout)
        except Exception:
            rep2 = {"verdict": "CRASH", "failures": []}
        intended = "manifest sha256"  # frozen R2 manifest pin rejects R1 bytes
        all_ok &= record("2b", "actual frozen R1 manifest", r.returncode, rep2,
                         "FAIL", intended)

    # ---- 3: wrong evidence commit -> FAIL ------------------------------
    d = scratch_clone("wrongev")
    rc, rep = run_consumer(d, "cd9c36c52a7702eef4a2b4ba899a4e35dfba8b1a",
                           expect_evidence="")
    all_ok &= record(3, "wrong evidence commit (ancestor snapshot)", rc, rep,
                     "FAIL", "evidence SHA mismatch")

    # ---- 3b: stale evidence pin via expect-override -> FAIL -------------
    rc, rep = run_consumer(FROZEN, "cd9c36c52a7702eef4a2b4ba899a4e35dfba8b1a",
                           expect_evidence="")
    all_ok &= record("3b", "ancestor snapshot pin (checkout mismatch)", rc, rep,
                     "FAIL", "evidence SHA mismatch")

    # ---- 4: wrong base -> FAIL ------------------------------------------
    d = scratch_clone("wrongbase")
    m = load_manifest(d)
    m["base_sha"] = "b68f8944300f104875d953fc8e4510908c9aaf0b"
    save_manifest(d, m)
    sha = commit_all(d, "adv: wrong base")
    rc, rep = run_consumer(d, sha, expect_evidence="")
    all_ok &= record(4, "wrong base_sha", rc, rep, "FAIL",
                     "known-stale historical anchor")

    # ---- 5: wrong source tree -> FAIL ------------------------------------
    d = scratch_clone("wrongtree")
    m = load_manifest(d)
    m["source_tree_identity"]["head_tree_sha1"] = "605d0d214acdbc06086fdb27c61fec970c0f2798"
    save_manifest(d, m)
    sha = commit_all(d, "adv: wrong tree")
    rc, rep = run_consumer(d, sha, expect_evidence="")
    all_ok &= record(5, "wrong head_tree (R1 tree)", rc, rep, "FAIL",
                     "superseded R1 tree")

    # ---- 6/7/8: patch tampering -> FAIL ----------------------------------
    for i, pname in enumerate(
            ["0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch",
             "0002-MIOpen-make-remaining-RTC-kernel-std-includes-self-c.patch",
             "0003-MIOpen-add-portable-HIPRTC-no-host-STL-regression-te.patch"], 1):
        d = scratch_clone(f"tamper{i}")
        p = os.path.join(d, "patches/phase5_1_r2/canonical", pname)
        raw = open(p, "rb").read()
        open(p, "wb").write(raw + b"\n# adversarial trailing byte\n")
        sha = commit_all(d, f"adv: tamper {i}")
        rc, rep = run_consumer(d, sha, expect_evidence="")
        all_ok &= record(5 + i, f"patch 000{i} tampering", rc, rep, "FAIL",
                         "sha256 mismatch")

    # ---- 9: wrong patch order -> FAIL -------------------------------------
    d = scratch_clone("order")
    m = load_manifest(d)
    m["ordered_patches"] = [m["ordered_patches"][1], m["ordered_patches"][0],
                            m["ordered_patches"][2]]
    for k, e in enumerate(m["ordered_patches"], 1):
        e["order"] = k
    save_manifest(d, m)
    sha = commit_all(d, "adv: reorder")
    rc, rep = run_consumer(d, sha, expect_evidence="")
    all_ok &= record(9, "wrong patch order", rc, rep, "FAIL",
                     "series hash mismatch")

    # ---- 10: wrong series hash -> FAIL -------------------------------------
    d = scratch_clone("series")
    m = load_manifest(d)
    m["series_hash"]["sha256"] = "797a69b5ae86d0e304b2258b5f5323cc97241a413d2c43134bf01703f7842f6d"
    save_manifest(d, m)
    sha = commit_all(d, "adv: r1 series")
    rc, rep = run_consumer(d, sha, expect_evidence="")
    all_ok &= record(10, "R1 series hash substitution", rc, rep, "FAIL",
                     "superseded R1 series")

    # ---- 11: extra .patch -> FAIL -------------------------------------------
    d = scratch_clone("extra")
    open(os.path.join(d, "patches/phase5_1_r2/canonical",
                      "9999-rogue.patch"), "w").write("rogue\n")
    sha = commit_all(d, "adv: extra patch")
    rc, rep = run_consumer(d, sha, expect_evidence="")
    all_ok &= record(11, "extra undeclared .patch", rc, rep, "FAIL",
                     "unexpected file in canonical patch dir")

    # ---- 12: missing patch -> FAIL --------------------------------------------
    d = scratch_clone("missing")
    os.unlink(os.path.join(d, "patches/phase5_1_r2/canonical",
                           "0003-MIOpen-add-portable-HIPRTC-no-host-STL-regression-te.patch"))
    sha = commit_all(d, "adv: missing patch")
    rc, rep = run_consumer(d, sha, expect_evidence="")
    all_ok &= record(12, "missing declared patch", rc, rep, "FAIL",
                     "declared file missing")

    # ---- 13: symlink substitution -> FAIL --------------------------------------
    d = scratch_clone("symlink")
    p = os.path.join(d, "patches/phase5_1_r2/canonical",
                     "0001-MIOpen-keep-RTC-type-traits-self-contained-when-no-h.patch")
    real = os.path.join(d, "rogue_real.patch")
    shutil.copy(p, real)
    os.unlink(p)
    os.symlink(os.path.join("..", "..", "..", "rogue_real.patch"), p)
    sha = commit_all(d, "adv: symlink")
    rc, rep = run_consumer(d, sha, expect_evidence="")
    all_ok &= record(13, "symlink patch substitution", rc, rep, "FAIL",
                     "symlink")

    # ---- 14: ../ traversal in manifest path -> FAIL ------------------------------
    d = scratch_clone("traversal")
    m = load_manifest(d)
    m["ordered_patches"][0]["path"] = "../phase5_1/canonical/0001-x.patch"
    save_manifest(d, m)
    sha = commit_all(d, "adv: traversal")
    rc, rep = run_consumer(d, sha, expect_evidence="")
    all_ok &= record(14, "../ path traversal", rc, rep, "FAIL",
                     "traversal")

    # ---- 15: incorrect manifest schema -> FAIL ------------------------------------
    d = scratch_clone("schema")
    m = load_manifest(d)
    m["upstream_base_sha"] = m.pop("base_sha")
    m["patch_series"] = [p["path"] for p in m.pop("ordered_patches")]
    m["series_sha256_mode"] = "concat"
    m["rca_evidence_commit"] = PIN
    save_manifest(d, m)
    sha = commit_all(d, "adv: old schema")
    rc, rep = run_consumer(d, sha, expect_evidence="")
    all_ok &= record(15, "provisional/old schema manifest", rc, rep, "FAIL",
                     "provisional/stale schema key present")

    # ---- 16: apply without authorization -> REFUSED -------------------------------
    target = os.path.join(SCRATCH, "applytarget")
    env_backup = os.environ.pop("ENABLE_APPLY", None)
    cmd = [sys.executable, CONSUMER, "--apply",
           os.path.join(FROZEN, MANIFEST_REL), target,
           "--rca-root", FROZEN, "--rca-evidence-sha", PIN]
    r = subprocess.run(cmd, capture_output=True, text=True)
    refused = ("REFUSED" in r.stderr or "authorization" in r.stderr.lower())
    results.append({
        "id": 16, "attack": "--apply without ENABLE_APPLY",
        "expected": "REFUSED", "actual_verdict": "REFUSED" if refused and r.returncode == 2 else f"exit={r.returncode}",
        "exit_code": r.returncode, "intended_reason": "refusal message + exit 2",
        "intended_reason_hit": refused and r.returncode == 2,
        "failures_observed": [r.stderr.strip()[:200]],
        "PASS": refused and r.returncode == 2 and not os.path.exists(target),
        "evidence_path": None,
    })
    all_ok &= results[-1]["PASS"]
    print(f"[{'OK ' if results[-1]['PASS'] else 'BAD'}] 16: apply w/o authorization -> exit {r.returncode} refused={refused}")
    if env_backup is not None:
        os.environ["ENABLE_APPLY"] = env_backup

    # ---- 16b: apply WITH authorization, into workspace (full checkout needs
    # ~2.5GB; /tmp tmpfs is too small) -> reconstruct OK ------------------------
    apply_target = f"{WS}/build/recon53/applytest"
    if os.path.exists(apply_target):
        shutil.rmtree(apply_target)
    rc, rep = run_consumer(FROZEN, PIN, apply=(os.path.join(FROZEN, MANIFEST_REL),
                                               apply_target))
    # HEAD stays at the base commit by design; the patched identity is the
    # INDEX tree (git add -A + write-tree), exactly what the consumer verifies.
    idx_tree = subprocess.run(["git", "-C", apply_target, "write-tree"],
                              capture_output=True, text=True).stdout.strip()
    ok = rc == 0 and idx_tree == "b983caddf9f9f561e7d1b590deadb16267c2de15"
    subprocess.run(["git", "-C", WS + "/repos/rocm-libraries", "worktree",
                    "remove", "--force", apply_target], capture_output=True)
    results.append({
        "id": "16b", "attack": "--apply WITH ENABLE_APPLY (authorized positive)",
        "expected": "RECONSTRUCTION_OK + tree b983cadd", "actual_verdict": f"exit={rc}",
        "exit_code": rc, "intended_reason": "tree b983cadd verified",
        "intended_reason_hit": ok, "failures_observed": [],
        "PASS": ok, "evidence_path": None,
    })
    all_ok &= ok
    print(f"[{'OK ' if ok else 'BAD'}] 16b: authorized apply -> exit {rc}")

    # ---- 17 (M2 regression): patch entry missing sha256 key -> clean FAIL ----
    d = scratch_clone("misskey")
    m = load_manifest(d)
    del m["ordered_patches"][0]["sha256"]
    save_manifest(d, m)
    sha = commit_all(d, "adv: missing sha256 key")
    rc, rep = run_consumer(d, sha, expect_evidence="")
    all_ok &= record(17, "ordered_patches entry missing sha256 key", rc, rep,
                     "FAIL", "missing key: sha256")

    out = f"{WS}/phase5_3/evidence/L02_adversarial_handoff_matrix.json"
    json.dump({"gate": "L02", "consumer": CONSUMER,
               "frozen_checkout": FROZEN, "pinned_evidence": PIN,
               "scratch_root": SCRATCH,
               "summary": {"total": len(results),
                           "passed": sum(1 for r in results if r["PASS"])},
               "results": results}, open(out, "w"), indent=2)
    print(f"\nmatrix: {sum(1 for r in results if r['PASS'])}/{len(results)} OK -> {out}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
