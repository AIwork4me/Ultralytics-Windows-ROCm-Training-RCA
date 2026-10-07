"""Gate L14: prove which MIOpen/HIPRTC libraries PyTorch loads, via /proc/self/maps.

1. import torch
2. run a MIOpen-backed BatchNorm (spatial train mode — the RTC path)
3. read /proc/self/maps
4. print every loaded path matching miopen/hiprtc/amdhip/comgr (case-insensitive)
"""

import sys


def loaded_matches(keywords):
    hits = set()
    with open("/proc/self/maps") as f:
        for line in f:
            path = line.rstrip("\n").partition(" /")[2]
            if not path:
                continue
            path = "/" + path
            low = path.lower()
            if any(k in low for k in keywords):
                hits.add(path)
    return sorted(hits)


def main() -> int:
    import torch
    import torch.nn as nn

    print("torch:", torch.__version__, "hip:", torch.version.hip)

    # pre-BN: what's loaded before any MIOpen call
    pre = loaded_matches(["miopen"])
    print("\n--- miopen mapped BEFORE batchnorm ---")
    for p in pre:
        print(p)

    m = nn.BatchNorm2d(16).cuda().train()
    x = torch.randn(8, 16, 64, 64, device="cuda")
    y = m(x)
    torch.cuda.synchronize()
    print("\nBN2d train result:", y.shape, "PASS")

    print("\n--- modules matching miopen/hiprtc/amdhip/comgr AFTER batchnorm ---")
    for p in loaded_matches(["miopen", "hiprtc", "amdhip", "comgr"]):
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
