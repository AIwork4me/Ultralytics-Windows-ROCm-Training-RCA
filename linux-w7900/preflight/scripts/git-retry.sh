#!/bin/bash
# Retry wrapper for git network ops through flaky proxy. Usage: git-retry.sh <git args...>
TRIES=${GIT_RETRY_TRIES:-10}
for i in $(seq 1 "$TRIES"); do
  if git "$@" 2>&1; then exit 0; fi
  echo "[git-retry] attempt $i/$TRIES failed, sleeping..." >&2
  sleep $(( (i % 5 + 1) * 10 ))
done
echo "[git-retry] FAILED after $TRIES attempts" >&2
exit 1
# G03 note: wrapper copied from /workspace bootstrap; retries git ops through
# flaky egress proxy (CONNECT 503 intermittent). Use for ALL git network ops.
