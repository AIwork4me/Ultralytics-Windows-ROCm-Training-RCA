# Final Submission Checklist — P5.1-CANDIDATE-R1

Single source of truth for identities: `findings/phase5_1/FINAL_HANDOFF.json`.
This checklist references it; it does not duplicate hand-maintained hashes.

## Engineering state (DONE on Windows)

- [x] Three-commit series on exact frozen base `7c5866144ac4b…`
      (`d4003de1` → `3b18a065` → `e7ff6d75`; subjects match manifest).
- [x] Canonical patches byte-exact under `patches/phase5_1/canonical/`
      (LF-only; `.gitattributes` `patches/** -text` protects checkout).
- [x] Series hash `sha256_file_concat_v1` verified by producer, freeze
      verifier, and Reviewer A independently.
- [x] Source-tree reconstruction (base + ordered patches == candidate
      tree `605d0d21…`) proven via `git am` AND `git apply --index` +
      `write-tree`.
- [x] Copyright: FOUR of four new files carry
      `Copyright (c) 2026 AIwork4me`; MIT text verbatim; P5→P5.1 delta
      is exactly those 4 comment lines (+4/−4); AMD notices untouched.
- [x] Windows validation at the exact final source: CI 4/4, A/B matrix
      13/13, DLL `9a774402…` rebuilt + load-proven, no-STL BN PASS,
      numerics PASS (bit-identical to P5), YOLO26n 1-epoch PASS
      (amp=False required minimum; amp_default passed as training with
      environment-attributed AMP-check fallback — control evidence
      recorded), wheel + MSVC environment restored hash-verified.
- [x] Freeze integrity: independent verifier PASS (6/6 verdict tokens).
- [x] Adversarial reviews A/B/C: all BLOCKER/MAJOR/MINOR findings
      resolved pre-publication (`findings/phase5_1/reviews/resolutions.json`).

## Human actions required before ANY submission

- [ ] **DCO certification decision.** Commits are deliberately unsigned
      (`DCO: PENDING HUMAN CONFIRMATION` marker in each message).
      Upstream CONTRIBUTING.md files state no DCO requirement, but the
      user must decide whether to certify. If yes, follow EXACTLY
      `docs/phase5_1/COPYRIGHT_AND_DCO_STATUS.md` §3 (reword each
      commit; `Signed-off-by: AIwork4me <AIwork4me@users.noreply.github.com>`;
      regenerate + re-hash patches; update the manifest; metadata-only
      change so validation remains applicable).
- [ ] **Linux independent validation.** Execute
      `docs/phase5_1/LINUX_FINAL_VALIDATION_HANDOFF.md` on the Linux
      machine: verify patch/series hashes FIRST (fail closed), build
      unpatched + patched MIOpen from source, HIPRTC A/B
      (negative exact-signature on unpatched; positive on patched;
      in-tree ctest), DIRECT `miopenKthvalueForward` runtime A/B
      (dladdr provenance, fresh `MIOPEN_CUSTOM_CACHE_DIR`,
      `MIOPEN_LOG_LEVEL=6`, same harness binary both sides, exact
      values+indices vs CPU, byte-identical A/B outputs), BN spot-check,
      optional YOLO26n amp=False. Record under `evidence/phase5_1-linux/`.
- [ ] **Submission-day applicability re-check** of upstream `develop`
      (Gate P5-02 method); rebase/regenerate if develop moved.
- [ ] **Regenerate the PR draft from the P5.1 manifest**
      (`docs/phase5/PR_DRAFT_FINAL.md` is superseded-annotated; do not
      reuse as-is).

## Submission day hard gates

- [ ] DCO decided (signed or explicitly accepted-unsigned).
- [ ] Linux validation PASS recorded against the exact P5.1 identities.
- [ ] Manifest updated to `FINAL_SUBMITTABLE_FREEZE` only after the two
      above; otherwise it stays `TECHNICALLY_VERIFIED_PROVISIONAL_FREEZE`.
- [ ] Human approval to submit (separate explicit authorization; this
      mission's authorization covers contribution rights, NOT submission).

## Prohibitions still in force

No upstream PR / issue / comment; no push to ROCm repositories or forks;
no modification of historical Phase-3/4/5 evidence; no force-push of the
evidence branch after publication.
