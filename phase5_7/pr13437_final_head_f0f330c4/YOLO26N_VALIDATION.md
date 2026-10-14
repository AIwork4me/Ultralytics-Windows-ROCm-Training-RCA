# YOLO26n End-to-End Smoke Validation — patched wheel DLL (leg F)

## Scenario
The real-world workload that motivated the contribution: Ultralytics YOLO26n
training on native Windows with the AMD ROCm PyTorch wheels. Executed as
`scripts/f_yolo26n_coco8.py` (archived verbatim) with the pinned-build
MIOpen.dll swapped into the wheel stack.

- Ultralytics 8.4.174, PyTorch 2.12.0+rocm7.14.0, Python 3.13.16
- Model: local `yolo26n.pt`; dataset: local COCO8 (4 train / 4 val images)
- 1 epoch, imgsz 640, batch 8, workers 0, seed 7, deterministic

## Runtime-binary provenance
Same swap protocol as leg D: wheel DLL verified `c739cb0e…` (the `f0f330c4`
build) while the test ran; in-process
`MIOpen.dll loaded from: …site-packages\_rocm_sdk_libraries\bin\MIOpen.dll`;
wheel restored + verified `74b4ee03…` afterwards. Additionally, the
`EvaluateInvokers` diagnostics in the log embed `C:/w56/projects/miopen/…`
source paths compiled into that DLL.

## Results (raw: `raw/yolo/F_yolo26n_coco8.log`, exit 0)

- GPU recognized: `CUDA:0 (AMD Radeon(TM) 8060S Graphics, 80065MiB)`
- One full training epoch completed: `1 epochs completed in 0.008 hours`
  (a single 1-iteration batch step at 22.8 s + 2.6 s validation)
- Validation after training: P 0.553, R 0.961, mAP50 0.942, mAP50-95 0.668 —
  consistent with the pre-squash round on the same seed/dataset
- **AMP checks ran and passed this round** (`AMP: checks passed`) — an
  improvement over the earlier round where the AMP precheck was
  offline-skipped; it is reported separately and not attributed to this fix.
- Absence checks: the log contains **no** `'type_traits' file not found`, no
  `HIPRTC_ERROR_COMPILATION`, and no new MIOpen compile failure. The only
  MIOpen diagnostics are the pre-existing, unrelated
  `EvaluateInvokers … Invalid elapsed time` timing-quirk messages and CK
  symbol-resolution warnings also present on the unpatched stack.
- The known `EvaluateInvokers` timing messages and the `fdb.txt` unreadable
  warning are environmental and orthogonal to this PR.

## Boundary statements
- This validates **this workload** (YOLO26n + COCO8, 1 epoch, gfx1151,
  ROCm 7.14 wheels). It does not claim universal YOLO/Windows support.
- Model weights and dataset were already on disk; nothing large was
  downloaded for training (the AMP precheck downloads its own copy of
  yolo26n.pt by Ultralytics design).
- Hostname occurrences in the raw log were redacted (`DESKTOP-REDACTED`)
  with a byte-preserving substitution; the published file is `cmp`-identical
  to the reference substitution output (same CR counts; the only byte
  differences are the eight hostname replacements themselves). SHA256SUMS
  covers the redacted file; the untouched original remains on the
  validation machine.
