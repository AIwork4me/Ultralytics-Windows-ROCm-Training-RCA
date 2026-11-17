# G7 attempt 1 — census cmdline truncation defect (disclosed, preserved)

- Attempt 1 (`attempt1_workers8_*` files, run-id `R22A5N-GFX1100-G7-W8`,
  envelope `stage_logs/attempt1_g7_workers8_20261117T072143_7788/`)
  physically PASSED: training with workers=8 completed
  `ADAMW_AMP_MULTISTEP_PASS` (11/6/5 attempts/effective/inf-skip), the live
  census recorded 16 simultaneous trainer children — all 16 carrying
  `spawn_main` — and the post-run orphan check recomputed `leftover=[]`
  (CLEAN).
- The r22a5n1100 hardened acceptance engine REJECTED the gate
  ("workers exercise incomplete — raw-snapshot recomputation failed").
  Root cause, confirmed from the attempt-1 raw snapshot: the deepest
  trainer process on THIS host's topology is the *real* interpreter behind
  the venv redirector (venv created by `install_official.ps1` from the uv
  base CPython WITHOUT `--copies`), whose command line is
  `"C:\Users\Rocm\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\python.exe" -X utf8 C:/Users/Rocm/Desktop/YOLO/rca-r21/windows-golden-path/scripts/audit_adamw_amp.py ...`
  — the `audit_adamw_amp` token lands past the 160-char cmdline truncation
  the census snapshot stored, so the engine's independent
  trainer-recomputation identified the redirector (pid 19432) instead of the
  real trainer (pid 15968) and correctly refused to certify identity it
  could not re-derive.
- This failure mode is host-topology-dependent: gfx1151's census (miniconda
  python, shorter paths) never tripped it. The hardened gate did its job —
  it refused to trust the stored `spawn_children_of_trainer` summary when
  the raw snapshot could not independently confirm trainer identity.
- Fix: `worker_stage.py` snapshot capture widened from 160 to 400 cmdline
  chars (the CIM query already captured 400; the extra bytes were being
  discarded). Additive change; historical receipts untouched.
- Attempt 2 (run-id `R22A5N-GFX1100-G7-W8-R2`) re-ran the full workers=8
  exercise with the widened capture. Attempt-1 evidence is preserved
  unmodified and disclosed here; nothing was overwritten.
