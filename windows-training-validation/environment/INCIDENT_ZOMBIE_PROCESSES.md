# INCIDENT — zombie python processes holding env-B MIOpen.dll

Date: 2026-11-14 · Machine: gfx1151 workstation

## What happened

During G1, two `pm13437_merged` python processes became unkillable zombies:

| PID | Origin | State |
|---|---|---|
| 29152 | first BN-estimator probe run (killed via shell TaskStop mid-GPU-op) | stuck in HIP driver cleanup; `Stop-Process` no-op, `taskkill /F` reports "no instance running" while WMI still lists it |
| 10940 | second BN-estimator probe run — **printed its full results, then hung at exit-time cleanup** (never returned; script's final print had flushed) | same unkillable state |

Both keep `...\pm13437_merged\...\_rocm_sdk_libraries\bin\MIOpen.dll` mapped, so
`envb_dll_swap.py --action restore` fails with `WinError 32` (file in use).

## Impact & disposition

- ENV B remains in **SOURCE_BUILT_PATCHED (ed7c67a9)** state — restore-to-official
  deferred; this is exactly the state required for the G2/G3 ENV-B legs, so no work is blocked.
- ENV A untouched (official, pristine). New GPU processes run fine alongside the zombies
  (verified: all G1 legs completed after the first zombie existed).
- Restore plan: re-run `envb_dll_swap.py --action restore` after the zombies clear
  (or after a reboot, Owner action); hash-verify e97891df.

## Stability signal (feeds G4.3)

1 of ~15 GPU processes today hung at *normal exit* (after results were produced) —
exit-time GPU cleanup hang on this driver/HIP stack (7.14.60850). The other was
force-killed mid-op (expected behavior). Recorded as a stability observation, not
a functional failure; new processes unaffected.

## RESOLVED — 2026-11-14 19:39 local

All three zombie PIDs (29152/10940/43404) cleared on their own — **no reboot needed**.
`envb_dll_swap.py --action restore` executed successfully (exit 0):

- before: `ed7c67a9…` (SOURCE_BUILT_PATCHED) → after: `e97891df…` (**OFFICIAL_WHEEL**, expected hash match)
- `ENVB_DLL_STATE.json` now records the restore; `verify_release_closure.py` re-run after restore: 184 checks, 0 violations, exit 0.
- ENV B is back to pristine official-wheel state.
