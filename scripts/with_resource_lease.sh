#!/usr/bin/env bash
# Serialize exclusive resources on an AutoDL instance shared by several projects.
# The lock is host-local and intentionally outside any one repository.
set -Eeuo pipefail
umask 077

RESOURCE=""
PROJECT="${RESEARCH_OPS_PROJECT:-unknown-project}"
TASK="${RESEARCH_OPS_TASK_ID:-manual}"
WAIT_SECONDS=0
LOCK_ROOT="${RESEARCH_WORKER_LOCK_ROOT:-/var/lock/research-workers}"

usage() {
  cat <<'EOF'
Usage:
  scripts/with_resource_lease.sh \
    --resource <gpu0|cpu-heavy|io-heavy|custom-name> \
    [--project NAME] [--task TASK_ID] [--wait SECONDS] -- COMMAND [ARG...]

Examples:
  scripts/with_resource_lease.sh --resource gpu0 --project uncertainty \
    --task P4-train -- python worker/run_with_heartbeat.py ...

  scripts/with_resource_lease.sh --resource cpu-heavy --wait 300 -- make benchmark

Exit code 75 means another project currently owns the requested resource.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --resource)
      RESOURCE="${2:-}"
      shift 2
      ;;
    --project)
      PROJECT="${2:-}"
      shift 2
      ;;
    --task)
      TASK="${2:-}"
      shift 2
      ;;
    --wait)
      WAIT_SECONDS="${2:-}"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[ -n "$RESOURCE" ] || { echo "--resource is required" >&2; exit 2; }
[[ "$RESOURCE" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ ]] || {
  echo "invalid resource name: $RESOURCE" >&2
  exit 2
}
[[ "$WAIT_SECONDS" =~ ^[0-9]+$ ]] || {
  echo "--wait must be a non-negative integer" >&2
  exit 2
}
[ "$#" -gt 0 ] || { echo "a command is required after --" >&2; exit 2; }
command -v flock >/dev/null 2>&1 || {
  echo "flock is required; install the util-linux package" >&2
  exit 1
}

mkdir -p "$LOCK_ROOT"
chmod 700 "$LOCK_ROOT" 2>/dev/null || true
LOCK_FILE="${LOCK_ROOT}/${RESOURCE}.lock"
META_FILE="${LOCK_ROOT}/${RESOURCE}.json"

exec 9>"$LOCK_FILE"
if ! flock -w "$WAIT_SECONDS" 9; then
  echo "resource '${RESOURCE}' is already leased" >&2
  if [ -f "$META_FILE" ]; then
    cat "$META_FILE" >&2
  fi
  exit 75
fi

LEASE_ID="$(python3 -c 'import secrets; print(secrets.token_hex(12))')"
python3 - "$META_FILE" "$LEASE_ID" "$RESOURCE" "$PROJECT" "$TASK" "$$" "$@" <<'PY'
from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "lease_id": sys.argv[2],
    "resource": sys.argv[3],
    "project": sys.argv[4],
    "task": sys.argv[5],
    "wrapper_pid": int(sys.argv[6]),
    "hostname": socket.gethostname(),
    "started_at": datetime.now(timezone.utc).isoformat(),
    "command": sys.argv[7:],
}
temporary = path.with_suffix(".tmp")
temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.chmod(temporary, 0o600)
temporary.replace(path)
PY

cleanup() {
  if [ -f "$META_FILE" ] && grep -q "$LEASE_ID" "$META_FILE" 2>/dev/null; then
    rm -f "$META_FILE"
  fi
}
trap cleanup EXIT HUP INT TERM

printf 'lease-acquired resource=%s project=%s task=%s lease_id=%s\n' \
  "$RESOURCE" "$PROJECT" "$TASK" "$LEASE_ID"

set +e
"$@"
status=$?
set -e
printf 'lease-released resource=%s project=%s task=%s exit=%s\n' \
  "$RESOURCE" "$PROJECT" "$TASK" "$status"
exit "$status"
