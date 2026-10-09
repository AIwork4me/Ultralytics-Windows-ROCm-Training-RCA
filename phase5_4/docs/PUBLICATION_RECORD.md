# PUBLICATION RECORD — Phase 5.4 (Gate P54-13)

- Branch: `phase5.4/windows-upstream-merge-readiness` (from main `58da94e`; no merge into main; no internal PR)
- Evidence commit: `91610753b97518b0ca8894172028a27ef83a1a0a` ("phase5.4: latest-develop merge-readiness evidence package (P5.4-SUBMISSION-CANDIDATE-R1)")
- Publication-record commit: see git log of this file (this commit).
- Remote: `origin` = `https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA.git`

## Remote verification performed (after push)

1. `git ls-remote`: branch tip = `91610753b97518b0ca8894172028a27ef83a1a0a` — identical to local HEAD (byte-level: `git fetch` + `rev-parse` comparison).
2. All 21 required artifacts present on the remote ref (docs×9, findings×4 incl. FINAL_GATE.md + SUBMISSION_CANDIDATE.json, evidence×8 incl. manifest + all gate JSONs, reviews/UPSTREAM_REVIEW_PANEL.md; zero MISSING).
3. Remote tree contains 55 files under `phase5_4/` = 54 manifest-listed + the manifest itself — consistent with `evidence/evidence_manifest.json`.
4. Patch-series identity from REMOTE blob bytes (`git cat-file blob` of the remote ref): concat-v1 SHA256 `8e00f59114d17205d06664a065856bbd9012e40065e8826e4725f790c024a0c5` — matches `SUBMISSION_CANDIDATE.json`.
5. Immutability of frozen history re-verified: `phase5.1/windows-r2-ci-portability-freeze` = `c8417161125dc33275b7ac615298b449a81e7cf8` (unchanged); `main` = `58da94e` (this branch is NOT merged); `linux-w7900/phase5.3-r2-final-ab` untouched.
6. No upstream repository was pushed to; the prospective candidate branch `miopen/hiprtc-freestanding-upstream-ready` exists only in the local rocm-libraries clone (push URL additionally guarded to `no-push`).

Push succeeded on attempt 1 (earlier phases needed retries; one transient `Recv failure` during a follow-up ls-remote resolved on retry).
