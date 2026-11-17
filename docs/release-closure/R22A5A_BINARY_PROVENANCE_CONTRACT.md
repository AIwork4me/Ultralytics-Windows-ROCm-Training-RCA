# R22A.5A Binary Provenance Contract — source-to-binary gate for the MIOpen fix

- Generated: 2026-11-17 (mission R22A.5A Phase B, §5)
- Status: **CONTRACT ACTIVE** — implemented by `scripts/r22a5a/audit_wheel_provenance.py`
  + `scripts/r22a5a/r22a5a_lib.py` + CPU negative controls in
  `windows-golden-path/tests/test_r22a5a_cpu.py`
- Critical fixed source commit: `f0a5d2664cf3334161f7b82c02dfcd2213988a8a`
  (ROCm/rocm-libraries PR #13437, squash-merged 2026-10-19)
- TheRock integration: PR #9359 merge `b0958085` (submodule bump to `d875648`,
  compare ahead_by=2 / behind_by=0 vs the fix)

## 1. Why this contract exists

The release blocker is **binary distribution, not source availability**. The
rc-channel precedent (`rocm_sdk_libraries-10.2.0rc2`, built 2026-11-06 —
AFTER the merge date — from a branch cut BEFORE it, compare `diverged`,
behind_by=92, marker=0) proves permanently:

> **A newer version number, a newer build date, or a matching-looking title
> proves NOTHING about fix presence. Only wheel-bytes → DLL-bytes →
> build-commit → ancestry evidence counts.**

## 2. The evidence chain (each step fail-closed)

| Step | Artifact | Method | Failure mode → classification |
|---|---|---|---|
| S1 | wheel bytes | bounded download from the EXACT official channel host (TLS, host allowlist, ≤3 GiB, cache-once) | non-official host → REFUSED |
| S2 | wheel identity | SHA256 of the wheel file | same version + different SHA than an audited anchor → `NEW_ARTIFACT_PROVENANCE_PENDING` / `BINARY_PROVENANCE_INCONCLUSIVE` (renamed artifact never inherits a frozen verdict) |
| S3 | archive safety | ZIP listing only: path-traversal / absolute-path member detection, NO extraction, NO execution | unsafe member → REFUSED |
| S4 | embedded MIOpen.dll | stream-hashed inside the ZIP (`_rocm_sdk_libraries/bin/MIOpen.dll`) | none present → not an SDK libraries wheel |
| S5 | screening marker | byte count of `miopen_initializer_list` (post-fix HIPRTC source registry string) | marker 0 → pre-fix bytes |
| S6 | build identity | embedded version string `3.x.y.<commit>` → build commit | absent → `NO_BUILD_IDENTITY` → inconclusive forever until identity exists |
| S7 | source ancestry | GitHub compare API `f0a5d266...<build_commit>`; behind_by==0 ⇔ the merged fix is an ancestor. **Never date inference; never commit-message matching.** | behind>0 or diverged → PRE_FIX even with marker>0; API unreachable → inconclusive (never silently passing) |
| S8 | set inheritance | a release-cut channel member of the SAME (channel, ROCm set version) inherits the audited set verdict with disclosure; dev/nightly (+git/.dev locals) NEVER inherit — every moving build is distinct | — |

## 3. Screening vs proof (the marker rule)

- `miopen_initializer_list` count ≥ 1 is a **screening signal**: necessary-ish,
  never sufficient. A matching marker does NOT prove the complete source fix
  is present and functioning.
- A version string alone cannot establish binary ancestry.
- `SOURCE_LINEAGE_CONFIRMED` (equivalently
  `STABLE_CANDIDATE_PENDING_GPU_VALIDATION` on stable/GA or
  `PRE_RELEASE_CANDIDATE` on rc/nightly/dev) requires **marker>0 AND
  behind_by==0** — both, always.
- A positive provenance verdict still **requires the runtime no-STL gate**
  (`verify_miopen_nostl.py --leg official`) on real hardware before any
  training PASS — executed in R22A.5B, never on CPU.

## 4. Frozen anchors (immutable reuse table)

Implemented as `r22a5a_lib.FROZEN_CHANNEL_ANCHORS` — verbatim from the
frozen R22 evidence (never mutated here):

| Channel | Package@version | Wheel SHA256 | DLL SHA256 / build | Marker | behind_by | Verdict |
|---|---|---|---|---|---|---|
| stable | rocm-sdk-libraries 10.1.0 | `0c34bafb…e06159` | `266d716b…1429b4` / `3.6.1.39d8d603` | 0 | — | OFFICIAL_PRE_FIX (P14/P15/P16 byte-identical) |
| rc | rocm-sdk-libraries 10.2.0rc2 | `ffbf6c77…ece25a` | `2a3a026c…fa6859` / `3.6.2.8faffed0f` | 0 | 92 | OFFICIAL_PRE_FIX (diverged branch) |
| nightly | rocm-sdk-libraries 10.3.0a20261115 | `33f5ea8a…fd465c` | build `9ea8cfc5` | 2 | 0 | fix present (frozen audit) |
| dev | rocm-sdk-libraries 10.3.0.dev0+ff576965… | `dac27df5…0b7d56` (gfx1151) | `47a2e32c…83b91` / `3.6.3.4e7d93e3` | 2 | 0 | fix present (frozen audit) |
| multi-arch | rocm-sdk-libraries 7.14.1 | installed-payload audit | `e97891df…647bc` / build `cd957402` | 0 | — | OFFICIAL_PRE_FIX (+ live no-STL EXPECTED_FAIL) |

Anchor reuse rule: an index artifact matching an anchor's
(channel, package, version) reuses the frozen verdict ONLY when its wheel
SHA256 (when known) matches; a SHA mismatch is a renamed/modified artifact
and fails to pending/inconclusive.

## 5. Fresh-audit results this mission (2026-11-17, live)

`release-provenance/r22a5a/nightly_wheel_audit_20261117.json` —
nightly `rocm_sdk_libraries-10.3.0a20261116`:

- wheel SHA256 `b11baad94242690642f95687993f200fe9ef27fcdbe34e2bbf4605e0407599f0`
- embedded MIOpen.dll SHA256 `f9312c3e646f5f871d30abfcb310cc5f7137499511e20e5e4b68d82d49a40cb6`
  (519,806,464 bytes)
- build commit `25f28906` (version `3.6.3.25f28906`), marker = 2
- ancestry `f0a5d266...25f28906`: **ahead_by=1074, behind_by=0** →
  `POST_FIX_LIBRARIES` (screening + lineage both positive)

Conclusion: the current nightly still carries the fix, but a nightly is a
development channel — it can never be labeled Stable and its physical
gates have not been run at this version (R22A.5B scope).

## 6. Negative controls (CPU, deterministic — all pinned in tests)

From mission §5.3, every one is enforced in
`windows-golden-path/tests/test_r22a5a_cpu.py`:

1. higher version + older DLL → OFFICIAL_PRE_FIX (`rc 10.2.0rc3` fixture)
2. fake fix marker (marker>0, ancestry diverged) → OFFICIAL_PRE_FIX
3. correctly named wheel, wrong hash → never inherits the anchor verdict
4. torch/SDK dependency mismatch (family mix / non-HIP torch) → plan UNQUALIFIED
5. Linux wheel cannot qualify as Windows (`win_amd64` false)
6. unsupported Python ABI → explicit plan blocker, never silent fallback
7. nightly cannot be labeled Stable (channel ceiling OFFICIAL_DEV)
8. missing build identity → BINARY_PROVENANCE_INCONCLUSIVE
9. unknown source ancestry never silently passes (ancestry absent → inconclusive)
10. incompatible device packages → set incomplete → UNQUALIFIED
11. forged serialized `verdict`/`fix_present` fields are never consulted
    (classification reads only embedded facts: marker + ancestry)
12. archive path traversal / absolute paths → inspection REFUSED

## 7. What this contract does NOT claim

- No physical GPU PASS of any kind (classifications are never training
  verdicts; R22A.5B gates G1..G9 decide on hardware).
- No claim that any current stable-channel artifact contains the fix
  (stable remains OFFICIAL_PRE_FIX at 10.1.0 as of 2026-11-17).
- No AMD-internal build metadata is assumed; when the publisher provides
  none, build identity comes from the embedded DLL version string only,
  and uncertainty is recorded honestly.
