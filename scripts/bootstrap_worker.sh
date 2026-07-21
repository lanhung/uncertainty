#!/usr/bin/env bash
# Bootstrap a generic Vultr/HPC/AutoDL worker.
set -Eeuo pipefail
umask 077

REPO_URL="${REPO_URL:-git@github.com:lanhung/uncertainty.git}"
REPO_DIR="${REPO_DIR:-/root/uncertainty}"
CONTROL_TAILNET_IP="${CONTROL_TAILNET_IP:-${VULTR_TAILNET_IP:-}}"
CONTROL_PORT="${RESEARCH_OPS_PORT:-8787}"
WORKER_NAME="${WORKER_NAME:-$(hostname)}"
WORKER_ROLE="${WORKER_ROLE:-worker}"
WORKER_INDEX="${WORKER_INDEX:-}"
PERSIST_DIR="${PERSIST_DIR:-/var/lib/research-ops-worker}"
SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

log(){ printf '\n==> %s\n' "$*"; }
die(){ echo "ERROR: $*" >&2; exit 1; }
[ -n "$CONTROL_TAILNET_IP" ] || die "set CONTROL_TAILNET_IP to uq-control-01's Tailscale IPv4"

log "Install minimal worker dependencies"
$SUDO apt-get update -y
$SUDO apt-get install -y python3 git curl ca-certificates

log "Install and join Tailscale"
if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
if ! tailscale ip -4 >/dev/null 2>&1; then
  if [ -n "${TAILSCALE_AUTHKEY:-}" ]; then
    $SUDO tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="$WORKER_NAME"
  else
    echo "Tailscale needs authentication; follow the login URL below."
    $SUDO tailscale up --hostname="$WORKER_NAME"
  fi
fi

log "Clone or refresh repository"
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "$REPO_URL" "$REPO_DIR"
else
  git -C "$REPO_DIR" fetch --all --prune
  git -C "$REPO_DIR" pull --ff-only
fi

TOKEN="${RESEARCH_OPS_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  read -r -s -p "RESEARCH_OPS_TOKEN: " TOKEN
  echo
fi
[ -n "$TOKEN" ] || die "empty token"

log "Persist worker telemetry settings"
mkdir -p "$PERSIST_DIR" "$REPO_DIR/logs"
chmod 700 "$PERSIST_DIR"
cat > "$HOME/.research-ops.env" <<EOF
export RESEARCH_OPS_ENDPOINT="http://${CONTROL_TAILNET_IP}:${CONTROL_PORT}"
export RESEARCH_OPS_TOKEN="${TOKEN}"
export RESEARCH_OPS_OWNER="${WORKER_NAME}"
export RESEARCH_OPS_STATE_DIR="${PERSIST_DIR}"
export RESEARCH_OPS_OUTBOX="${PERSIST_DIR}/outbox"
export RESEARCH_OPS_CHECKPOINT_DIR="${PERSIST_DIR}/checkpoints"
export RESEARCH_OPS_RUN_DIR="${PERSIST_DIR}/runs"
EOF
chmod 600 "$HOME/.research-ops.env"
grep -qF 'source ~/.research-ops.env' "$HOME/.bashrc" 2>/dev/null || \
  echo 'source ~/.research-ops.env' >> "$HOME/.bashrc"
# shellcheck disable=SC1090
source "$HOME/.research-ops.env"

log "Verify control-plane link"
cd "$REPO_DIR"
python taskctl/taskctl.py health
python taskctl/taskctl.py show
if [ -n "$WORKER_INDEX" ]; then
  python taskctl/taskctl.py progress P0-tailnet \
    --current "$((WORKER_INDEX + 1))" --total 3 \
    --message "${WORKER_NAME} joined tailnet" --metric "role=${WORKER_ROLE}"
  python taskctl/taskctl.py start P0-worker-bootstrap --total 2 --unit workers --force || true
  python taskctl/taskctl.py progress P0-worker-bootstrap \
    --current "$WORKER_INDEX" --total 2 \
    --message "${WORKER_NAME} (${WORKER_ROLE}) bootstrapped"
fi

cat <<EOF

Worker ready: ${WORKER_NAME} (${WORKER_ROLE})
Repository:   ${REPO_DIR}
Persistent telemetry/checkpoints: ${PERSIST_DIR}

Example detached task:
  cd ${REPO_DIR}
  nohup python worker/run_with_heartbeat.py \
    --task P0-ops-e2e --total 4 --unit checks --resume \
    -- python -u scripts/ops_demo_job.py --steps 4 \
    > logs/P0-ops-e2e.log 2>&1 &
EOF
