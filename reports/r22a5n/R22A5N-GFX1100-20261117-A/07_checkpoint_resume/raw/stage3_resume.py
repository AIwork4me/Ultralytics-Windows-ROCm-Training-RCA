
from ultralytics import YOLO
import pathlib, torch
last = pathlib.Path(r"C:\r22a5n1100\g5work\runs\lifecycle\weights\last.pt")
assert last.is_file(), "last.pt missing: " + str(last)
m = YOLO(str(last))
obs = {"effective": 0, "attempts": 0, "state_entries": None, "opt_class": None,
       "start_epoch": None}

def on_train_start(trainer):
    opt = trainer.optimizer
    obs["opt_class"] = type(opt).__name__
    obs["state_entries"] = len(getattr(opt, "state", {}) or {})
    obs["start_epoch"] = int(getattr(trainer, "start_epoch", -1))
    print("RESUME_OPTIMIZER class=%s state_entries=%s start_epoch=%s" %
          (obs["opt_class"], obs["state_entries"], obs["start_epoch"]))
    live = {n: p for n, p in trainer.model.named_parameters()}
    id2name = {id(p): n for n, p in live.items()}
    sents = {}
    for gi, group in enumerate(opt.param_groups):
        cands = sorted(((p.numel(), j, id2name.get(id(p), f"u[{gi}:{j}]"))
                        for j, p in enumerate(group["params"])), key=lambda t: t[0])
        for _, _, n in cands[:2]:
            sents[f"g{gi}:{n}"] = live.get(n)
    before = {k: v.detach().clone() for k, v in sents.items() if v is not None}
    orig = opt.step
    def counting_step(*a, **kw):
        obs["attempts"] += 1
        r = orig(*a, **kw)
        moved = max(float((v.detach() - before[k]).abs().max().item())
                    for k, v in sents.items() if k in before)
        if moved > 0.0:
            obs["effective"] += 1
        for k, v in sents.items():
            before[k] = v.detach().clone()
        return r
    opt.step = counting_step

def on_train_end(trainer):
    print("RESUME_EFFECTIVE_UPDATES attempts=%s effective=%s" %
          (obs["attempts"], obs["effective"]))

m.add_callback("on_train_start", on_train_start)
m.add_callback("on_train_end", on_train_end)
r = m.train(resume=True)
print("RESUME_DONE")
