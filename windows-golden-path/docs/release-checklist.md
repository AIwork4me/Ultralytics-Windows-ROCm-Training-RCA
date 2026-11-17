# Release Checklist — Windows Radeon YOLO Golden Path (R22 GO/NO-GO)

One line per gate; a gate is PASS only with archived evidence. No partial
success may be reported as Golden Path availability.

## Pre-flight (any run)
- [ ] `run-golden-path.ps1 -Preflight` baseline written (R21_ENVIRONMENT_BASELINE.json)
- [ ] GPU idle during acceptance measurements (no concurrent GPU jobs)
- [ ] Workspace `C:\RadeonYOLO\` used; P17/P18/P19 untouched

## G0 — Official artifact provenance
- [ ] Wheel set resolved ONLY from observed index pages (wheel_discovery.json)
- [ ] Every wheel URL + SHA256 frozen in resolved_wheel_lock.json
- [ ] Downloaded bytes hash-verified BEFORE install
- [ ] Loaded MIOpen.dll SHA256 + version string recorded; build lineage traced
      (GitHub compare `f0a5d266...<commit>` behind_by=0, NOT date inference)
- [ ] No workaround detected (else verdict ceiling drops to ENGINEERING_REFERENCE)

## G1 — MIOpen no-STL regression
- [ ] BatchNorm2d(100) @ (20,100,35,45) fwd+bwd finite under
      VCToolsInstallDir-redirect + empty INCLUDE + fresh cache, NO shim
- [ ] Pre-fix wheel reproduces #3956 signature (negative control archived)

## G2 — PyTorch/torchvision GPU gates
- [ ] 9/9 gates PASS on GPU (is_available, identity, FP32/FP16 GEMM, autograd,
      conv, BN, torchvision nms, tensor lifetime, clean exit)
- [ ] No CPU fallback anywhere; device wheels present

## G3 — Standard Ultralytics workflow
- [ ] `ultralytics==8.4.214` released wheel (non-editable)
- [ ] Exact CLI `yolo train model=yolo26n.pt data=coco8.yaml epochs=1 device=-1`
- [ ] Genuine GPU via device=-1, AMP recorded, epoch+val complete, ckpts hashed, exit 0

## G4 — Real optimizer updates
- [ ] ≥1 optimizer step; named_parameters delta >1e-9 (buffers excluded); finite
- [ ] Per-step GradScaler history (skips counted from history, not inferred)

## G5 — Checkpoint resume
- [ ] Interrupt only after last.pt fully written; NEW process resume=True
- [ ] Epoch continuity; best.pt GPU inference in a third process

## G6/G7 — Physical gfx1100 + gfx1151
- [ ] Both architectures run G1..G5 (portable runner, identical bytes)
- [ ] gfx1151 evidence independently generated on Radeon 8060S hardware

## G8 — Reliability
- [ ] ≥10 independent training processes per arch; cold AND warm cache classes
- [ ] Zero unexplained hipErrorInvalidKernelFile / MIOpen solver / CK-symbol /
      HIPRTC failures (tracked as separate families)

## G9 — Clean Windows
- [ ] CLEAN_WINDOWS_INSTALL class requires a fresh/controlled Windows image
      (no historical caches, no host STL dependency, no shims, no PYTHONPATH)
- [ ] On a development host this gate is BLOCKED_INFRASTRUCTURE — record it

## Channel ceiling rules
- dev/nightly/rc locks → at most *_CANDIDATE_PASS; stable lock required for
  OFFICIAL_STABLE_PASS; functional PASS never promotes the channel class.

## Final verdict vocabulary (exact meanings — see mission §21)
R21_HARNESS_VALIDATED / R22_BLOCKED_OFFICIAL_ARTIFACT / R22_CANDIDATE_VALIDATED /
R22_OFFICIAL_STABLE_PASS / R23_DRAFT_READY / R23_RELEASE_READY
