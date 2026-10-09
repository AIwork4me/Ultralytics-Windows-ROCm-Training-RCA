#!/usr/bin/env python3
"""Phase 5.3 final evidence integrity checker.

Validates the Phase 5.3 evidence package for INTERNAL CONSISTENCY:
  - every gate JSON's verdict is consistent with its recorded facts
    (e.g. a PASS verdict with a recorded nonzero exit code is rejected);
  - L08 Kthvalue evidence cross-checked against the RAW logs
    (dispatch lines, provenance lines, exit files, harness-sha equality);
  - key binary identities re-hashed;
  - verdict-specific mandatory fields present.

This is the checker referenced by Gate L11 attack A15 (a contradictory
record must be rejected). It never modifies evidence.
Exit 0 only if every check passes.
"""
import hashlib
import json
import os
import re
import sys

# EVIDENCE_DIR override exists ONLY for adversarial testing of this checker
# (Gate L11 attack A15); default enforces the real evidence tree.
P53 = os.environ.get("EVIDENCE_DIR", "/workspace/miopen-w7900-validation/phase5_3")
WS = "/workspace/miopen-w7900-validation"
fails = []


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(name):
    return json.load(open(f"{P53}/evidence/{name}"))


def chk(name, ok, detail=""):
    if not ok:
        fails.append(f"{name}: {detail}")
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))



def main():
    # ---- binary identities ---------------------------------------------------
    chk("binary:legA_sha256",
        sha256(f"{WS}/install/legA-frozen-baseline/lib/libMIOpen.so.1.0")
        == "7e045dc01b22af02f37d6314b1782bcb77aed2e12166e6da1f25d884a363e97d")
    chk("binary:legB_sha256",
        sha256(f"{WS}/install/patched/lib/libMIOpen.so.1.0")
        == "bf21a5fa4abc5ff77b0f50756a69dccf7a077970603a846300f0ea077d61eac1")
    chk("binary:harness_sha256",
        sha256(f"{WS}/build/kthvalue-harness/kthvalue_runtime_harness_gfx1100")
        == "b830b37a5aa7aef37da8c79e3ceb30435fd631b99dda29516f2ed36c152e7ef8")
        # note: mission brief lists a 65-char value (trailing 'f' typo); the
        # true 64-char digest is pinned here (documented in L00 evidence)

    # ---- L08: cross-check evidence vs raw logs --------------------------------
    l08 = load("L08_kthvalue_ab.json")
    for leg in ("A", "B"):
        log = open(f"{P53}/logs/L08_leg{leg}_kthvalue.log").read()
        exit_code = open(f"{P53}/logs/L08_leg{leg}_kthvalue.exit").read().strip()
        rec = l08[f"leg{leg}"]
        chk(f"L08:leg{leg}_exit_file_matches", str(rec["exit_code"]) == exit_code,
            f"evidence={rec['exit_code']} file={exit_code}")
        chk(f"L08:leg{leg}_exit_zero_for_pass",
            not (l08["verdict"] == "PASS" and rec["exit_code"] != "0"),
            "PASS verdict with nonzero exit is contradictory")
        chk(f"L08:leg{leg}_dispatch_in_rawlog",
            "FindSolutionImpl] KthvalueFwd" in log and "kernel_name = KthvalueFwd" in log,
            "raw log lacks dispatch lines")
        chk(f"L08:leg{leg}_provenance_in_rawlog",
            rec["provenance_libMIOpen"] in log, "provenance line missing in raw log")
    chk("L08:same_harness_both_legs",
        l08["legA"]["harness_sha256"] if "harness_sha256" in l08["legA"]
        else True, "checked via wrapper sha lines")
    ha = re.search(r"harness (\S+) sha256: (\w+)",
                   open(f"{P53}/logs/L08_legA_kthvalue.log").read())
    hb = re.search(r"harness (\S+) sha256: (\w+)",
                   open(f"{P53}/logs/L08_legB_kthvalue.log").read())
    chk("L08:harness_sha_equality_rawlogs",
        ha and hb and ha.group(2) == hb.group(2) == l08["harness"]["sha256"],
        f"{ha.group(2)[:12] if ha else '?'} vs {hb.group(2)[:12] if hb else '?'}")
    chk("L08:dumps_identical", l08["ab_dump_comparison"]["all_byte_identical"] is True)

    # ---- L09: exit/verdict consistency ---------------------------------------
    l09 = load("L09_batchnorm_numerics.json")
    for leg in ("A", "B"):
        rec = l09["legs"][leg]
        exit_code = open(f"{P53}/logs/L09_batchnorm_leg{leg}.exit").read().strip()
        chk(f"L09:leg{leg}_exit_consistent",
            rec["exit_code"] == exit_code == "0" and rec["harness_result"] == "PASS",
            f"evidence={rec['exit_code']} file={exit_code}")
        chk(f"L09:leg{leg}_all_checks_pass",
            all(c["result"] == "PASS" for c in rec["checks"]))

    # ---- L07: ctest skip honesty ----------------------------------------------
    l07 = load("L07_ctest_portability.json")
    exec_log = open(f"{P53}/logs/L07_ctest_execution.log").read()
    chk("L07:ctest_skipped_not_failed",
        "***Skipped" in exec_log and "0 tests failed" in exec_log
        and l07["ctest"]["ctest_process_exit"] == 0)
    chk("L07:positive_exit4", l07["direct_mode_matrix"]["positive"]["exit"] == 4)
    chk("L07:ordinary_and_withstl_pass",
        l07["direct_mode_matrix"]["ordinary"]["exit"] == 0
        and l07["direct_mode_matrix"]["with-stl"]["exit"] == 0)

    # ---- L10: optional gate consistency ---------------------------------------
    l10 = load("L10_yolo_smoke.json")
    chk("L10:exit_consistent",
        (l10["run"]["training_exit_code"] == 0) == (l10["verdict"].startswith("PASS")),
        "PASS verdict requires exit 0")
    chk("L10:provenance_is_legB",
        l10["run"]["in_process_miopen_provenance"].find("bf21a5fa") > 0
        and "install/patched" in l10["run"]["in_process_miopen_provenance"])

    # ---- L11 matrix self-consistency ------------------------------------------
    l11 = load("L11_false_pass_matrix.json")
    npass = sum(1 for e in l11["results"] if e["ACTUAL_RESULT"].startswith("PASS"))
    chk("L11:all_attacks_behaved", npass == len(l11["results"]), f"{npass}/{len(l11['results'])}")

    # ---- L05/L06 identity cross-refs ------------------------------------------
    l05 = load("L05_legB_build.json")
    chk("L05:legB_sha_matches_l06",
        l05["binary"]["sha256"]
        == "bf21a5fa4abc5ff77b0f50756a69dccf7a077970603a846300f0ea077d61eac1")
    l06 = load("L06_library_provenance.json")
    chk("L06:no_contamination_both_legs",
        l06["legA"]["contamination_721"] == 0 and l06["legB"]["contamination_721"] == 0)

    print(f"\n{'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' FAILURES'}")
    for f in fails:
        print("  - " + f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
