# DCO, COPYRIGHT AND CONTRIBUTION POLICY — Gate P54-09

Mission: `WINDOWS-P54-MIOPEN-UPSTREAM-MERGE-READINESS` · Re-audited 2026-10-09 at upstream develop `681bc9ed`.

## 1. Upstream contribution instructions re-check (at `681bc9ed`)

| Source | Finding |
|---|---|
| Root `CONTRIBUTING.md` (rocm-libraries) | Development workflow / superbuild / sparse-checkout guidance. **No DCO, no `Signed-off-by`, no Developer Certificate of Origin requirement anywhere in the file** (case-insensitive scan). |
| `projects/miopen/CONTRIBUTING.md` | "All contributions you make will be under the **MIT Software License** (LICENSE.txt)." PR-process section (small commits, well-organized sequence). **No DCO / Signed-off-by requirement.** |
| `.github/PULL_REQUEST_TEMPLATE.md` | Not present at that path (404 via API). No sign-off checkbox exists to satisfy. |
| Repo commit practice (empirical) | Last 5 develop commits (`681bc9ed` window): **0 `Signed-off-by` trailer lines** — upstream commits are routinely merged unsigned. |
| Repository enforced checks | No DCO-check app configuration discoverable through the public API surface (no `.github/workflows` DCO gate; the workflow changes in the base→develop window contain none). |

**Conclusion — DCO policy**: DCO sign-off is **NOT required** by the project's current contribution instructions. Per the mission rule, a maintainer's mere recommendation would not make it mandatory; none was even found. Decision: **commits remain unsigned**; no `Signed-off-by` trailer is added. If a human later decides to sign, that is a `git commit --amend -s` away and does not change any tree/blob identity — only commit SHAs.

## 2. Recorded compliance status (unchanged boundaries)

```text
RIGHT_TO_CONTRIBUTE = USER_CONFIRMED
DCO_SIGNOFF         = NOT_AUTHORIZED
UPSTREAM_SUBMISSION = NOT_AUTHORIZED
```

The user previously confirmed: "AIwork4me owns the relevant copyright or has obtained authorization to contribute under the applicable license." No DCO certification is made on the user's behalf.

## 3. Copyright and license attribution

- All four new files (`miopen_freestanding_type_traits.hpp`, `miopen_freestanding_utility.hpp`, `miopen_freestanding_initializer_list.hpp`, `test/hiprtc_selfcontained.cpp`) carry the **full MIT License block with `Copyright (c) 2026 AIwork4me`**.
- Convention check (Gate P54-03 §C7): the full MIT block is exactly the convention of top-level `projects/miopen/test/*.cpp` drivers (`conv2d.cpp`) and `src/kernels/*.hpp` (`miopen_cstdint.hpp`, © 2023 AMD). The MIT text is preserved verbatim; only the holder line differs, truthfully.
- The MIT license text is unchanged from upstream's; contribution under it is what `projects/miopen/CONTRIBUTING.md` explicitly states ("All contributions … under the MIT Software License").

## 4. Git identity (prospective submission branch)

- Author/committer: `AIwork4me <AIwork4me@users.noreply.github.com>` — matches the GitHub account that will own the eventual PR (API-verified account `AIwork4me`, and the `gh` session in this mission is authenticated as that account).
- No change to copyright holder is made anywhere without factual basis; no DCO trailer is added.

## 5. Verdict

**PASS** — DCO not required upstream; commits stay unsigned by design; copyright attribution truthful and convention-conformant; right-to-contribute user-confirmed; upstream submission remains NOT_AUTHORIZED (human decision).
