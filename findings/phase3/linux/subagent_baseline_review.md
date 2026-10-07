# Subagent Baseline Review — Gate L19

Date: 2026-10-07
Reviewer: independent general-purpose subagent (fresh context), mission:
"Try to prove the Linux baseline is invalid or contaminated."
Full review text preserved verbatim below.

## Verdict

BASELINE_VALID_WITH_NOTES

## Reviewer findings summary (full text follows)

- MAJOR-1 "fresh cache created today" claim contradicted by ukdb birth ts (2026-08-23) — **accepted; corrected via direct fresh-cache compile proof run**
- MAJOR-2 hiprtc-in-maps after BN is a DT_NEEDED artifact, not RTC proof — **accepted; doc corrected; fresh-cache INSERT INTO kern_db + comgr llvmcache now serve as the RTC proof**
- MAJOR-3 archived header-matrix JSON didn't match archived script (bodies `*out = 1;`) — **accepted; root cause: latent name-vs-include-line bug inherited from Phase-2 probe; fixed; matrix regenerated with std-exercising bodies, all PASS**
- MAJOR-4 GEMM/BN evidence generators not archived, unlabeled outputs — **accepted; gemm_control.py / batchnorm_matrix.py / run_fresh_cache.sh archived and re-run; labeled outputs; exit codes captured**
- MAJOR-5 "system ROCm not detected on library path" was false (/opt/rocm-7.2.1 on ldconfig) — **accepted; corrected with the three-part non-contamination proof (maps/RPATH/cache-tag) and the risk kept documented**
- MINOR-6 coco8 "already present" wrong (it downloaded on 4th attempt) — **accepted; corrected**
- MINOR-7 exit codes not captured for yolo runs — **accepted; predict+train re-run with yolo_predict_exit=0 / yolo_train_exit=0 in evidence**
- MINOR-8 which_stl.json program-log copy empty (trace escapes to stderr) — **accepted; both raw and filtered files retained with explanation**
- MINOR-9 same-day prior ultralytics run dirs not disclosed — **accepted; disclosed in deviations**
- NIT-10/11 phase-3 trees untracked (manifest/commit pending at Gates L47-L48); misc labeling — **addressed by this commit**

## Reviewer "checked and found clean" highlights

- Version line exact (torch 2.12.0+rocm7.14.0 / torchvision 0.27.0 / torchaudio 2.11.0 / ultralytics 8.4.174 / rocm 7.14.0 wheels / Python 3.13.15), verified live in-venv
- Wheel libMIOpen.so.1 independently re-hashed: byte-identical to provenance JSON; RPATH resolves deps into venv; zero /opt resolution in ldd
- HIPRTC probe genuinely targets gfx1151 and executes on GPU (all-zero return codes, gpu_result=1)
- Ultralytics 8.4.174 unmodified (372/372 RECORD hashes match); pyvenv.cfg isolated; no MIOPEN_*/HIP_*/ROCM_* overrides ambient or system-wide
- STL claim corroborated: raw RTC -H trace shows comgr-injected hiprtc_runtime.h + GCC-13 libstdc++ tree; wheel bundles no lib/gcc
- YOLO train artifacts coherent (best.pt/last.pt 5.5MB, per-class mAP, timeline consistent)

## Full verbatim review

(The reviewer's complete output, as returned to the validator, follows.)

---

# Adversarial Review — Linux Baseline (Gate L19) Validity

**VERDICT: BASELINE_VALID_WITH_NOTES**

The headline conclusion — the controlled wheel line (torch 2.12.0+rocm7.14.0 / ultralytics 8.4.174 / Python 3.13.15) passes GEMM, spatial BatchNorm, standalone HIPRTC header compiles with GPU execution, and YOLO inference+training on gfx1151, with the **wheel** MIOpen loaded — survives adversarial scrutiny. However, two *mechanism* claims in the claim document are wrong or unsupported, and there are provenance gaps a hostile reviewer must know about. Nothing found rises to contamination or invalidation of the PASS results.

## Findings

### MAJOR-1 — "Fresh MIOpen cache created today" is false; the ukdb predates the session by 6 weeks
- Claim: `findings/phase3/linux/linux_baseline.md:43-44` — "Fresh kernel cache created at first spatial BN: ~/.cache/miopen/3.5.2.cd957402/gfx1151_20.ukdb (runtime RTC compile genuinely happened — not a stale-cache artifact)."
- Fact (read-only `stat`): `/home/amd/.cache/miopen/3.5.2.cd957402/` and `gfx1151_20.ukdb` both have **Birth: 2026-08-23 09:08:39**. The file was *not* created today. Its only write today is **Modify 15:37:41** — during the YOLO train, ~12 minutes after the BN evidence runs. The same MIOpen build (version tag 3.5.2.cd957402) ran on this machine on Aug 23, so the kernel DB could contain pre-existing BN kernels.

### MAJOR-2 — loaded_modules.txt cannot prove the RTC path ran during BatchNorm (DT_NEEDED makes hiprtc map with MIOpen)
- `readelf -d .venv/.../_rocm_sdk_libraries/lib/libMIOpen.so.1` shows `DT_NEEDED: libhiprtc.so.7`, `libamd_comgr.so.3`, `libamdhip64.so.7`. The dynamic loader maps all NEEDED libraries when libMIOpen is mapped. The generator filtered the BEFORE snapshot to `["miopen"]` only, so hiprtc's absence before BN was never actually observed.
- Impact: maps still prove **which** libraries were used (all wheel paths), but not that an RTC compile happened during the BN.

### MAJOR-3 — Archived header-matrix evidence does not match the archived script
- JSON records `source` bodies of exactly `*out = 1;` — headers included but not used, while the archived script generates std-exercising bodies. Evidence not regenerable from the archived script — a provenance defect. (Even with `*out = 1;`, an unresolvable `#include <type_traits>` is a hard error, so 6/6 PASS still proves header resolution.)

### MAJOR-4 — The generators of the core GEMM/BN evidence are not in the repository
- gemm.txt / bn_minimal.txt / bn_matrix.txt match no archived script's output format; no exit-code capture. PASS semantics unreviewable.

### MAJOR-5 — Claim doc misstates machine state: a system ROCm IS on the library path
- `/opt/rocm -> /etc/alternatives/rocm -> /opt/rocm-7.2.1` exists; `ldconfig -p` lists its libMIOpen.so.1 etc. The doc's sentence "system ROCm not detected on library path" was factually wrong. Mitigation: no contamination demonstrated (RPATH/ldd/maps/cache-tag all resolve to the wheel stack).

### MINOR-6 — Deviation 1's "coco8 was already present" is contradicted by the evidence (download succeeded on 4th attempt, "Unzipping … Dataset download success ✅ (189.5s)").

### MINOR-7 — "exit 0" for YOLO runs asserted but never captured in evidence.

### MINOR-8 — STL "-H trace" evidence chain reproducibility-fragile: which_stl.json has empty log (trace escapes to process stderr); the doc cites the filtered file while quoting raw-file-only lines; raw file retained and self-authenticating.

### MINOR-9 — Machine not pristine same day (empty ultralytics run dirs earlier that day), only partially disclosed.

### NIT-10 — Phase-3 trees untracked in git at review time; no MANIFEST/SHA256SUMS yet.

### NIT-11 — Misc: unlabeled bn_matrix values; empty skeleton evidence dirs; LINUX_STL_BASELINE.md omits that the host-mode driver probe failed (rc=1, legitimate since device path is the relevant one); "libhiprtc 9.0" is the self-reported hiprtcVersion inside a 7.14 stack — worth a clarifying note.

## What was checked and found clean (reviewer's list)

1. Version line exact, verified live in the venv (torch 2.12.0+rocm7.14.0, torchvision 0.27.0+rocm7.14.0, torchaudio 2.11.0+rocm7.14.0, ultralytics 8.4.174, rocm wheels 7.14.0, hip 7.14.60850, Python 3.13.15); "51 packages compatible" matches.
2. Wheel libMIOpen loaded (maps proof real); reviewer independently re-hashed the wheel libMIOpen.so.1 (sha256 f5be2328…, 477251657 bytes, byte-identical to provenance JSON); binary contains "MIOpen version 3.5.2."; RPATH resolves all NEEDED deps into the venv; ldd shows zero /opt resolution; today's cache writes under wheel tag 3.5.2.cd957402.
3. HIPRTC probe genuinely targeted gfx1151 (`--gpu-architecture=gfx1151` into hiprtcCompileProgram) and genuinely executed on GPU (exec_control all-zero return codes, memcpyDtoH kind 2, gpu_result=1 — wrong-arch code object would fail hipModuleLoadData).
4. No evidence of ATen-native fallback for spatial BN; archived probe runs spatial BN2d in-process with wheel MIOpen mapped and PASSes.
5. YOLO train genuinely completed (1 epoch 16.3s, validation per-class mAP, last.pt/best.pt 5,522,693 bytes each, CUDA:0 banner, timeline coherent).
6. No validator contamination: ultralytics 8.4.174 verified unmodified (372/372 RECORD hashes), pyvenv.cfg include-system-site-packages=false, no MIOPEN_*/HIP_*/ROCM_* overrides ambient or in /etc/environment, /etc/profile.d/.
7. STL resolution corroborated: raw RTC trace contains comgr-injected hiprtc_runtime.h + GCC-13 libstdc++ tree; driver hip-offload search list includes /usr/lib/gcc/.../include/c++/13; no lib/gcc under wheel llvm dirs; system g++ 13.3.0 present; wheel libc++ exists but is not in the device search list.
8. Bootstrap claims match (kernel 6.17.0-1032-oem ≥ 6.14, render+video membership, /dev/kfd + renderD128 rw, no passwordless sudo); GPU identity consistent across rocminfo/torch/cache filename (gfx1151_20.ukdb).

## Bottom line (reviewer)
Baseline *results* credible and independently corroborated where generators are archived; the *mechanism narrative* (fresh cache + hiprtc-after-BN) was the weakest part and should be corrected; GEMM/BN generators plus exit-code capture should be archived and the claims downgraded or re-proven.

---

(End of reviewer output. Validator remediation of every accepted finding is
recorded in the table at the top of this file and in the revised
findings/phase3/linux/linux_baseline.md.)
