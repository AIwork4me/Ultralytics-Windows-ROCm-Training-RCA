"""AMP precheck replacement matcher — geometric detection equivalence.

Replaces ``torch.allclose(a, b, atol=0.5)`` on raw post-NMS box tensors inside
Ultralytics ``check_amp``/``amp_allclose`` (ultralytics/utils/checks.py).

WHY (RCA, amp-rca/ROOT_CAUSE.md): fp16 conv kernels legitimately move box
coordinates 0.07-0.76 px at imgsz 640 with identical detections/classes/
confidences (dconf <= 0.0043). An absolute 0.5 px tolerance on coordinates
rejects healthy stacks, and the verdict flips on MIOpen kernel-cache state —
a coin flip, not a numerical verdict.

ACCEPTANCE CRITERIA (each justified — mission §4.2):
  1. count equality: missing/extra detections are material -> fail
  2. finiteness: any NaN/Inf anywhere -> fail
  3. one-to-one class-constrained matching, greedy by FP32 conf desc,
     best-IoU first: order-independent (NMS tie reordering is benign),
     class flips fail, injective (no double-matching)
  4. matched pairs need IoU >= 0.95 — the strictest standard COCO operating
     point; below it the two boxes are different objects
  5. matched pairs need per-coordinate absolute drift <= abs_tol =
     1.0 px * (imgsz/640) + 0.5% of the FP32 box max-extent:
     - floor 1 px @640 gives 1.3x margin over the largest observed benign
       fp16 drift (0.76 px) while remaining 30x tighter than a "anything
       goes" tolerance
     - the relative term bounds large boxes: a 600 px box tolerates ~4 px,
       but a 10 px shift (>=2.5x over) still fails — no concealment of
       large absolute errors on huge boxes
     - tiny boxes are protected by IoU: 1 px shift on an 8 px box gives
       IoU ~0.56 -> fail despite the 1 px floor
  6. confidence drift per matched pair <= 0.05 (benign observed <= 0.0043,
     a 10x margin); larger drift = material behavior change -> fail
  7. degenerate/zero-area boxes fail conservatively (IoU=0; an identical
     degenerate box on both sides is still flagged — disclosed limitation)
  8. empty-vs-empty passes (nothing to compare); empty-vs-nonempty = count
     mismatch fail
  9. comparisons carry a 1e-6 epsilon (float32 rounding at tolerance scale;
     1e4x below any meaningful drift — not a semantic relaxation)
 10. device-agnostic pure numerics — no device-specific paths (CUDA NVIDIA
     behavior unchanged: element diffs there are already <= old atol and
     remain far inside these criteria); CPU/MPS early-return in check_amp
     is upstream's, not touched by the matcher

This is NOT a blind diagonal-IoU swap: matching is injective and
class-constrained, so reordering and ties are handled and a class flip can
never "match" geometrically.
"""
from __future__ import annotations

import torch

IOU_THRESHOLD = 0.95
CONF_TOLERANCE = 0.05
ABS_FLOOR_PX_AT_640 = 1.0
REL_BOX_TOLERANCE = 0.005  # 0.5% of FP32 box max-extent
REF_IMGSZ = 640.0


def box_iou_xyxy(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """Pairwise IoU for [N,4] xyxy vs [M,4] xyxy — pure torch, no torchvision
    dependency; degenerate (zero/negative-area) boxes yield IoU 0."""
    if a.numel() == 0 or b.numel() == 0:
        return torch.zeros(a.shape[0], b.shape[0])
    area_a = (a[:, 2] - a[:, 0]).clamp_min(0) * (a[:, 3] - a[:, 1]).clamp_min(0)
    area_b = (b[:, 2] - b[:, 0]).clamp_min(0) * (b[:, 3] - b[:, 1]).clamp_min(0)
    lt = torch.maximum(a[:, None, :2], b[None, :, :2])
    rb = torch.minimum(a[:, None, 2:], b[None, :, 2:])
    wh = (rb - lt).clamp_min(0)
    inter = wh[..., 0] * wh[..., 1]
    union = area_a[:, None] + area_b[None, :] - inter
    return torch.where(union > 0, inter / union.clamp_min(1e-12), torch.zeros_like(inter))


def amp_match_verdict(a: torch.Tensor, b: torch.Tensor, imgsz: float = REF_IMGSZ) -> dict:
    """Decide whether FP32 boxes `a` and AMP boxes `b` ([N,6] xyxy conf cls)
    are detection-equivalent under fp16 quantization. Returns a verdict dict
    with reason codes so tests can assert WHY, not just pass/fail."""
    reasons: list[str] = []
    a = a.detach().float().cpu()
    b = b.detach().float().cpu()
    floor = ABS_FLOOR_PX_AT_640 * (float(imgsz) / REF_IMGSZ)

    if a.numel() == 0 and b.numel() == 0:
        return {"verdict": True, "reasons": ["both_empty"], "floor_px": floor,
                "iou_threshold": IOU_THRESHOLD, "conf_tolerance": CONF_TOLERANCE}
    if not torch.isfinite(a).all():
        reasons.append("non_finite_in_fp32_boxes")
    if not torch.isfinite(b).all():
        reasons.append("non_finite_in_amp_boxes")
    if reasons:
        return {"verdict": False, "reasons": reasons, "floor_px": floor}

    if a.dim() != 2 or b.dim() != 2 or a.shape[1] < 6 or b.shape[1] < 6:
        return {"verdict": False, "reasons": ["unexpected_shape"],
                "shapes": [list(a.shape), list(b.shape)]}
    if a.shape[0] != b.shape[0]:
        return {"verdict": False,
                "reasons": ["detection_count_mismatch"],
                "counts": [int(a.shape[0]), int(b.shape[0])]}

    n = a.shape[0]
    cls_a, cls_b = a[:, 5], b[:, 5]
    conf_a, conf_b = a[:, 4], b[:, 4]
    iou = box_iou_xyxy(a[:, :4], b[:, :4])

    order = torch.argsort(conf_a, descending=True, stable=True)
    matched_b: list[int] = []
    pair_stats = []
    for ai in order.tolist():
        cand_iou = iou[ai].clone()
        cand_cls_ok = cls_b == cls_a[ai]
        for bj in matched_b:
            cand_iou[bj] = -1.0
        if not bool(cand_cls_ok.any()):
            return {"verdict": False, "reasons": ["class_set_mismatch_no_candidate"],
                    "counts": [n, n], "first_unmatched_fp32_index": ai,
                    "cls_fp32": cls_a.tolist(), "cls_amp": cls_b.tolist()}
        cand_iou[~cand_cls_ok] = -1.0
        best = int(torch.argmax(cand_iou).item())
        best_iou = float(cand_iou[best].item())
        if best_iou < IOU_THRESHOLD or best_iou <= 0.0:
            return {"verdict": False, "reasons": ["no_class_matched_box_with_iou_ge_threshold"],
                    "counts": [n, n], "first_unmatched_fp32_index": ai,
                    "best_iou_found": best_iou, "iou_threshold": IOU_THRESHOLD,
                    "hint": ("class flip, material geometric shift, or degenerate/zero-area "
                             "box (IoU of a zero-area box is 0 by definition)")}
        matched_b.append(best)
        extent = float(torch.max(a[ai, 2:4] - a[ai, 0:2]).item())
        abs_tol = floor + REL_BOX_TOLERANCE * extent
        drift = float((a[ai, :4] - b[best, :4]).abs().max().item())
        conf_drift = float(abs(conf_a[ai].item() - conf_b[best].item()))
        pair_stats.append({"a_index": ai, "b_index": best, "iou": best_iou,
                           "abs_coord_drift_px": drift, "abs_tol_px": abs_tol,
                           "conf_drift": conf_drift})
    if len(matched_b) != n:  # unreachable by construction; defensive
        return {"verdict": False, "reasons": ["matching_incomplete"], "counts": [n, n]}

    for ps in pair_stats:
        if ps["iou"] < IOU_THRESHOLD - 1e-6:
            reasons.append("iou_below_threshold")
        if ps["abs_coord_drift_px"] > ps["abs_tol_px"] + 1e-6:
            reasons.append("absolute_coordinate_drift_over_scale_sensitive_bound")
        if ps["conf_drift"] > CONF_TOLERANCE + 1e-6:
            reasons.append("confidence_drift_over_tolerance")
        if reasons:
            return {"verdict": False, "reasons": reasons, "pairs": pair_stats,
                    "worst_pair": max(pair_stats, key=lambda p: p["abs_coord_drift_px"])}

    return {"verdict": True, "reasons": ["detection_equivalent"],
            "pairs": pair_stats,
            "max_iou": max(ps["iou"] for ps in pair_stats),
            "max_abs_coord_drift_px": max(ps["abs_coord_drift_px"] for ps in pair_stats),
            "max_conf_drift": max(ps["conf_drift"] for ps in pair_stats),
            "floor_px": floor, "iou_threshold": IOU_THRESHOLD,
            "conf_tolerance": CONF_TOLERANCE}


def amp_allclose(m, im, model=None) -> bool:
    """Drop-in replacement for the body of ultralytics.utils.checks.amp_allclose
    (8.4.182). `m` is the YOLO object check_amp passes; `model` is the outer
    closure nn.Module upstream uses for stride — defaults to m.model when
    called outside the closure. The minimal upstream patch replaces only the
    final `return a.shape == b.shape and torch.allclose(a, b.float(), atol=0.5)`
    with `return amp_match_verdict(a, b, imgsz=imgsz)["verdict"]`."""
    from ultralytics.utils.torch_utils import autocast

    nn_module = model if model is not None else m.model
    device = next(nn_module.parameters()).device
    batch = [im] * 8
    imgsz = max(256, int(nn_module.stride.max() * 4))
    a = m(batch, imgsz=imgsz, device=device, verbose=False)[0].boxes.data
    with autocast(enabled=True, device=device.type):
        b = m(batch, imgsz=imgsz, device=device, verbose=False)[0].boxes.data
    return amp_match_verdict(a, b, imgsz=float(imgsz))["verdict"]
