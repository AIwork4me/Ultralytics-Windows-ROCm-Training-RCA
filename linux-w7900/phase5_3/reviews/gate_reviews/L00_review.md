# Gate L00 Independent Subagent Review — Hardware/ROCm Isolation Audit
Reviewer: fresh general subagent (session ses_ee07eb6e1ffeoInbjHX84RuKyI)
## VERDICT: PASS
All 8 claims independently reproduced. Leg A lib SHA256 and harness SHA256 independently
confirmed (mission brief harness string = 64-char true hash + trailing 'f' typo).
### Findings
- BLOCKER: none
- MAJOR: none
- MINOR-1: ldconfig cache maps ROCm libs -> /opt/rocm-7.2.1; LD_LIBRARY_PATH precedence covers
  today, but every subsequent gate must re-verify no /opt/rocm-7.2.1 in loaded maps (standing check).
- MINOR-2: Mission brief harness hash is 65 chars (invalid); documented in evidence JSON.
- NIT-1: W7900D marketing-name artifact of rocminfo version; 0x744b gfx1100 silicon confirmed.
- NIT-2: rocminfo_gpu_agent capture field empty; gfx1100_section carries data.
- NIT-3: Single-GPU cgroup isolation (8x GPUs on host, 1 exposed) - good determinism.
### False-claim checks performed
GPU compute proven via independent hipcc SAXPY kernel (residual 0) + torch matmul vs CPU;
system ROCm leak tested at PATH/LD_LIBRARY_PATH/live-maps levels (0 entries); hash lengths
and prefix equality independently computed; HSA_OVERRIDE_GFX_VERSION unset.
### Standing action for later gates
Re-verify /proc maps free of /opt/rocm-7.2.1 at L05/L06/L07/L08/L09.
