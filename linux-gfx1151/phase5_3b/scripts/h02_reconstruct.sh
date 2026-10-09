#!/usr/bin/env bash
# Gate H02 — exact R2 source reconstruction on Linux gfx1151.
# Leg A: pristine frozen base 7c58661.
# Leg B: base + exact R2 patches (sha256-verified bytes from the pinned
#        evidence checkout c841716).
# Two independent methods must both land on tree b983cadd:
#   M1: git am 0001 0002 0003
#   M2: git apply --index (3 patches) + git write-tree (in a second worktree)
# No committer-metadata falsification: Linux commit SHAs MAY differ from
# Windows; tree identity is the content anchor.
set -euo pipefail
WS=/home/amd/Desktop/YOLO_AMD/phase5_3b
REPO="$WS/src/upstream.git"
BASE=7c5866144ac4b879be442563e2b49fa1c142ea36
EXPECT_TREE=b983caddf9f9f561e7d1b590deadb16267c2de15
PATCHES="$WS/tmp/r2-evidence-clone/patches/phase5_1_r2/canonical"
cd "$REPO"

report() { echo "[H02] $*"; }

# Blob backfill note: only projects/miopen blobs are local (8032/8032,
# SHA-1-verified via raw backfill); the monorepo's other blobs are absent
# BY DESIGN, so worktrees use cone-mode sparse checkout. Tree verification
# operates on git objects and is unaffected by sparse checkout scope.

add_sparse_worktree() {  # <dir> <base>
  local dir="$1"
  git worktree remove --force "$dir" 2>/dev/null || true
  git worktree add --detach --no-checkout "$dir" "$BASE" >/dev/null 2>&1
  git -C "$dir" sparse-checkout init --cone >/dev/null 2>&1
  git -C "$dir" sparse-checkout set projects/miopen >/dev/null 2>&1
  git -C "$dir" checkout -q "$BASE" 2>/dev/null
}

# ---- Leg A: pristine base worktree --------------------------------------
add_sparse_worktree "$WS/src/legA"
A_TREE=$(git -C "$WS/src/legA" rev-parse 'HEAD^{tree}')
A_HEAD=$(git -C "$WS/src/legA" rev-parse HEAD)
[ "$A_HEAD" = "$BASE" ] || { report "FATAL legA HEAD != base"; exit 3; }
report "legA HEAD=$A_HEAD tree=$A_TREE (pristine, sparse=projects/miopen)"

# ---- Leg B METHOD 1: git am ---------------------------------------------
add_sparse_worktree "$WS/src/legB"
cd "$WS/src/legB"
git -c user.name='phase53b-linux' -c user.email='phase53b@local' \
  am --committer-date-is-author-date \
  "$PATCHES"/0001-*.patch "$PATCHES"/0002-*.patch "$PATCHES"/0003-*.patch \
  > "$WS/logs/h02_git_am.log" 2>&1 || { cat "$WS/logs/h02_git_am.log"; exit 4; }
B_HEAD=$(git rev-parse HEAD)
B_TREE=$(git rev-parse 'HEAD^{tree}')
B_BASE=$(git rev-parse HEAD~3)
report "legB(git am) HEAD=$B_HEAD tree=$B_TREE base=$B_BASE"
[ "$B_TREE" = "$EXPECT_TREE" ] || { report "FATAL M1 tree mismatch"; exit 5; }
[ "$B_BASE" = "$BASE" ] || { report "FATAL M1 parent chain"; exit 6; }
report "METHOD 1 (git am): TREE OK = $EXPECT_TREE"

# subject/order sanity
git log --reverse --format='%s' "$BASE"..HEAD > "$WS/evidence/h02_subjects.txt"
report "subjects recorded"

# ---- Leg B METHOD 2: git apply --index + write-tree ----------------------
# Sparse worktree (same cone as legB): git am already proved sparse-index
# write-tree needs no out-of-cone blobs. A full index would make git greedily
# prefetch every missing monorepo blob (observed, documented in logs).
add_sparse_worktree "$WS/src/legB-m2"
cd "$WS/src/legB-m2"
git apply --index "$PATCHES"/0001-*.patch
git apply --index "$PATCHES"/0002-*.patch
git apply --index "$PATCHES"/0003-*.patch
M2_TREE=$(git write-tree)
git reset -q --hard "$BASE"
git clean -qfd
echo "$M2_TREE" > "$WS/evidence/h02_m2_tree.txt"
report "legB(git apply --index + write-tree) tree=$M2_TREE"
[ "$M2_TREE" = "$EXPECT_TREE" ] || { report "FATAL M2 tree mismatch"; exit 7; }
report "METHOD 2 (git apply --index + write-tree): TREE OK = $EXPECT_TREE"

# ---- changed-file inventory vs base (blob identities) --------------------
git -C "$WS/src/legB" diff --raw "$BASE" HEAD > "$WS/evidence/h02_changed_files_raw.txt"
report "changed files: $(wc -l < "$WS/evidence/h02_changed_files_raw.txt")"

python3 - "$WS" << 'PYEOF'
import json, subprocess, sys, os
WS = sys.argv[1]
def g(*a, cwd=None):
    return subprocess.run(["git"]+list(a), cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
base = "7c5866144ac4b879be442563e2b49fa1c142ea36"
out = {"gate": "H02", "legA_head": g("rev-parse", "HEAD", cwd=f"{WS}/src/legA"),
       "legA_tree": g("rev-parse", "HEAD^{tree}", cwd=f"{WS}/src/legA"),
       "legB_head": g("rev-parse", "HEAD", cwd=f"{WS}/src/legB"),
       "legB_tree": g("rev-parse", "HEAD^{tree}", cwd=f"{WS}/src/legB"),
       "legB_base": g("rev-parse", "HEAD~3", cwd=f"{WS}/src/legB"),
       "m2_tree": open(f"{WS}/evidence/h02_m2_tree.txt").read().strip(),
       "expected_tree": "b983caddf9f9f561e7d1b590deadb16267c2de15",
       "changed_files": {}}
raw = subprocess.run(
    ["git","diff","--raw",base,"HEAD"], cwd=f"{WS}/src/legB", capture_output=True, text=True).stdout
for line in raw.splitlines():
    meta, path = line.split("\t", 1)
    parts = meta.split()
    newsha = parts[3]
    out["changed_files"][path] = newsha
json.dump(out, open(f"{WS}/evidence/source_reconstruction.json","w"), indent=2)
print("[H02] evidence/source_reconstruction.json written,", len(out["changed_files"]), "changed files")
PYEOF

report "DONE"
