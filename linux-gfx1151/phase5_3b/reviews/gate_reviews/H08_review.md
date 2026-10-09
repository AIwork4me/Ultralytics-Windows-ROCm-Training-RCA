# H08 review — optional YOLO smoke

Executed with in-process provenance assertion (path + sha256 of legB R2
libMIOpen b14e907a...) BEFORE any training; assert-based, so a wrong binding
would have aborted. 1 epoch coco8 amp=False, then val with trained weights;
TRAIN_COMPLETE + VAL_COMPLETE; last.pt sha256 40ae9450... recorded. Metrics
mAP50 0.943 consistent with a 1-epoch coco8 overfit smoke (non-goal:
accuracy claims). Fresh isolated MIOpen cache. No ROCm stack changes were
made for this optional gate. (Independent subagent review deferred to the
H10 panel's runtime reviewer, which re-examines the binding proof; the gate
is optional per mission.)
