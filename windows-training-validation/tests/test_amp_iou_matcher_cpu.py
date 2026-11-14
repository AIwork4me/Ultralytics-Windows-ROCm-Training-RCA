"""Adversarial CPU suite for the AMP precheck matcher (mission §4.2).

    python tests/test_amp_iou_matcher_cpu.py [--archived <paired_boxes.pt>]

Covers every acceptance criterion in amp_iou_matcher.py: benign fp16
quantization, reordering, NMS ties, class flips, missing/extra detections,
empty predictions, degenerate boxes, small/huge boxes, material shifts,
confidence drift, NaN/Inf, a genuinely broken AMP operator, and boundary
semantics — plus real archived FP32/AMP tensors from the gfx1151 capture
(the audit C-o5 requirement: the matcher must run against archived tensors
on CPU BEFORE any upstream submission).

Runs on CPU in any torch environment; no GPU, no Ultralytics.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amp_iou_matcher import amp_match_verdict, box_iou_xyxy

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {detail}")


def boxes(rows) -> torch.Tensor:
    """rows of (x1,y1,x2,y2,conf,cls) -> float tensor"""
    return torch.tensor(rows, dtype=torch.float32)


BASE = [(100, 120, 180, 240, 0.90, 5.0), (300, 320, 420, 460, 0.80, 0.0),
        (50, 60, 90, 130, 0.70, 2.0)]


def shift(rows, dx, dy=0.0):
    return [(x1 + dx, y1 + dy, x2 + dx, y2 + dy, c, k) for (x1, y1, x2, y2, c, k) in rows]


def case_benign_quantization():
    """Benign fp16 coordinate quantization: 0.76 px drift (largest observed
    real value) must PASS — this is the exact case the old atol=0.5 rejected."""
    a = boxes(BASE)
    b = boxes(shift(BASE, 0.76))
    v = amp_match_verdict(a, b)
    check("benign 0.76px drift PASSES (old atol=0.5 rejected this)",
          v["verdict"], json.dumps({k: v[k] for k in ("reasons", "max_abs_coord_drift_px")} if v["verdict"] else v))
    b2 = boxes([(r[0] + d, r[1], r[2], r[3], r[4], r[5])
                for r, d in zip(BASE, (0.1, 0.4, 0.76))])  # mixed per-column noise
    check("benign mixed per-column drift PASSES", amp_match_verdict(a, b2)["verdict"])


def case_reorder_and_ties():
    a = boxes(BASE)
    perm = [2, 0, 1]
    b = boxes([BASE[i] for i in perm])
    v = amp_match_verdict(a, b)
    check("reordered detections PASSES (order-independent matching)",
          v["verdict"] and sorted(ps["a_index"] for ps in v["pairs"]) == [0, 1, 2],
          json.dumps(v) if not v["verdict"] else "")
    # NMS tie: two same-class boxes with EQUAL conf swapped between runs
    tie = [(50, 50, 150, 150, 0.80, 1.0), (200, 200, 300, 300, 0.80, 1.0)]
    a_t, b_t = boxes(tie), boxes([tie[1], tie[0]])
    v2 = amp_match_verdict(a_t, b_t)
    check("NMS tie-reordering (equal conf, swapped) PASSES", v2["verdict"],
          json.dumps(v2) if not v2["verdict"] else "")
    # injectivity: two FP32 boxes must not collapse onto one AMP box
    a_dup = boxes([(100, 100, 200, 200, 0.90, 1.0), (105, 105, 205, 205, 0.85, 1.0)])
    b_one = boxes([(100, 100, 200, 200, 0.90, 1.0)])
    check("extra FP32 detection (count mismatch) FAILS",
          not amp_match_verdict(a_dup, b_one)["verdict"])


def case_class_flips():
    a = boxes(BASE)
    flipped = [list(r) for r in BASE]
    flipped[1][5] = 7.0  # class flip on the middle detection
    v = amp_match_verdict(a, boxes(flipped))
    check("class flip FAILS (class-constrained matching)",
          not v["verdict"] and "class_set_mismatch_no_candidate" in v["reasons"],
          json.dumps(v["reasons"]))
    # geometric overlap but class differs -> must still fail
    a2 = boxes([(100, 100, 200, 200, 0.9, 1.0)])
    b2 = boxes([(100, 100, 200, 200, 0.9, 3.0)])
    check("identical geometry, different class FAILS",
          not amp_match_verdict(a2, b2)["verdict"])


def case_count_changes():
    a = boxes(BASE)
    b_missing = boxes(BASE[:2])
    check("missing AMP detection FAILS", not amp_match_verdict(a, b_missing)["verdict"])
    b_extra = boxes(BASE + [(500, 500, 560, 560, 0.6, 4.0)])
    check("extra AMP detection FAILS", not amp_match_verdict(a, b_extra)["verdict"])


def case_empty():
    e = boxes([])
    check("empty-vs-empty PASSES with note", amp_match_verdict(e, e.clone())["verdict"])
    check("empty-vs-nonempty FAILS", not amp_match_verdict(e, boxes(BASE))["verdict"])
    check("nonempty-vs-empty FAILS", not amp_match_verdict(boxes(BASE), e)["verdict"])


def case_degenerate():
    a = boxes([(100, 100, 100, 200, 0.9, 1.0)])  # zero-width degenerate box
    check("zero-area box on both sides FAILS conservatively",
          not amp_match_verdict(a, a.clone())["verdict"],
          json.dumps(amp_match_verdict(a, a.clone())))
    a2 = boxes(BASE)
    b2 = boxes([(float("nan"), 100, 200, 200, 0.9, 5.0)] + BASE[1:])
    check("degenerate NaN-coordinate box FAILS", not amp_match_verdict(a2, b2)["verdict"])


def case_small_and_huge_boxes():
    # tiny box: 1px shift on an 8px box -> IoU ~0.56 -> FAIL (IoU protects tiny boxes)
    tiny_a = boxes([(100, 100, 108, 108, 0.9, 1.0)])
    tiny_b = boxes([(101, 100, 109, 108, 0.9, 1.0)])
    v = amp_match_verdict(tiny_a, tiny_b)
    check("1px shift on 8px box FAILS via IoU (no tiny-box permissiveness)",
          not v["verdict"] and "no_class_matched_box_with_iou_ge_threshold" in v["reasons"],
          json.dumps(v))
    # 0.2px shift on the tiny box: IoU ~0.9 -> borderline; 8px box with 0.2px
    # shift has IoU = ((7.8*8))/(64+64-62.4)... compute: inter 7.8*8=62.4 union 65.6 -> 0.951 PASS
    tiny_b2 = boxes([(100.2, 100, 108.2, 108, 0.9, 1.0)])
    check("0.2px shift on 8px box PASSES at IoU boundary", amp_match_verdict(tiny_a, tiny_b2)["verdict"],
          json.dumps(amp_match_verdict(tiny_a, tiny_b2)))
    # huge box: 10px shift on 600px box -> IoU ~0.97 (passes IoU) but rel bound
    # (1 + 0.005*600 = 4px) FAILS it — no concealment of large absolute errors
    huge_a = boxes([(20, 20, 620, 620, 0.9, 1.0)])
    huge_b = boxes([(30, 20, 630, 620, 0.9, 1.0)])
    v2 = amp_match_verdict(huge_a, huge_b)
    check("10px shift on 600px box FAILS via scale-sensitive absolute bound",
          not v2["verdict"] and "absolute_coordinate_drift_over_scale_sensitive_bound" in v2["reasons"],
          json.dumps(v2["reasons"]))
    # 3px shift on 600px box: within floor+rel (4px) and IoU 0.99 -> accepted
    huge_b2 = boxes([(23, 20, 623, 620, 0.9, 1.0)])
    check("3px shift on 600px box accepted (0.5% relative, documented criterion)",
          amp_match_verdict(huge_a, huge_b2)["verdict"])


def case_broken_operator():
    a = boxes(BASE)
    b = boxes(shift(BASE, 30.0))  # a genuinely broken AMP operator: wholesale displacement
    v = amp_match_verdict(a, b)
    check("genuinely broken AMP operator (30px displacement) FAILS", not v["verdict"],
          json.dumps(v["reasons"]))
    b2 = boxes([(x1 * 1.15, y1, x2 * 1.15, y2, c, k) for (x1, y1, x2, y2, c, k) in BASE])
    check("size-inflation corruption FAILS", not amp_match_verdict(a, b2)["verdict"])


def case_conf_drift_and_nan():
    a = boxes(BASE)
    drifted = [list(r) for r in BASE]
    drifted[0][4] += 0.06  # > 0.05 tolerance
    v = amp_match_verdict(a, boxes(drifted))
    check("confidence drift 0.06 FAILS", not v["verdict"]
          and "confidence_drift_over_tolerance" in v["reasons"], json.dumps(v["reasons"]))
    drifted2 = [list(r) for r in BASE]
    drifted2[0][4] += 0.0043  # largest observed benign fp16 conf delta
    check("confidence drift 0.0043 PASSES", amp_match_verdict(a, boxes(drifted2))["verdict"])
    nan_a = boxes(BASE)
    nan_a[0, 4] = float("nan")
    check("NaN in FP32 boxes FAILS", not amp_match_verdict(nan_a, boxes(BASE))["verdict"])
    inf_b = boxes(BASE)
    inf_b[1, 2] = float("inf")
    check("Inf in AMP boxes FAILS", not amp_match_verdict(boxes(BASE), inf_b)["verdict"])


def case_boundaries():
    a = boxes([(100, 100, 200, 200, 0.5, 1.0)])
    # conf drift exactly 0.05 -> inclusive PASS
    b = boxes([(100, 100, 200, 200, 0.55, 1.0)])
    check("boundary: conf drift == 0.05 PASSES (inclusive)", amp_match_verdict(a, b)["verdict"],
          json.dumps(amp_match_verdict(a, b)))
    b2 = boxes([(100, 100, 200, 200, 0.5501, 1.0)])
    check("boundary: conf drift 0.0501 FAILS", not amp_match_verdict(a, b2)["verdict"])


def case_archived(arch: Path | None):
    if arch is None or not arch.is_file():
        print("[SKIP] archived real-tensor cases (capture not yet produced — "
              "run tests/g3_amp_paired_boxes.py on GPU first)")
        return 0
    data = torch.load(arch, map_location="cpu", weights_only=False)
    n_pass = n_tot = 0
    for entry in data["captures"]:
        a, b = entry["fp32_boxes"], entry["amp_boxes"]
        v = amp_match_verdict(a, b)
        n_tot += 1
        n_pass += bool(v["verdict"]) == bool(entry.get("expected_verdict", v["verdict"]))
        label = f"archived[{entry.get('label', '?')}]"
        if not v["verdict"] and entry.get("expected_verdict", True):
            check(f"{label}: real benign fp16 tensors PASSES matcher", False,
                  json.dumps(v)[:400])
        else:
            print(f"[INFO] {label}: verdict={v['verdict']} "
                  f"max_drift={v.get('max_abs_coord_drift_px')} old_allclose={entry.get('old_allclose')}")
    check(f"archived real tensors: matcher verdict consistent on {n_pass}/{n_tot} captures",
          n_pass == n_tot)
    return n_tot


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archived", default=None,
                    help="path to paired_boxes_*.pt produced by g3_amp_paired_boxes.py")
    args = ap.parse_args()
    for fn in (case_benign_quantization, case_reorder_and_ties, case_class_flips,
               case_count_changes, case_empty, case_degenerate,
               case_small_and_huge_boxes, case_broken_operator,
               case_conf_drift_and_nan, case_boundaries):
        print(f"--- {fn.__name__}")
        fn()
    arch = Path(args.archived) if args.archived else None
    print("--- case_archived")
    case_archived(arch)
    print(f"SUMMARY {PASS}/{PASS + FAIL} checks PASS")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
