"""Gate 32 reproduction: the length-preserving MIOpen.dll gate-flip
falsification experiment (7e9 -> 8e9). Backs up, patches, runs a
cache-isolated BN, RESTORES and verifies. Expected result: compile STILL
FAILS at the version-rotted shim (false_type/enable_if) - proving a naive
gate-number change is not a fix. Original SHA256 is asserted at both ends.
Usage: python 30_dll_gate_flip_experiment.py [--dry-run]
"""
import hashlib, os, shutil, subprocess, sys
MIO = os.path.join(os.environ.get(
    "YoloSitePackages",
    r"C:\Users\rocm\miniconda3\envs\yolo_amd\Lib\site-packages"),
    "_rocm_sdk_libraries", "bin", "MIOpen.dll")
EXPECT_SHA = "74b4ee038803606e6ea4846362a8565fa9e286cb0df18cf80b9e5a7657b78f0a"
PY = os.environ.get("YoloPython", r"C:\Users\rocm\miniconda3\envs\yolo_amd\python.exe")
OLD = b"HIP_PACKAGE_VERSION_FLAT < 7000000000ULL"
NEW = b"HIP_PACKAGE_VERSION_FLAT < 8000000000ULL"

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def run_bn():
    env = dict(os.environ, PYTHONNOUSERSITE="1",
               USERPROFILE=os.environ["ISO"], HOME=os.environ["ISO"],
               LOCALAPPDATA=os.path.join(os.environ["ISO"], "AppData", "Local"))
    r = subprocess.run([PY, "-c",
        "import torch,torch.nn as nn; bn=nn.BatchNorm2d(4).cuda().train();"
        " x=torch.randn(2,4,8,8,device='cuda'); y=bn(x);"
        " torch.cuda.synchronize(); print('BN OK', float(y.mean()))"],
        capture_output=True, text=True, env=env, timeout=600)
    return r.returncode, (r.stdout + r.stderr)

def main():
    assert sha(MIO) == EXPECT_SHA, "baseline SHA mismatch - abort"
    bak = MIO + ".gateflipbak"
    shutil.copy2(MIO, bak)
    data = bytearray(open(MIO, "rb").read())
    n = data.count(OLD); assert n == 2, f"expected 2 gate sites, found {n}"
    if "--dry-run" not in sys.argv:
        data = bytes(data).replace(OLD, NEW)
        open(MIO, "wb").write(data)
        print("patched sites:", n, "patched sha:", sha(MIO))
        import tempfile
        os.environ["ISO"] = tempfile.mkdtemp(prefix="gateflip_iso_")
        os.makedirs(os.path.join(os.environ["ISO"], "AppData"), exist_ok=True)
        rc, log = run_bn()
        print("bn rc:", rc)
        for line in log.splitlines():
            if "error" in line.lower() and ("expected class name" in line or "enable_if" in line):
                print("EVIDENCE:", line[:160])
        shutil.copy2(bak, MIO)
        assert sha(MIO) == EXPECT_SHA, "RESTORE FAILED"
        print("restored + verified:", sha(MIO))
        os.remove(bak)

if __name__ == "__main__":
    main()
