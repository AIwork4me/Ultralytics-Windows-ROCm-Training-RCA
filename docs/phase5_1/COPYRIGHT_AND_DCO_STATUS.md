# Copyright and DCO Status — Phase 5.1 (Gates 04 + 05)

Date: 2026-10-08. Candidate under review: **P5.1-CANDIDATE-R1** (rebuilt
from P5-CANDIDATE-R1 with copyright attribution applied).

## 1. Authorship identity (established in Phase 5, unchanged)

```text
Git author:  AIwork4me <AIwork4me@users.noreply.github.com>
```

Verified in Phase 5 (see `docs/phase5/AUTHORSHIP_DCO_AUDIT.md` §1–2):
GitHub links both `AIwork4me@users.noreply.github.com` and
`AIwork4me@qq.com` to account `AIwork4me` (id 261514469). All P5.1
commits carry this exact author AND committer identity (local worktree
config; no environment fallback).

## 2. Right to contribute — CONFIRMED_BY_USER

The user explicitly confirmed during Phase 5.1 (mid-mission
authorization, 2026-10-08):

> "AIwork4me owns the relevant copyright OR has obtained the necessary
> authorization to contribute this code under the applicable open-source
> license."

Recorded status:

```text
RIGHT_TO_CONTRIBUTE = CONFIRMED_BY_USER (2026-10-08)
```

The four affected files are NEW files authored entirely within this
project (no third-party code); no external copyright holder exists to
attribute. Accordingly all four placeholders were replaced with exactly:

```text
Copyright (c) 2026 AIwork4me
```

MIT license text preserved verbatim (only the copyright-notice line
changed; comment-only delta, 1 line per file — verified by
`git diff 29846fc4..e7ff6d75`: 4 files, +4/−4 lines, no other change).

### The four files (GATE 05 scope)

```text
projects/miopen/src/kernels/miopen_freestanding_type_traits.hpp
projects/miopen/src/kernels/miopen_freestanding_utility.hpp
projects/miopen/src/kernels/miopen_freestanding_initializer_list.hpp
projects/miopen/test/hiprtc_selfcontained.cpp
```

Earlier Phase-5 documentation inconsistently said "3 MIT headers"
(itself an error caught by Reviewer D in Phase 5 but not propagated to
every summary). Phase 5.1 corrected every current checklist, conclusion
and summary to say FOUR: `findings/phase5/phase5_conclusion.json`
(`copyright_status`), `docs/phase5/AUTHORSHIP_DCO_AUDIT.md` §4,
`docs/phase5/P3_TO_P5_DELTA.md`. Historical reviewer transcripts under
`findings/phase5/reviews/` are immutable evidence and were NOT edited.

## 3. DCO status — DCO_ATTESTATION_PENDING (truthfully retained)

Upstream policy, read from the frozen tree at base
`7c5866144ac4b879be442563e2b49fa1c142ea36`:

- `CONTRIBUTING.md` (repo root): no DCO / `Signed-off-by` requirement
  (grep for dco|signed-off|sign off|developer certificate: no matches).
- `projects/miopen/CONTRIBUTING.md`: MIT-licensed contributions, branch
  + PR flow, two reviewers, regression test, issue association — **no
  DCO / Signed-off-by requirement stated** (same grep: no matches).
- Recent develop commits (`7c58661..`) carry no `Signed-off-by`
  trailers (squash-merged GitHub PRs).

The user confirmed the **right to contribute** but did NOT separately
instruct to certify the DCO. A DCO sign-off is a personal certification
distinct from authorship or right-to-contribute; Phase 5.1 therefore
keeps:

```text
DCO_STATUS = DCO_ATTESTATION_PENDING
```

All three P5.1 commits remain unsigned, each retaining the explicit
marker line (NOT a trailer, deliberately not parseable as a sign-off):

```text
DCO: PENDING HUMAN CONFIRMATION - provisional local commit, not for upstream submission; replace this line with a real Signed-off-by per DCO before submitting.
```

Consequence: P5.1-CANDIDATE-R1 is **technically frozen but NOT
submission-ready** until the DCO decision is made. This is a
human-authorization condition, not a technical defect.

### Exact sign-off instructions (if the user later certifies)

```bash
cd /c/Users/rocm/Desktop/YOLO_AMD/rocm-libraries-phase5.1-candidate
git rebase -i 7c5866144ac4b879be442563e2b49fa1c142ea36
# reword EACH of the three commits: delete the "DCO: PENDING..." line
# and add exactly (no other text on that line):
#   Signed-off-by: AIwork4me <AIwork4me@users.noreply.github.com>
git format-patch -o /tmp/p51-signed 7c5866144ac4b879be442563e2b49fa1c142ea36..HEAD
```

This changes commit SHAs and patch hashes again (metadata-only: tree
bytes unchanged, so the technical validation remains applicable, but
patches must be regenerated and re-hashed, and the manifest updated).

## 4. Status summary

```text
RIGHT_TO_CONTRIBUTE            = CONFIRMED_BY_USER (2026-10-08)
COPYRIGHT_FILES_RESOLVED       = 4/4 (Copyright (c) 2026 AIwork4me)
COPYRIGHT_FILES_PENDING        = 0
MIT_LICENSE_TEXT_PRESERVED     = YES (verbatim)
DCO_REQUIRED_BY_UPSTREAM       = NOT DOCUMENTED AS REQUIRED (no DCO text in
                                 root or projects/miopen CONTRIBUTING.md)
DCO_ATTESTATION                = PENDING (not authorized; markers retained)
CANDIDATE_CLASSIFICATION       = TECHNICALLY_VERIFIED_PROVISIONAL_FREEZE
```
