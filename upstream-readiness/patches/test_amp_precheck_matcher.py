"""Tests for the AMP precheck geometric matcher (_amp_detections_equivalent).

CPU-only, no GPU required: covers benign fp16 coordinate quantization,
detection reordering, NMS ties, class flips, missing/extra detections,
empty predictions, degenerate boxes, scale-sensitive absolute drift on
large boxes, confidence drift, NaN/Inf and a genuinely broken AMP operator.
Mirrors ultralytics repo test style (pytest, plain asserts).
"""

import pytest
import torch

from ultralytics.utils.checks import _amp_detections_equivalent

BASE = [
    [100.0, 120.0, 180.0, 240.0, 0.90, 5.0],
    [300.0, 320.0, 420.0, 460.0, 0.80, 0.0],
    [50.0, 60.0, 90.0, 130.0, 0.70, 2.0],
]


def _t(rows):
    return torch.tensor(rows, dtype=torch.float32)


def _shift(rows, dx, dy=0.0):
    return [[x1 + dx, y1 + dy, x2 + dx, y2 + dy, c, k] for x1, y1, x2, y2, c, k in rows]


@pytest.mark.parametrize("drift", [0.1, 0.4, 0.76])
def test_benign_fp16_quantization_passes(drift):
    """fp16 coordinate noise up to the largest observed real drift (0.76 px
    at imgsz 640) must NOT disable AMP — this is the check_amp design flaw."""
    assert _amp_detections_equivalent(_t(BASE), _t(_shift(BASE, drift)), imgsz=640)


def test_reordered_detections_pass():
    b = _t([BASE[2], BASE[0], BASE[1]])
    assert _amp_detections_equivalent(_t(BASE), b, imgsz=640)


def test_nms_tie_reordering_passes():
    tie = [[50.0, 50.0, 150.0, 150.0, 0.80, 1.0], [200.0, 200.0, 300.0, 300.0, 0.80, 1.0]]
    assert _amp_detections_equivalent(_t(tie), _t([tie[1], tie[0]]), imgsz=640)


def test_class_flip_fails():
    flipped = [row[:] for row in BASE]
    flipped[1][5] = 7.0
    assert not _amp_detections_equivalent(_t(BASE), _t(flipped), imgsz=640)


def test_count_mismatch_fails():
    assert not _amp_detections_equivalent(_t(BASE), _t(BASE[:2]), imgsz=640)
    extra = BASE + [[500.0, 500.0, 560.0, 560.0, 0.6, 4.0]]
    assert not _amp_detections_equivalent(_t(BASE), _t(extra), imgsz=640)


def test_empty_predictions():
    empty = torch.zeros(0, 6)
    assert _amp_detections_equivalent(empty, empty.clone(), imgsz=640)
    assert not _amp_detections_equivalent(empty, _t(BASE), imgsz=640)
    assert not _amp_detections_equivalent(_t(BASE), empty, imgsz=640)


def test_non_finite_fails():
    b = _t(BASE)
    b[0, 4] = float("nan")
    assert not _amp_detections_equivalent(_t(BASE), b, imgsz=640)
    a = _t(BASE)
    a[1, 2] = float("inf")
    assert not _amp_detections_equivalent(a, _t(BASE), imgsz=640)


def test_degenerate_box_fails():
    degenerate = [[100.0, 100.0, 100.0, 200.0, 0.9, 1.0]]
    assert not _amp_detections_equivalent(_t(degenerate), _t(degenerate), imgsz=640)


def test_small_box_1px_shift_fails_via_iou():
    """A 1 px shift on an 8 px box gives IoU ~0.56 — must fail despite the
    1 px absolute floor (no permissiveness for tiny boxes)."""
    tiny = [[100.0, 100.0, 108.0, 108.0, 0.9, 1.0]]
    shifted = [[101.0, 100.0, 109.0, 108.0, 0.9, 1.0]]
    assert not _amp_detections_equivalent(_t(tiny), _t(shifted), imgsz=640)


def test_large_box_absolute_drift_fails():
    """10 px shift on a 600 px box passes IoU (~0.97) but must fail the
    scale-sensitive absolute bound — no concealment of large absolute
    errors on huge boxes."""
    huge = [[20.0, 20.0, 620.0, 620.0, 0.9, 1.0]]
    shifted = [[30.0, 20.0, 630.0, 620.0, 0.9, 1.0]]
    assert not _amp_detections_equivalent(_t(huge), _t(shifted), imgsz=640)


def test_confidence_drift_threshold():
    drifted = [row[:] for row in BASE]
    drifted[0][4] += 0.0043  # largest observed benign fp16 conf delta
    assert _amp_detections_equivalent(_t(BASE), _t(drifted), imgsz=640)
    drifted[0][4] += 0.06
    assert not _amp_detections_equivalent(_t(BASE), _t(drifted), imgsz=640)


def test_broken_amp_operator_fails():
    """A genuinely broken AMP operator displaces everything — must be caught."""
    assert not _amp_detections_equivalent(_t(BASE), _t(_shift(BASE, 30.0)), imgsz=640)


def test_imgsz_scales_floor():
    """The absolute floor scales with inference size (1 px @ 640)."""
    a = _t([[100.0, 100.0, 200.0, 200.0, 0.9, 1.0]])
    b = _t([[101.6, 100.0, 201.6, 200.0, 0.9, 1.0]])  # 1.6 px @ imgsz 1280 (floor 2 px)
    assert _amp_detections_equivalent(a, b, imgsz=1280)
