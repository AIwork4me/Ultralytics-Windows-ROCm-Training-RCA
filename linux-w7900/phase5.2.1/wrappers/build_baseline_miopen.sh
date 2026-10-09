#!/usr/bin/env bash
# Leg A (baseline/unpatched) = build_leg_miopen.sh with default dirs.
# Thin wrapper retained so G04 evidence stays reproducible with the same
# entry point after the parameterized refactor.
set -euo pipefail
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$WS/scripts/build_leg_miopen.sh" "$@"
