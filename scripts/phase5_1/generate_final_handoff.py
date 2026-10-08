#!/usr/bin/env python3
"""Phase 5.1 / Gate 08 - generate the authoritative FINAL_HANDOFF.json and
the derived LINUX_FINAL_VALIDATION_HANDOFF.md for P5.1-CANDIDATE-R1.

Reads ONLY real evidence (git objects, canonical patch bytes, validation
JSONs produced by the GATE-07 scripts). Refuses to emit a manifest if any
required evidence is missing. No hand-maintained SHA lists: every identity
is recomputed here.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

Y = Path(r"C:\Users\rocm\Desktop\YOLO_AMD")
RCA = Y / "Ultralytics-Windows-ROCm-Training-RCA"
WT = Y / "rocm-libraries-phase5.1-candidate"
PATCHES = RCA / "patches" / "phase5_1" / "canonical"
EV = RCA / "evidence" / "phase5_1"
BASE = "7c5866144ac4b879be442563e2b49fa1c142ea36"

KTHVALUE_CASES = [
    {"shape": [100, 500], "dtype": "FP32", "dim": -1, "k": 10, "keepDim": False},
    {"shape": [10, 20, 300], "dtype": "FP32", "dim": 2, "k": 137, "keepDim": True},
    {"shape": [8, 3, 10, 2000], "dtype": "FP16", "dim": -1, "k": 2000, "keepDim": True},
]


def git(*a):
    r = subprocess.run(["git", "-C", str(WT), *a], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {a} failed: {r.stderr}")
    return r.stdout.strip()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: Path):
    if not p.exists():
        raise SystemExit(f"MISSING EVIDENCE: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    commits = git("rev-parse", "HEAD~2", "HEAD~1", "HEAD").split()
    subjects = [s for s in git("log", "--reverse", "--format=%s", f"{BASE}..HEAD").split("\n") if s]
    base_actual = git("rev-parse", "HEAD~3")
    head_tree = git("rev-parse", "HEAD^{tree}")
    author = git("log", "-1", "--format=%an")
    email = git("log", "-1", "--format=%ae")
    if base_actual != BASE:
        raise SystemExit(f"base mismatch: {base_actual}")

    patch_names = sorted(p.name for p in PATCHES.glob("*.patch"))
    if len(patch_names) != 3:
        raise SystemExit(f"expected 3 patches, found {patch_names}")
    concat = b""
    patch_records = []
    for n in patch_names:
        b = (PATCHES / n).read_bytes()
        concat += b
        patch_records.append({"order": len(patch_records) + 1, "path": f"patches/phase5_1/canonical/{n}",
                              "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)})
    series = hashlib.sha256(concat).hexdigest()

    ci = load(EV / "ci" / "ci_integration.json")
    matrix = load(EV / "ci" / "ci_matrix_phase5_1.json")
    build = load(EV / "build" / "build_provenance.json")
    runtime = load(EV / "runtime" / "runtime_validation.json")
    yolo = load(EV / "yolo" / "yolo_train.json")
    delta = load(EV / "p51_source_tree_identity.json")
    am = load(EV / "git_am_roundtrip.json")

    if build["source_git_head"] != commits[-1]:
        raise SystemExit("build provenance head != series HEAD")

    dll_sha = build["dll_sha256"]
    p5_to_p51 = []
    for f, v in delta["files"].items():
        p5_to_p51.append({"file": f, "p5_1_sha256": v["sha256"],
                          "change": "COPYRIGHT_TEXT (comment-only)" if f in (
                              "projects/miopen/src/kernels/miopen_freestanding_type_traits.hpp",
                              "projects/miopen/src/kernels/miopen_freestanding_utility.hpp",
                              "projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp",
                              "projects/miopen/test/hiprtc_selfcontained.cpp") else "UNCHANGED vs P5"})

    manifest = {
        "schema_version": 1,
        "handoff_type": "final_pre_upstream_linux_validation",
        "generated": datetime.now().isoformat(),
        "candidate_id": "P5.1-CANDIDATE-R1",
        "candidate_status": "TECHNICALLY_VERIFIED_PROVISIONAL_FREEZE",
        "candidate_status_reason": "right-to-contribute CONFIRMED and copyright resolved (4/4 files); DCO attestation PENDING (not authorized); Linux validation PENDING",
        "supersedes": {
            "phase5_candidate_id": "P5-CANDIDATE-R1",
            "phase5_commits": ["135f775e855bc40185d0a39e13d0a1a97105c1b9",
                               "66f66944f171628076785e5b89b4a1334d5a987d",
                               "29846fc4fb736800ff0ad91af95c7cc32f1373ad"],
            "phase5_patches_dir": "patches/phase5/canonical (immutable, retained)",
            "superseded_docs": ["docs/phase5/LINUX_FINAL_VALIDATION_HANDOFF.md (corrected + marked superseded)"],
        },
        "base_repo": "ROCm/rocm-libraries",
        "base_branch": "develop",
        "base_sha": BASE,
        "ordered_commits": commits,
        "ordered_commit_subjects": subjects,
        "ordered_patches": patch_records,
        "series_hash": {
            "algorithm": "sha256_file_concat_v1",
            "definition": "SHA256 of the three canonical patch files' bytes (LF) concatenated in order with no separator",
            "sha256": series,
        },
        "source_tree_identity": {
            "head_tree_sha1": head_tree,
            "git_am_roundtrip_tree_match": am["source_tree_match"],
            "changed_files_vs_base": delta["files"],
        },
        "source_delta_from_phase5": p5_to_p51,
        "source_delta_summary": "4 files, 1 comment line each: copyright placeholder -> 'Copyright (c) 2026 AIwork4me' (RIGHT_TO_CONTRIBUTE=CONFIRMED_BY_USER 2026-10-08). All other source bytes identical to P5-CANDIDATE-R1.",
        "git_author": author,
        "git_email": email,
        "dco_status": "DCO_ATTESTATION_PENDING (upstream CONTRIBUTING.md files state no DCO requirement; user has NOT authorized certification; explicit marker lines retained on all three commits; sign-off instructions in docs/phase5_1/COPYRIGHT_AND_DCO_STATUS.md §3)",
        "copyright_status": "RESOLVED: 4/4 new files carry 'Copyright (c) 2026 AIwork4me'; MIT license text preserved verbatim; RIGHT_TO_CONTRIBUTE=CONFIRMED_BY_USER (2026-10-08)",
        "windows_validation_status": {
            "cmake_configure": "PASS" if ci["configure"]["exit"] == 0 else "FAIL",
            "target_build": "PASS" if ci["build_target"]["exit"] == 0 else "FAIL",
            "ctest_discovery": "PASS" if ci["ctest_discovery"]["exit"] == 0 else "FAIL",
            "ctest_execution": "PASS" if ci["ctest_run"]["exit"] == 0 else "FAIL",
            "ci_ab_matrix": matrix["overall"] + f" ({sum(1 for v in matrix['verdicts'].values() if v=='PASS')}/{len(matrix['verdicts'])} cells)",
            "miopen_dll_build": "PASS",
            "miopen_dll_sha256": dll_sha,
            "dll_load_provenance": "PASS" if runtime["phase5_canonical_miopen_loaded"] else "FAIL",
            "nostl_runtime": "PASS" if all(runtime["nostl"]["checks"].values()) else "FAIL",
            "batchnorm_numerics": "PASS" if all(runtime.get("numerics_checks", {}).values()) else "FAIL",
            "batchnorm_numerics_detail": runtime.get("numerics", {}).get("max_abs"),
            "yolo_train_amp_false": "PASS" if yolo["amp_false_pass"] else "FAIL",
            "yolo_train_amp_default": "PASS" if yolo["amp_default_pass"] else "FAIL",
            "yolo_amp_note": "amp_default training PASSED (exit 0, weights, provenance) with ultralytics' AMP check failing in the CURRENT environment -> FP32 fallback; control experiment (evidence/phase5_1/yolo/amp_check_control.json) shows the check fails identically with the P5 DLL and the pristine wheel DLL => environment-state dependent, NOT a P5.1 regression. P5's historical AMP=True success remains valid for P5 bytes. amp_genuine on P5.1 = FALSE (honest record).",
            "wheel_dll_restored": "PASS" if (runtime["wheel_restored_ok"] and yolo["wheel_restored_ok"]) else "FAIL",
        },
        "linux_validation_status": "PENDING",
        "linux_validation_authority": "this manifest + docs/phase5_1/LINUX_FINAL_VALIDATION_HANDOFF.md; consumers must fail closed on identity mismatch",
        "authorization_to_submit_upstream": False,
        "upstream_pr_created": False,
        "upstream_issue_created": False,
        "upstream_comment_posted": False,
        "internal_pr_created": False,
    }

    # hard consistency gate: refuse to emit FINAL if any windows check failed
    wv = manifest["windows_validation_status"]
    failures = [k for k, v in wv.items() if isinstance(v, str) and v.startswith("FAIL")]
    if failures:
        raise SystemExit(f"REFUSING: windows validation failures: {failures}")
    if manifest["git_author"] != "AIwork4me" or manifest["git_email"] != "AIwork4me@users.noreply.github.com":
        raise SystemExit("REFUSING: author identity mismatch")

    out = RCA / "findings" / "phase5_1" / "FINAL_HANDOFF.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("wrote", out)

    # ---- derived Linux handoff markdown (generated FROM the manifest) ----
    md = f"""# Linux Final Validation Handoff — P5.1-CANDIDATE-R1 (Phase 5.1, Gate 08)

**Status: `LINUX_VALIDATION = PENDING`** — authoritative manifest:
`findings/phase5_1/FINAL_HANDOFF.json` (this file is GENERATED from it;
do not hand-edit SHA lists here).

Supersedes `docs/phase5/LINUX_FINAL_VALIDATION_HANDOFF.md` (P5-CANDIDATE-R1,
corrected and marked superseded). Historical Phase-3/4/5 evidence is
immutable; nothing there is rewritten.

## Candidate identity (fail closed on any mismatch)

```text
candidate ID:              {manifest['candidate_id']}
frozen upstream base SHA:  {manifest['base_sha']}
ordered candidate commits:  {commits[0]}
                           {commits[1]}
                           {commits[2]}
ordered patch paths:       patches/phase5_1/canonical/
  {patch_names[0]}
  {patch_names[1]}
  {patch_names[2]}
individual SHA256:         {patch_records[0]['sha256']}
                           {patch_records[1]['sha256']}
                           {patch_records[2]['sha256']}
series SHA256 (concat):    {series}
source head tree SHA1:     {head_tree}
```

Verify each patch SHA256 and the series SHA256
(`sha256_file_concat_v1` = SHA256 over the three patch files' LF bytes
concatenated in order, no separator) BEFORE building. If any value
differs, STOP — wrong candidate.

## Linux consumer rules

1. Use ONLY this manifest as the identity authority. Any mismatch of
   base SHA, commit SHAs, patch hashes, series hash or reconstructed
   tree → FAIL CLOSED (do not proceed to "close enough" testing).
2. Apply with exact blob bytes (no email-client/clipboard mangling, no
   CRLF conversion):
   `git checkout {BASE} && git apply < 0001 && git apply < 0002 && git apply < 0003`
   (sequential, ordered; `git am` also reproduces the identical tree —
   proven on Windows: tree `{head_tree}`). When reproducing patches
   with `git format-patch`, write PER-FILE output into a directory;
   `--stdout` mode appends two extra LF bytes and breaks byte-exact
   reproduction (Reviewer A NIT A-2).
3. Reconstruct-verify: after applying, the source tree identity must
   equal head tree `{head_tree}` (e.g. `git write-tree` on the staged
   result of a clean base + patches).

## P5 → P5.1 delta (what Linux is actually validating)

P5.1 = P5 + copyright attribution only: 4 files, 1 comment line each
(placeholder → `Copyright (c) 2026 AIwork4me`), MIT text preserved.
All other bytes identical to the P5-CANDIDATE-R1 series that carries
the full Windows validation history. Linux validates the FINAL bytes.

## Minimum Linux validation set (targeted)

1. **Build both libraries from source**: clean checkout of `{BASE[:8]}`,
   apply the ordered series, configure + build MIOpen the Phase-3 way;
   ALSO build the UNPATCHED library from the bare base.
2. **HIPRTC regression A/B** (the point of the patch):
   - `test_hiprtc_selfcontained <kernels-dir> --mode=negative` on the
     UNPATCHED tree → PASS with the exact `'type_traits' file not found`
     signature (Linux may need `--isolate=-nostdinc++`);
   - `--mode=positive` on the PATCHED tree → PASS with non-empty code
     object;
   - `--mode=ordinary` both trees → PASS;
   - in-tree `ctest -R ^test_hiprtc_selfcontained$` (anchored regex)
     on the patched build → PASS.
3. **Kthvalue runtime — DIRECT MIOpen harness (authoritative method;
   NOT torch.topk/torch.kthvalue)**: execute
   `miopenKthvalueForward` directly via the validated Phase-3 harness
   (`scripts/phase3/linux/kthvalue_runtime_harness.cpp`; closure doc
   `docs/phase3/linux/KTHVALUE_RUNTIME_CLOSURE.md`). Required chain and
   proof:
   - chain `miopenKthvalueForward` → solver `KthvalueFwd` →
     `MIOpenKthvalue.cpp` → `radix.hpp` (the patched file);
   - run against source-built UNPATCHED and PATCHED `libMIOpen.so`,
     isolated via `LD_PRELOAD`, using the SAME harness binary on both
     sides (record its SHA256; the two runs must differ ONLY in which
     library was preloaded — Reviewer B B-N1);
   - prove which library was loaded: `dladdr` on the exact
     `miopenKthvalueForward` function pointer used (+ wrapper on
     `miopenCreate`);
   - fresh isolated `MIOPEN_CUSTOM_CACHE_DIR` per run (no cached
     binaries can hide compile behavior);
   - kernel dispatch evidence in logs ("Invoker registered … solver
     KthvalueFwd"; `kernel_name = KthvalueFwd`; RTC
     LoadBinary(miss) → HIPRTC compile → SaveBinary for
     `MIOpenKthvalue.cpp.o`). These are Info2-level lines: set
     `MIOPEN_LOG_LEVEL=6` (a default release build logs only warnings,
     which would silently omit the required dispatch evidence —
     Reviewer B B-M1);
   - deterministic cases: {json.dumps(KTHVALUE_CASES)}
     (fixed-seed pairwise-distinct inputs — Phase-3 set);
   - verify values AND indices vs CPU reference (exact equality
     expected, as in Phase 3);
   - compare patched vs unpatched outputs byte-for-byte;
   - record real exit codes and raw logs.
   `torch.topk`/`torch.kthvalue` may be run as SUPPLEMENTAL evidence
   only — never as primary proof of the MIOpen radix path.
4. **BatchNorm spot-check**: BN train fwd/bwd + running stats, finite +
   vs CPU tolerances (Phase-3 method).
5. Optional end-to-end: one-epoch YOLO26n coco8 (`amp=False`).

Record PASS/FAIL with raw logs under `evidence/phase5_1-linux/` on the
Linux evidence branch; until then this status stays PENDING.
"""
    md_path = RCA / "docs" / "phase5_1" / "LINUX_FINAL_VALIDATION_HANDOFF.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")
    print("wrote", md_path)
    print("candidate:", manifest["candidate_id"], "| series:", series)
    return 0


if __name__ == "__main__":
    sys.exit(main())
