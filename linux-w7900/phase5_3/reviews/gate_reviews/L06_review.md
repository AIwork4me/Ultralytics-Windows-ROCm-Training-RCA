# Gate L06 Independent Subagent Review — Dynamic Library Audit
Reviewer: fresh general subagent (ses_ee036c98effeXhY2MO5fpUCSTJ)
## VERDICT: PASS
All 4 claims independently reproduced from freshly compiled probe. Contamination scan
strengthened by auditor (broader /opt/rocm OR rocm-7.2 pattern, post-GPU-init): 0 hits both legs.
### Live hazard confirmed (Phase-5.2 concern)
Bare dlopen("libMIOpen.so.1") under env_rocm7141.sh resolves to the WHEEL MIOpen
(sha 941a92da..., exists in 3 wheel locations incl torch/lib). Legs absent from LD_LIBRARY_PATH.
MITIGATION VERIFIED: run_validation_leg.sh-style wrapper (leg lib prepend + LD_PRELOAD leg
libMIOpen.so.1) flips resolution to the leg (7e045dc0). ALL L08/L09 runs MUST use that wrapper.
### Findings
- LOW-1 probe contamination literal 'rocm-7.2.1' only -> auditor's broader scan clean; noted.
- LOW-2 CK grouped-conv sublibrary comes from wheel on BOTH legs identically (A/B invariant
  intact; kthvalue unaffected; warnings logged in both legs equally).
- NIT-1 probe exit does not gate on miopenCreate rc (rc was 0, recorded separately).
- NIT-2 popen quoting brittleness (harmless for these paths).
