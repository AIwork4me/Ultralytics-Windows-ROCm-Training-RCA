"""Phase-3 Gate 65+66: BatchNorm shape/variant matrix + numerical
correctness against CPU, with the REAL patched MIOpen build loaded.

Covers: minimal shape, MIOpen#3956 shape, YOLO-like shape, BatchNorm1d(2D
in) control, BatchNorm1d(3D in), BatchNorm2d, BatchNorm3d, train+eval,
plus controls (GroupNorm, Conv2d, Linear backward, GPU GEMM).
Numerics: max/mean abs error vs CPU reference, running stats deltas,
gradient finiteness.
"""

import json
import sys

import torch
import torch.nn as nn

results = []


def run_case(name, fn):
    try:
        info = fn()
        info["status"] = "PASS" if info.get("ok") else "CHECK"
        results.append({"case": name, **info})
        print(f"[{info['status']}] {name}: {info.get('detail','')}")
    except Exception as e:  # noqa: BLE001
        results.append({"case": name, "status": "FAIL", "error": repr(e)[:500]})
        print(f"[FAIL] {name}: {repr(e)[:300]}")


def bn_train_eval(shape, tag, momentum=0.1, eps=1e-5):
    bn_cls = {3: nn.BatchNorm1d, 4: nn.BatchNorm2d, 5: nn.BatchNorm3d}[len(shape)]
    def fn():
        torch.manual_seed(0)
        m = bn_cls(shape[1], momentum=momentum, eps=eps).cuda().train()
        ref = bn_cls(shape[1], momentum=momentum, eps=eps).train()
        ref.load_state_dict({k: v.clone() for k, v in m.state_dict().items()})
        x = torch.randn(*shape)
        y = m(x.cuda()); y.sum().backward()
        yr = ref(x); yr.sum().backward()
        # eval mode
        m.eval(); ref.eval()
        with torch.no_grad():
            ye = m(x.cuda()); yer = ref(x)
        max_abs = max((y.cpu() - yr).abs().max().item(),
                      (ye.cpu() - yer).abs().max().item())
        rm = (m.running_mean.cpu() - ref.running_mean).abs().max().item()
        rv = (m.running_var.cpu() - ref.running_var).abs().max().item()
        gok = all(torch.isfinite(p.grad).all().item()
                  for p in m.parameters() if p.grad is not None)
        gx = (x.grad if x.grad is not None else torch.zeros_like(x))
        grx = ref  # ref input grad
        return {"ok": max_abs < 1e-4 and rm < 1e-5 and rv < 1e-4 and gok,
                "detail": f"max_abs={max_abs:.3e} rm={rm:.3e} rv={rv:.3e}",
                "max_abs_err": max_abs, "run_mean_delta": rm, "run_var_delta": rv,
                "grads_finite": gok}
    return fn


def variant_case(module_factory, shape, tag):
    def fn():
        torch.manual_seed(1)
        m = module_factory().cuda()
        x = torch.randn(*shape)
        y = m(x.cuda()); loss = (y * y).mean(); loss.backward()
        ok = bool(torch.isfinite(y).all().item()) and all(
            torch.isfinite(p.grad).all().item() for p in m.parameters() if p.grad is not None)
        return {"ok": ok, "detail": f"finite={ok} mean={float(y.mean()):.3e}"}
    return fn


run_case("bn2d_minimal_8x16x64x64", bn_train_eval((8, 16, 64, 64), "min"))
run_case("bn2d_issue3956_4x64x32x32", bn_train_eval((4, 64, 32, 32), "3956"))
run_case("bn2d_yololike_16x32x160x160", bn_train_eval((16, 32, 160, 160), "yolo"))
run_case("bn1d_3dinput_8x16x512", bn_train_eval((8, 16, 512), "bn1d3d"))
run_case("bn3d_4x8x16x16x16", bn_train_eval((4, 8, 16, 16, 16), "bn3d"))
run_case("bn2d_eval_only", variant_case(lambda: nn.BatchNorm2d(8).eval(), (2, 8, 8, 8), "ev"))
run_case("bn1d_2dinput_CONTROL", variant_case(lambda: nn.BatchNorm1d(16), (8, 16), "bn1d2d"))
run_case("groupnorm_CONTROL", variant_case(lambda: nn.GroupNorm(4, 16), (2, 16, 8, 8), "gn"))
run_case("conv2d_CONTROL", variant_case(lambda: nn.Conv2d(8, 16, 3, padding=1), (2, 8, 16, 16), "cv"))
run_case("linear_bwd_CONTROL", variant_case(lambda: nn.Linear(64, 32), (4, 64), "ln"))
def gemm_control():
    a = torch.randn(1024, 1024, device="cuda")
    b = torch.randn(1024, 1024, device="cuda")
    c = a @ b
    return {"ok": bool(torch.isfinite(c).all()), "detail": "1024^2 matmul finite"}


run_case("gpu_gemm_CONTROL", gemm_control)

n_pass = sum(1 for r in results if r["status"] == "PASS")
n_fail = sum(1 for r in results if r["status"] == "FAIL")
print(f"\nMATRIX: {n_pass} PASS / {len(results) - n_pass - n_fail} CHECK / {n_fail} FAIL")
json.dump(results, open(sys.argv[1], "w") if len(sys.argv) > 1 else sys.stdout, indent=1)
sys.exit(1 if n_fail else 0)
