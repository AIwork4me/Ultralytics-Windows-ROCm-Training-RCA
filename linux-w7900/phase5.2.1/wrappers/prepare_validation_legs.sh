#!/usr/bin/env bash
# prepare_validation_legs.sh — build/clean the two MIOpen validation legs
# for the final Phase-5.1 A/B validation.
#
#   LEG A = UNPATCHED source-built MIOpen (baseline)
#   LEG B = FINAL Phase-5.1 PATCHED source-built MIOpen (NOT AUTHORIZED YET)
#
# Single-variable discipline: same frozen upstream base SHA, same GPU,
# same driver, same 7.14.1 wheel toolchain, same CMake flags, same harness,
# same inputs, same tolerances. The ONLY difference: the patch series.
#
# Usage:
#   prepare_validation_legs.sh preflight          # readiness check only
#   prepare_validation_legs.sh leg-a              # (re)build unpatched leg
#   prepare_validation_legs.sh leg-b <handoff.json>  # post-freeze only
#
# leg-b refuses to run unless the handoff manifest passes
# check_final_handoff.py --check-only.
set -euo pipefail

WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-preflight}"
REPO="$WS/repos/rocm-libraries"
SRC_PRISTINE="$WS/source/upstream-pristine"
SRC_B="$WS/source/final-patched"

fail() { echo "FATAL: $*" >&2; exit 3; }

check_git() {
  [ -d "$REPO/.git" ] || fail "no git repo at $REPO"
  git -C "$REPO" status --porcelain | head -3
}

verify_library() { # <leg>
  local leg="$1" inst="$WS/install/$leg" lib="$WS/install/$leg/lib/libMIOpen.so.1"
  [ -e "$lib" ] || fail "leg $leg: $lib missing"
  local sha; sha=$(sha256sum "$lib" | cut -d' ' -f1)
  echo "leg $leg libMIOpen.so.1 sha256=$sha"
  python3 - "$leg" "$inst" "$sha" <<'PYEOF'
import json, sys, datetime
leg, inst, sha = sys.argv[1:4]
WS = "/workspace/miopen-w7900-validation"
rec = {"leg": leg, "install": inst, "libMIOpen_sha256": sha,
       "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
p = f"{WS}/evidence/G07_library_sha256.json"
try: d = json.load(open(p))
except Exception: d = {}
d[leg] = rec
json.dump(d, open(p, "w"), indent=2)
PYEOF
}

leg_a() {
  local frozen_sha="${2:-}"
  echo "== LEG A: unpatched source build =="
  # WARNING (B11 Reviewer C M-1): this mode builds into install/baseline —
  # the HISTORICAL b68f894 preflight leg. The FINAL frozen-base Leg A lives
  # at install/legA-frozen-baseline via the runbook's re-materialization
  # block (phase5_2/docs/FINAL_AB_VALIDATION_RUNBOOK.md). Do NOT use this
  # mode for the final A/B mission.
  check_git
  if [ -n "$frozen_sha" ]; then
    # G10 Reviewer C M-1 fix: reconstruct leg-A source at the FROZEN sha
    # (mirrors leg-b discipline; forbids silently rebuilding the historical
    # anchor b68f894 when the final handoff pins a different base).
    local target="$SRC_PRISTINE"
    if ! git -C "$REPO" cat-file -e "${frozen_sha}^{commit}" 2>/dev/null; then
      fail "frozen SHA $frozen_sha not present in $REPO - fetch it first (network retry loops in scripts/)"
    fi
    if [ -e "$target/.git" ] || [ -n "$(ls -A "$target" 2>/dev/null)" ]; then
      # replace the prep-time tarball tree with a clean worktree
      rm -rf "$target"
    fi
    git -C "$REPO" worktree add --detach "$target" "$frozen_sha"
    git -C "$target" status --porcelain | grep -q . && fail "leg-A worktree not clean"
    echo "leg-A source reconstructed at frozen sha $frozen_sha"
  else
    echo "WARNING: no frozen sha supplied; building source/upstream-pristine as-is (prep anchor b68f894). The FINAL run MUST pass the frozen sha."
  fi
  MIOPEN_SOURCE="$WS/source/upstream-pristine/projects/miopen" \
  MIOPEN_BUILD="$WS/build/baseline-miopen" \
  MIOPEN_INSTALL="$WS/install/baseline" \
    bash "$WS/scripts/build_leg_miopen.sh"
  verify_library baseline
}

leg_b() {
  local handoff="${2:-}"
  [ -n "$handoff" ] || fail "leg-b requires the FINAL_HANDOFF.json path"
  echo "== LEG B: patched source build (post-freeze only) =="
  # 1. verify manifest strictly, byte-exact hashes, no side effects.
  #    Pinned RCA evidence checkout (phase5_2): repos/rca-evidence at the
  #    frozen evidence commit 494907699f3b... (override with RCA_REPO_ROOT /
  #    RCA_EVIDENCE_SHA env only for the authorized final-validation mission).
  local rca_root="${RCA_REPO_ROOT:-$WS/repos/rca-evidence}"
  local ev_sha="${RCA_EVIDENCE_SHA:-494907699f3b57095663f0a70b42278001a8efb7}"
  python3 "$WS/scripts/check_final_handoff.py" --check-only "$handoff" \
    --rca-root "$rca_root" --rca-evidence-sha "$ev_sha" \
    || fail "handoff manifest failed check-only; LEG B refused"
  # 2. reconstruct patched tree in a clean worktree via the consumer
  python3 "$WS/scripts/check_final_handoff.py" --apply "$handoff" "$SRC_B" \
    --rca-root "$rca_root" --rca-evidence-sha "$ev_sha" \
    || fail "patched-tree reconstruction failed; LEG B refused"
  # 3. assert B directories are the reconstructed tree only
  [ -f "$SRC_B/projects/miopen/src/kernels/radix.hpp" ] \
    || fail "reconstructed tree incomplete"
  # 4. build with the IDENTICAL flags as leg A (same script, different dirs)
  MIOPEN_SOURCE="$SRC_B/projects/miopen" MIOPEN_BUILD="$WS/build/patched-miopen" \
  MIOPEN_INSTALL="$WS/install/patched" bash "$WS/scripts/build_leg_miopen.sh"
  verify_library patched
}

preflight() {
  echo "== A/B leg readiness preflight =="
  local ok=0
  # Leg A readiness
  if [ -e "$WS/install/baseline/lib/libMIOpen.so.1" ]; then
    echo "[A] install/baseline ready: $(sha256sum "$WS/install/baseline/lib/libMIOpen.so.1" | cut -d' ' -f1)"
  else echo "[A] MISSING baseline install"; ok=1; fi
  if [ -d "$WS/build/baseline-miopen" ] && grep -q "MIOPEN_USE_HIPRTC:BOOL=ON" "$WS/build/baseline-miopen/CMakeCache.txt"; then
    echo "[A] build dir configured HIPRTC=ON gfx1100"
  else echo "[A] build dir not configured"; ok=1; fi
  # Leg B reservation: MUST be empty of patches/sources now
  b_files=$(find "$SRC_B" "$WS/build/patched-miopen" "$WS/install/patched" -mindepth 1 2>/dev/null | wc -l)
  if [ "$b_files" -eq 0 ]; then
    echo "[B] patched source/build/install dirs EMPTY (correctly reserved)"
  else
    echo "[B] RESERVED DIRS NOT EMPTY ($b_files entries) - FINAL CANDIDATE MUST WIPE+RECONSTRUCT"; ok=1
  fi
  # Cache isolation
  for d in baseline-cache patched-cache; do
    [ -d "$WS/runtime/$d" ] && echo "[cache] runtime/$d isolated" || { mkdir -p "$WS/runtime/$d"; echo "[cache] runtime/$d created"; }
  done
  # Scripts executable
  for s in build_baseline_miopen.sh run_validation_leg.sh check_final_handoff.py env_rocm7141.sh env_system721.sh; do
    [ -x "$WS/scripts/$s" ] && echo "[script] $s executable" || { echo "[script] $s NOT executable"; ok=1; }
  done
  # Git repo usable for worktrees
  if git -C "$REPO" cat-file -e "$(git -C "$REPO" rev-parse HEAD)" 2>/dev/null; then
    echo "[git] repo present, HEAD=$(git -C "$REPO" rev-parse --short HEAD)"
  else echo "[git] repo not ready (backfill still running?)"; ok=1; fi
  if [ "$ok" -eq 0 ]; then echo "PREFLIGHT: READY"; else echo "PREFLIGHT: INCOMPLETE"; exit 1; fi
}

case "$MODE" in
  preflight) preflight ;;
  leg-a) leg_a "$@" ;;
  leg-b) leg_b "$@" ;;
  *) fail "usage: $0 {preflight|leg-a [frozen_sha]|leg-b <handoff.json>}" ;;
esac
