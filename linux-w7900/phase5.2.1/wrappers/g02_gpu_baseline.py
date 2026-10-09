"""G02 baseline GPU test — mission-canonical script (verbatim logic).

Run under a chosen environment (system 7.2.1 or isolated 7.14.1).
Additionally records the actually-loaded MIOpen library path from
/proc/<pid>/maps after CUDA init (provenance requirement).
"""
import json
import subprocess
import sys

import torch
import torch.nn as nn

result = {"argv0_py": sys.executable, "torch": torch.__version__,
          "torch_hip": torch.version.hip}

print("Torch:", torch.__version__)
print("HIP:", torch.version.hip)
print("Available:", torch.cuda.is_available())

assert torch.cuda.is_available()

print("Device:", torch.cuda.get_device_name(0))
result["device"] = torch.cuda.get_device_name(0)

x = torch.randn(2048, 2048, device="cuda")
y = x @ x
torch.cuda.synchronize()

assert torch.isfinite(y).all()
result["matmul"] = "PASS"

m = nn.BatchNorm2d(16).cuda().train()
a = torch.randn(
    8, 16, 64, 64,
    device="cuda",
    requires_grad=True
)

b = m(a)
b.square().mean().backward()

torch.cuda.synchronize()

assert torch.isfinite(b).all()
assert torch.isfinite(a.grad).all()
result["bn_forward"] = "PASS"
result["bn_backward"] = "PASS"

print("BASELINE GPU + BATCHNORM PASS")

# --- provenance: which MIOpen did this process actually load? ---
maps = open(f"/proc/{__import__('os').getpid()}/maps").read()
miopen_paths = sorted({l.rstrip().split()[-1] for l in maps.splitlines()
                       if "libMIOpen" in l and l.rstrip().split()[-1].startswith("/")})
result["loaded_libMIOpen_paths"] = miopen_paths
print("Loaded libMIOpen:", miopen_paths)
for p in miopen_paths:
    sha = subprocess.run(["sha256sum", p], capture_output=True, text=True).stdout.split()[0]
    print(f"  sha256({p}) = {sha}")
    result.setdefault("libMIOpen_sha256", {})[p] = sha

hip_paths = sorted({l.rstrip().split()[-1] for l in maps.splitlines()
                    if "libamdhip64" in l and l.rstrip().split()[-1].startswith("/")})
result["loaded_libamdhip64_paths"] = hip_paths
print("Loaded libamdhip64:", hip_paths)

json.dump(result, open(sys.argv[1], "w"), indent=2)
print("WROTE", sys.argv[1])
