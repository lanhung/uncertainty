#!/usr/bin/env bash
# AutoDL specialization for an elastic instance that may serve several projects.
# Project code/scratch use the fast local data disk; durable state uses file storage.
set -Eeuo pipefail

export RESEARCH_OPS_PROJECT="${RESEARCH_OPS_PROJECT:-uncertainty}"
export WORKER_ROLE="${WORKER_ROLE:-${AUTODL_NODE_ROLE:-elastic}}"
export REPO_URL="${REPO_URL:-https://github.com/lanhung/uncertainty.git}"

AUTODL_NODE_NAME="${AUTODL_NODE_NAME:-$(hostname -s)}"
AUTODL_REGION="${AUTODL_REGION:-unknown}"
HOST_STATE_ROOT="${AUTODL_HOST_STATE_ROOT:-/root/autodl-fs/_research-host}"
PERSIST_ROOT="${AUTODL_PERSIST_ROOT:-/root/autodl-fs/projects/${RESEARCH_OPS_PROJECT}}"
SCRATCH_ROOT="${AUTODL_SCRATCH_ROOT:-/root/autodl-tmp/projects/${RESEARCH_OPS_PROJECT}}"

export REPO_DIR="${REPO_DIR:-${SCRATCH_ROOT}/repo}"
export PERSIST_DIR="${PERSIST_DIR:-${PERSIST_ROOT}}"
export WORKER_ENV_FILE="${WORKER_ENV_FILE:-${PERSIST_ROOT}/ops/research-ops.env}"
export TAILSCALE_MODE="${TAILSCALE_MODE:-auto}"
export TAILSCALE_HOSTNAME="${TAILSCALE_HOSTNAME:-${AUTODL_NODE_NAME}}"
export TAILSCALE_STATE_DIR="${TAILSCALE_STATE_DIR:-${HOST_STATE_ROOT}/tailscale}"
export TAILSCALE_PROXY_PORT="${TAILSCALE_PROXY_PORT:-1055}"
export TAILSCALE_EPHEMERAL="${TAILSCALE_EPHEMERAL:-0}"
export AUTO_SOURCE_WORKER_ENV="${AUTO_SOURCE_WORKER_ENV:-0}"
export RESEARCH_WORKER_LOCK_ROOT="${RESEARCH_WORKER_LOCK_ROOT:-/var/lock/research-workers}"

if [ -z "${WORKER_CAPABILITIES:-}" ]; then
  CPU_COUNT="$(nproc 2>/dev/null || echo unknown)"
  MEMORY_GB="$(awk '/MemTotal/ {printf "%.0f", $2/1024/1024}' /proc/meminfo 2>/dev/null || echo unknown)"
  GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || true)"
  GPU_MEMORY="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || true)"
  export WORKER_CAPABILITIES="region=${AUTODL_REGION};cpu=${CPU_COUNT};ram_gb=${MEMORY_GB};gpu=${GPU_NAME:-unknown};gpu_mem_mib=${GPU_MEMORY:-unknown}"
fi

case "$WORKER_ROLE" in
  solver)
    DEFAULT_WORKER_NAME="${RESEARCH_OPS_PROJECT}-${AUTODL_NODE_NAME}-solver"
    ;;
  train|train-verify|verify)
    DEFAULT_WORKER_NAME="${RESEARCH_OPS_PROJECT}-${AUTODL_NODE_NAME}-${WORKER_ROLE}"
    ;;
  *)
    DEFAULT_WORKER_NAME="${RESEARCH_OPS_PROJECT}-${AUTODL_NODE_NAME}-elastic"
    ;;
esac
export WORKER_NAME="${WORKER_NAME:-$DEFAULT_WORKER_NAME}"

mkdir -p \
  "${HOST_STATE_ROOT}/tailscale" \
  "${PERSIST_ROOT}/ops" \
  "${PERSIST_ROOT}/checkpoints" \
  "${PERSIST_ROOT}/outbox" \
  "${PERSIST_ROOT}/runs" \
  "${PERSIST_ROOT}/artifacts" \
  "${PERSIST_ROOT}/manifests" \
  "${SCRATCH_ROOT}" \
  "${RESEARCH_WORKER_LOCK_ROOT}"
chmod 700 "${HOST_STATE_ROOT}" "${PERSIST_ROOT}" "${PERSIST_ROOT}/ops" "${RESEARCH_WORKER_LOCK_ROOT}" 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/bootstrap_worker.sh"
