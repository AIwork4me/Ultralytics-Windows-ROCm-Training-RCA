"""Gate L35 part 1: capture deterministic BN outputs under a given MIOpen build.

Usage: numerics_capture.py <unpatched|patched> <output.pt>

Fixed seeds; identical operator sequence; saves every output tensor needed
for the unpatched-vs-patched comparison (y, running stats, input/weight/bias
gradients) plus a CPU reference for sanity.
"""

import sys

import torch
import torch.nn as nn

CASES = [
    ("bn2d_train_min", "BatchNorm2d", (8, 16, 64, 64)),
    ("bn2d_train_3956", "BatchNorm2d", (2, 32, 32, 32)),
    ("bn2d_train_yololike", "BatchNorm2d", (16, 64, 160, 160)),
    ("bn3d_train", "BatchNorm3d", (4, 16, 8, 16, 16)),
    ("bn1d_3d_train", "BatchNorm1d", (8, 16, 32)),
    ("bn2d_eval", "BatchNorm2d", (8, 16, 64, 64)),
]


def main() -> int:
    which, out_path = sys.argv[1], sys.argv[2]
    data = {}
    for name, kind, shape in CASES:
        torch.manual_seed(1234)
        gen = torch.Generator(device="cpu").manual_seed(1234)
        x_cpu = torch.randn(*shape, generator=gen)
        m = getattr(nn, kind)(shape[1]).cuda()
        # fixed weights for eval-mode meaningfulness
        with torch.no_grad():
            for p in m.parameters():
                p.copy_(torch.randn_like(p))
        is_eval = name.endswith("eval")
        x = x_cpu.cuda().requires_grad_(not is_eval)
        m.train(mode=not is_eval)
        if is_eval:
            with torch.no_grad():
                y = m(x)
            data[f"{name}/y"] = y.cpu()
        else:
            y = m(x)
            y.sum().backward()
            torch.cuda.synchronize()
            data[f"{name}/y"] = y.cpu()
            data[f"{name}/xgrad"] = x.grad.cpu()
            data[f"{name}/wgrad"] = m.weight.grad.cpu()
            data[f"{name}/bgrad"] = m.bias.grad.cpu()
            data[f"{name}/running_mean"] = m.running_mean.cpu()
            data[f"{name}/running_var"] = m.running_var.cpu()
        # CPU reference (same weights/x)
        mcpu = getattr(nn, kind)(shape[1])
        mcpu.load_state_dict({k: v.cpu() for k, v in m.state_dict().items()})
        mcpu.train(mode=not is_eval)
        with torch.no_grad():
            yref = mcpu(x_cpu)
        data[f"{name}/y_cpu_ref"] = yref
    torch.save(data, out_path)
    print(f"saved {len(data)} tensors -> {out_path} (build={which})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
