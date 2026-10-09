# H06 independent audit — BatchNorm numerics

VERDICT: PASS. BLOCKERS: none. MAJORS: none.
Reviewer rebuilt the harness from the checked-in source against legA public
headers, ran it on legA (exit 0): results identical to the shipped binary.
Re-ran both legs with fresh /tmp caches: CHECK lines byte-identical between
legs and to recorded logs. Tolerances verified as constexpr at source lines
104-105 (y 1e-5, dx 1e-5, dw 1e-4, db 1e-5, rm 1e-4, rv_rel 1e-3), printed
before GPU work; CPU reference verified genuine float64 full-gradient (not
inference shortcut). Measured margins 4-6 orders below tolerance; identical
across legs; MIOpenBatchNormFwdTrainSpatial/BwdSpatial dispatch proven with
-mcpu=gfx1151 and MIO_BN_GFX115X=1; per-leg fresh ukdb confirmed distinct.
Minors adopted: regex-misparse fields removed from evidence JSON with note;
same_binding_paths key annotated; cache-dir wording exactified.
