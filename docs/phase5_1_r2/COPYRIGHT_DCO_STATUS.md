# COPYRIGHT AND DCO STATUS — P5.1-CANDIDATE-R2

## Copyright — RESOLVED (carried from R1; R2 adds no files)
- All four new files carry `Copyright (c) 2026 AIwork4me`:
  src/kernels/miopen_freestanding_type_traits.hpp,
  miopen_freestanding_utility.hpp,
  miopen_freestanding_initializer_list.hpp,
  test/hiprtc_selfcontained.cpp.
- MIT license text preserved verbatim.
- Right to contribute: CONFIRMED_BY_USER (2026-10-08, R1 mission §3;
  identity AIwork4me <AIwork4me@users.noreply.github.com>).
- R2 modifies only projects/miopen/test/CMakeLists.txt — no new
  copyrightable file introduced.

## DCO — UNSIGNED BY DESIGN, MARKERS RESOLVED

Policy inspection (frozen upstream base 7c586614, re-verified this
mission): `CONTRIBUTING.md` (315 lines) and `.github/`/`docs/` contain NO
Signed-off-by / DCO / Developer Certificate requirement. The previously
reviewed conclusion stands: the project does not explicitly require DCO
certification.

Actions taken in R2 per mission §3:
- The provisional `DCO: PENDING HUMAN CONFIRMATION …` placeholder lines
  were REMOVED from all three R2 commit messages (verified: zero
  occurrences in commits and patches — verify_patch_identity.py enforces).
- NO `Signed-off-by` trailer was added: DCO certification was NOT
  separately authorized by the user, and removing a placeholder is not
  certification.
- Commits are therefore unsigned. They must never be described as
  DCO-certified.
- If upstream policy later turns out to require DCO (or the user chooses
  to certify), a human must authorize sign-off and the three-patch series
  must be regenerated — commit hashes, patch SHA256s and the series hash
  all change. Never amend the published R2 artifacts in place.

Human actions still pending:
1. Linux W7900 R2 validation (independent validator;
   docs/phase5_1_r2/LINUX_FINAL_VALIDATION_HANDOFF.md).
2. Submission-day develop re-check (upstream base may have moved).
3. Explicit authorization to create the upstream PR (not granted; none
   created).
