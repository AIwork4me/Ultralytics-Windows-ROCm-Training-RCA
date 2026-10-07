# Phase-3 PATCH_HANDOFF Independent Review (Gate 10)

Reviewer: fresh adversarial subagent (independent session). Mandate: try
to prove `findings/phase3/PATCH_HANDOFF.json` points to the wrong patch,
wrong source SHA, wrong hashing algorithm, or an ambiguous consumer
contract. Method: independent recomputation of all identities from Git
blob bytes + live-fire tamper tests of the verifier in a throwaway repo.

## VERDICT: PASS

No BLOCKER or MAJOR findings. Every identity claim was independently
reproduced from Git blob bytes; the verifier rejected all six tamper
attacks with nonzero exit; the consumer contract is explicit and
internally consistent; superseded artifacts are correctly excluded; no
validation claim outruns the evidence.

## Independent verification results

| Check | Result |
|---|---|
| SHA256(blob 0001) | MATCHES `f06d7ae5d87f73e102c10a4e985afde70659210b96e5ad3247eeea85f4568e20` |
| SHA256(blob 0002) | MATCHES `77f9fc1613695b849a5b04e59723c05482467ddc34d0a9d53bf3cdd31f761532` |
| SHA256(concat 0001‖0002) | MATCHES `b1150afcf2170a9d396f9a25669547c0ed4021c221f7feaa59e073d4b9706685` — reverse-order concat yields a DIFFERENT hash (`b32318b2…`), so the series hash cryptographically pins order |
| Ordering | Unambiguous: order fields [1,2] = array order = lexical names = README order = conclusion `final_patch_path` |
| Superseded fencing | `candidate_v1.diff` + `miopen_hiprtc_freestanding_v2.patch` marked "SUPERSEDED … do not submit" in patches/phase3/README.md; neither appears in the handoff (strict parse: exactly two series entries) |
| Source SHA | `b68f8944300f104875d953fc8e4510908c9aaf0b` corroborated by phase3_conclusion.json AND evidence/phase3/raw/source/upstream_baseline.txt (remote URL matches) |
| Algorithm reproducibility | Definition == `git cat-file blob` + `cat` + `sha256sum` on Linux, no transcoding; reproduced exactly from Windows (platform independence demonstrated); blob-byte authority additionally proven via git blob-IDs `37a36710…`/`458e0e24…` — these are Git blob identities, correctly NOT used as SHA256 |
| Contract flags | patch_mutation_allowed=false; source/individual/series must_match=true; upstream pr/issue/comment=false (strict JSON parse, duplicate-key detection) |
| Verifier live-fire | 6/6 tamper attacks rejected exit 1 (flip hash char; tamper series hash; wrong source sha; wrong algorithm string; order swap; appended byte to blob); baseline `HANDOFF VALID` exit 0 |
| Validation-block traceability | every PASS entry traced to phase3_conclusion.json fields; `linux_regression: "PENDING"` consistent with conclusion's BLOCKED (no PASS claim) |

## Findings (all MINOR/NIT — none invalidate)

1. **MINOR — Windows CRLF smudge trap**: working-tree copies hash
   differently (`521b6cc0…`/`e8d45e03…`, CRLF) than the LF blobs; a
   Windows consumer hashing the checked-out file with `Get-FileHash`
   would mismatch. The blob-bytes definition is the correct and only
   portable reading; defused for anyone using the verifier or
   `git cat-file`.
2. **MINOR — verifier did not enforce policy blocks** (consumer_contract
   / upstream_state). → FIXED by producer (see disposition below).
3. **MINOR — `intended_consumer` lane name unresolvable inside the repo**
   (requirements live in `findings/phase3/reviewer_pr_readiness.md`);
   contract itself unambiguous.
4. **MINOR — handoff uncommitted at review time** (by design, pre-commit
   stage). → Resolved by this commit + push.
5. NIT: `linux_regression` PENDING vs conclusion's BLOCKED wording —
   same substance, producer→consumer framing.
6. NIT: `final_patch_roundtrip.txt` says "403 lines" for 0001 (blob is
   404 LF-terminated lines; SHA256 unaffected).
7. NIT: a third superseded `.patch` exists in the directory — consumers
   must use the handoff paths, not globs.
8. NIT: verifier prints a git "fatal" line in pre-commit fallback mode
   (cosmetic).

## Producer disposition (2026-10-08, pre-commit)

- Handoff JSON kept EXACTLY per the mandated template (no structural
  changes; only real hash values inserted).
- MINOR 2: ACCEPTED — `scripts/phase3/verify_patch_handoff.py` now also
  machine-checks `consumer_contract` (patch_mutation_allowed=false;
  three must-match flags=true) and `upstream_state` (all false), failing
  nonzero on violation.
- MINOR 4: resolved by committing and pushing the handoff; post-push
  verification runs against `origin/main` blobs.
- MINORs 1/3 and NITs 5-8: documented here; no further action.
