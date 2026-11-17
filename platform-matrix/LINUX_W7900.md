# WINDOWS_LINUX_W7900 — template for when hardware is available

**Status: BLOCKED_HARDWARE — no result exists; do not cite gfx1151 results here.**

## To execute when an RX 7900 XTX / W7900 (gfx1100 (Linux)) Ubuntu 26.04 LTS machine is connected

```powershell
# 1. environment (isolated venv/conda)
python -m pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ "torch[device-gfx1100 (Linux)]==<version-from-index>" "torchvision[device-gfx1100]==<same>"
python -m pip install ultralytics

# 2. provenance probe (in-process loaded DLL + HIP + device)
python release-provenance/scripts/probe_loaded_miopen.py --out raw/gfx1100 (Linux)_provenance.json

# 3. G1 primitive matrix (3 independent cold cache homes, STL + no-STL legs)
python windows-training-validation/scripts/g1_runner.py --python <env-python> --legs gfx1100 (Linux)_stl --mode stl --repeat 3 --raw-dir windows-training-validation/raw --report-dir windows-training-validation/reports

# 4. G2 lifecycle (each task)
python windows-training-validation/scripts/g2_runner.py --python <env-python> --task detect --data coco8.yaml --weights yolo26n.pt --infer-source <images-dir> --raw-dir windows-training-validation/raw

# 5. G3 AMP decomposition + real-AMP probe
python windows-training-validation/tests/g3_amp_rca.py --out raw/g3_amp_gfx1100 (Linux).json --repeats 5
python windows-training-validation/tests/g3_amp_training_10ep.py --out raw/g3_amp10_gfx1100 (Linux).json
```

Record driver + wheel + MIOpen sha256 in the results; update `GPU_SUPPORT_MATRIX.md` only with actual outputs.
