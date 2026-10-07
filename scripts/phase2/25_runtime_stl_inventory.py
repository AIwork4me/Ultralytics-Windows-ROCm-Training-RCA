"""Gate 31 reproduction: compute the quoted-include closure and std usage
of an extracted MIOpen kernel tree (captured with AMD_COMGR_SAVE_TEMPS=1
and cache-isolated run). Usage: python 25_runtime_stl_inventory.py <tree>
(tree = dir containing <Kernel>.cpp and include/)."""
import os, re, sys, json
tree = sys.argv[1]
root = sys.argv[2] if len(sys.argv) > 2 else "MIOpenBatchNormFwdTrainSpatial.cpp"
rootp = os.path.join(tree, root)
def qi(p):
    t = open(p, encoding="utf-8", errors="replace").read()
    return (re.findall(r'#include\s+"([^"]+)"', t),
            re.findall(r'#include\s+<([^>]+)>', t))
seen, angle = set(), []
stack = [rootp]
while stack:
    p = stack.pop()
    if p in seen: continue
    seen.add(p)
    q, a = qi(p); angle += a
    for n in q:
        c = os.path.join(tree, "include", n)
        if os.path.exists(c): stack.append(c)
agg = {}
for p in seen:
    t = open(p, encoding="utf-8", errors="replace").read()
    for i in set(re.findall(r"std::[a-zA-Z_0-9]+", t)): agg[i] = agg.get(i, 0) + 1
print(json.dumps({
    "closure": sorted(os.path.basename(p) for p in seen),
    "non_hip_angle_includes": sorted({a for a in angle if not a.startswith("hip")}),
    "std_usage": dict(sorted(agg.items(), key=lambda x: -x[1])),
}, indent=2))
