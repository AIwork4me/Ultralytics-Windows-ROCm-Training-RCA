# P16 INDEPENDENT USER ACCEPTANCE (2026-11-15)

Per mission §6.7.

## State

- [Issue #14](https://github.com/AIwork4me/Ultralytics-Windows-ROCm-Training-RCA/issues/14) (invitation to @LZ-QWQ): OPEN, **0 comments** (re-checked live at P16 start). The invited developer has not responded.
- No other independent Windows Radeon developer has been recruited; per mission §6.7 the invitation stays open and no work is assigned without acceptance.

## Verdict: BLOCKED_INDEPENDENT_USER_TEST

No independent execution of the official documented workflow can be recorded. Additionally, even a willing tester would currently hit the release blocker (no official package contains the MIOpen fix — see P16_NO_STL_RELEASE_ACCEPTANCE.md), so the honest independent-acceptance experiment cannot succeed today regardless of participation.

## Record-keeping plan (unchanged, ready)

When a tester accepts, record: GitHub identity (with consent), hardware, Windows/driver/package versions, exact commands, first-attempt success/failure, unexpected installation steps, errors, interventions, duration, final outputs, raw logs — plus the honest possibility of a genuine FAIL being valid evidence.

## Owner / next action

- Owner: invited developer (@LZ-QWQ, no obligation) / RCA maintainer for publicizing a broader invitation.
- The invitation becomes actionable the moment AMD publishes a fixed `rocm_sdk_libraries` (see P16_WINDOWS_RELEASE_OWNER_MAP.md); until then an independent test of the official path would legitimately FAIL at the BatchNorm/training step.
