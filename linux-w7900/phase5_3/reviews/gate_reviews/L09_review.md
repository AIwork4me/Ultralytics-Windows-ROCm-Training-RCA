# Gate L09 Independent Subagent Review — BatchNorm Numerics / Dispatch Audit
Reviewer: fresh general subagent (ses_ee00cbecfffer0eDJl22O2dnoa)
## VERDICT: PASS
All 5 claims verified incl. independent recompile (bit-identical sha256 569a7249) and live
rerun on leg B (exit 0, identical metrics, fresh cache, PrepareInvoker + kernel run lines).
Full-gradient reference + NCHW strided indexing + constexpr predeclared tolerances confirmed
in source. Dev iterations ran against leg A only; leg B ran once with final binary (sound).
Honesty judgment: all admitted interim fixes were harness-defect fixes (allowed); no library
or tolerance changes.
### Findings & resolutions
- LOW-1 (hipMemcpy kind 3, unchecked returns) -> RESOLVED: kinds corrected to 1/2 per
  driver_types.h; both legs re-run: results identical; binary now a8c4a141...
- LOW-2 (rv_moved unconditional) -> RESOLVED: real measurement added (max |rv-1|=9.999e-02,
  consistent with expAvgFactor=0.1 and var~0 under scaled inputs).
- INFO-1 (input scaling bounds absolute-strength of numerics claim; A/B regression conclusion
  unaffected) -> documented in evidence.
- INFO-2 (interim-revision count wording) -> evidence reworded.
### Final state
Both legs: fwd/bwd status 0, sync OK, all 6 checks PASS (y 3.75e-7, dx 2.30e-7, dw 6.47e-7,
db 2.67e-7, rm 2.6e-12, rv_rel 5.4e-8), exit 0, identical metrics on both legs.
