#!/usr/bin/env bash
# AutoDL specialization of the generic worker bootstrap.
set -Eeuo pipefail

export RESEARCH_OPS_PROJECT="${RESEARCH_OPS_PROJECT:-uncertainty}"
export WORKER_ROLE="${WORKER_ROLE:-${AUTODL_NODE_ROLE:-worker}}"
export REPO_URL="${REPO_URL:-https://github.com/lanhung/uncertainty.git}"
export REPO_DIR="${REPO_DIR:-/root/${RESEARCH_OPS_PROJECT}}"

PERSIST_ROOT="${AUTODL_PERSIST_ROOT:-/root/autodl-fs/${RESEARCH_OPS_PROJECT}}"
export PERSIST_DIR="${PERSIST_DIR:-${PERSIST_ROOT}/ops}"
export WORKER_ENV_FILE="${WORKER_ENV_FILE:-${PERSIST_ROOT}/ops/research-ops.env}"
export TAILSCALE_MODE="${TAILSCALE_MODE:-auto}"

case "$WORKER_ROLE" in
  solver)
    DEFAULT_WORKER_NAME="${RESEARCH_OPS_PROJECT}-sim-autodl-$(hostname -s)"
    ;;
  train|train-verify|verify)
    DEFAULT_WORKER_NAME="${RESEARCH_OPS_PROJECT}-train-autodl-$(hostname -s)"
    ;;
  *)
    DEFAULT_WORKER_NAME="${RESEARCH_OPS_PROJECT}-autodl-$(hostname -s)"
    ;;
esac
export WORKER_NAME="${WORKER_NAME:-$DEFAULT_WORKER_NAME}"

mkdir -p \
  "${PERSIST_ROOT}/ops" \
  "${PERSIST_ROOT}/checkpoints" \
  "${PERSIST_ROOT}/artifacts" \
  "/root/autodl-tmp/${RESEARCH_OPS_PROJECT}"
chmod 700 "${PERSIST_ROOT}/ops"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/bootstrap_worker.sh"
