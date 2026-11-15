# P15.8 — Independent Developer Acceptance (2026-11-15)

Status: **BLOCKED_INDEPENDENT_USER_TEST** (maintained — verified live today).

## 1. Existing invitation state

- Issue: [AIwork4me/Ultralytics-Windows-ROCm-Training-RCA#14](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/issues/14), invitee **@LZ-QWQ**.
- Live check 2026-11-15: issue open, **comments: 0** (`release-provenance/raw/p15_baseline/issue14_state.json`). No response, no acceptance, no participation.
- No credit of any kind is granted to a non-participating invitee.

## 2. What is ready the moment a tester accepts

The acceptance package is content-complete and was executed end-to-end by the project owner on the official released stack in P14 (MODE B all-PASS):

| Provided item | Where |
|---|---|
| Public documentation links + supported hardware requirements | `golden-path/WINDOWS_SETUP.md` |
| Exact Golden Path acceptance commands | `golden-path/acceptance_manifest.json` (+ schema) |
| Executable steps (verify/train/validate/resume/checkpoint) | `golden-path/*.py` |
| Model/dataset identity | `yolo26n.pt` + COCO8 (smoke) / COCO128 (representative), locked versions in `requirements-lock.txt` |
| Expected outputs | `P14_GOLDEN_PATH_EXECUTION_REPORT.md` (mAP curve, resume row counts, error-UX texts) |
| Evidence manifest + safe error-report instructions | manifest + README |

Tester must NOT use RCA debugging commands, private DLLs, development forks, hidden patches, or undocumented troubleshooting — the kit enforces this by construction (official channels only).

## 3. GATE 4 relationship

GATE 4 (first-time developer success) requires GATE 3 to be meaningful: with official wheels still pre-#13437 (BLOCKED_RELEASE), an independent tester on the ordinary installation path would hit the no-STL failure — a genuine, well-documented FAIL would still be useful evidence, but the project does not route a tester into a known-broken official path before the release closure verdict changes.

Two separate dependencies, both external:
1. **GATE 3 / BLOCKED_RELEASE** — owner: AMD release chain.
2. **A real independent human** — owner: @LZ-QWQ (invitation open) or a new public call.

## 4. Public call for testers (prepared, not yet posted)

A short public call is prepared for posting either (a) when @LZ-QWQ declines/nonresponsive after a reasonable window, or (b) when GATE 3 clears, whichever comes first: it states the supported hardware (gfx1151-class Windows Radeon; second architecture class welcome), the time cost (≤2 h), the all-PASS/fail-logs reporting format, and explicitly promises no pressure to obtain a PASS (a documented FAIL is valuable). No Co-authored-by is added without real contribution; no write access is granted without consent.

## 5. Required verdict

**BLOCKED_INDEPENDENT_USER_TEST** — recorded without any claim of participation.
