#!/usr/bin/env bash
# Bootstrap a project-scoped AutoDL/HPC/VM worker.
set -Eeuo pipefail
umask 077

PROJECT_SLUG="${RESEARCH_OPS_PROJECT:-uncertainty}"
[[ "$PROJECT_SLUG" =~ ^[a-z0-9][a-z0-9-]{0,47}$ ]] || {
  echo "ERROR: RESEARCH_OPS_PROJECT must match [a-z0-9][a-z0-9-]{0,47}" >&2
  exit 1
}

REPO_URL="${REPO_URL:-https://github.com/lanhung/uncertainty.git}"
REPO_DIR="${REPO_DIR:-/root/${PROJECT_SLUG}}"
CONTROL_TAILNET_IP="${CONTROL_TAILNET_IP:-${VULTR_TAILNET_IP:-}}"
CONTROL_PORT="${RESEARCH_OPS_PORT:-8787}"
CONTROL_ENDPOINT="${RESEARCH_OPS_ENDPOINT:-}"
WORKER_NAME="${WORKER_NAME:-${PROJECT_SLUG}-$(hostname -s)}"
WORKER_ROLE="${WORKER_ROLE:-worker}"
WORKER_INDEX="${WORKER_INDEX:-}"
PERSIST_DIR="${PERSIST_DIR:-/var/lib/research-ops-worker/${PROJECT_SLUG}}"
WORKER_ENV_FILE="${WORKER_ENV_FILE:-${HOME}/.research-ops-${PROJECT_SLUG}.env}"
TAILSCALE_MODE="${TAILSCALE_MODE:-auto}"
TAILSCALE_PROXY_PORT="${TAILSCALE_PROXY_PORT:-1055}"
SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

log(){ printf '\n==> %s\n' "$*"; }
die(){ echo "ERROR: $*" >&2; exit 1; }

case "$TAILSCALE_MODE" in
  auto|kernel|userspace|skip) ;;
  *) die "TAILSCALE_MODE must be auto, kernel, userspace or skip" ;;
esac
if [ -z "$CONTROL_ENDPOINT" ] && [ -z "$CONTROL_TAILNET_IP" ]; then
  die "set CONTROL_TAILNET_IP or an explicit RESEARCH_OPS_ENDPOINT"
fi

log "Install minimal worker dependencies"
$SUDO apt-get update -y
$SUDO apt-get install -y python3 git curl ca-certificates
mkdir -p "$PERSIST_DIR" "$REPO_DIR/logs" "$(dirname "$WORKER_ENV_FILE")"
chmod 700 "$PERSIST_DIR" "$(dirname "$WORKER_ENV_FILE")"

PROXY_EXPORTS=""
if [ "$TAILSCALE_MODE" != "skip" ]; then
  log "Install Tailscale for the ephemeral/replaceable worker"
  if ! command -v tailscale >/dev/null 2>&1; then
    curl -fsSL https://tailscale.com/install.sh | sh
  fi

  if [ "$TAILSCALE_MODE" = "auto" ]; then
    if [ -S /var/run/tailscale/tailscaled.sock ]; then
      TAILSCALE_MODE="kernel"
    elif [ -e /dev/net/tun ] && command -v systemctl >/dev/null 2>&1; then
      $SUDO systemctl enable --now tailscaled >/dev/null 2>&1 || true
      if [ -S /var/run/tailscale/tailscaled.sock ]; then
        TAILSCALE_MODE="kernel"
      else
        TAILSCALE_MODE="userspace"
      fi
    else
      TAILSCALE_MODE="userspace"
    fi
  fi

  if [ "$TAILSCALE_MODE" = "kernel" ]; then
    if ! tailscale ip -4 >/dev/null 2>&1; then
      if [ -n "${TAILSCALE_AUTHKEY:-}" ]; then
        $SUDO tailscale up --auth-key="$TAILSCALE_AUTHKEY" --hostname="$WORKER_NAME"
      else
        echo "Tailscale needs authentication; follow the login URL below."
        $SUDO tailscale up --hostname="$WORKER_NAME"
      fi
    fi
  else
    TS_DIR="${PERSIST_DIR}/tailscale"
    TS_SOCKET="${TS_DIR}/tailscaled.sock"
    TS_PID_FILE="${TS_DIR}/tailscaled.pid"
    TS_LOG="${TS_DIR}/tailscaled.log"
    mkdir -p "$TS_DIR"
    if [ ! -f "$TS_PID_FILE" ] || ! kill -0 "$(cat "$TS_PID_FILE" 2>/dev/null || true)" 2>/dev/null; then
      rm -f "$TS_SOCKET" "$TS_PID_FILE"
      nohup tailscaled \
        --tun=userspace-networking \
        --state=mem: \
        --socket="$TS_SOCKET" \
        --socks5-server="127.0.0.1:${TAILSCALE_PROXY_PORT}" \
        --outbound-http-proxy-listen="127.0.0.1:${TAILSCALE_PROXY_PORT}" \
        > "$TS_LOG" 2>&1 &
      echo $! > "$TS_PID_FILE"
    fi
    for _ in $(seq 1 30); do
      [ -S "$TS_SOCKET" ] && break
      sleep 1
    done
    [ -S "$TS_SOCKET" ] || die "userspace tailscaled did not create ${TS_SOCKET}; inspect ${TS_LOG}"
    if ! tailscale --socket="$TS_SOCKET" ip -4 >/dev/null 2>&1; then
      if [ -n "${TAILSCALE_AUTHKEY:-}" ]; then
        tailscale --socket="$TS_SOCKET" up \
          --auth-key="$TAILSCALE_AUTHKEY" --hostname="$WORKER_NAME"
      else
        echo "Tailscale userspace mode needs authentication; follow the login URL below."
        tailscale --socket="$TS_SOCKET" up --hostname="$WORKER_NAME"
      fi
    fi
    PROXY_EXPORTS="export HTTP_PROXY=\"http://127.0.0.1:${TAILSCALE_PROXY_PORT}\"\nexport HTTPS_PROXY=\"http://127.0.0.1:${TAILSCALE_PROXY_PORT}\"\nexport http_proxy=\"http://127.0.0.1:${TAILSCALE_PROXY_PORT}\"\nexport https_proxy=\"http://127.0.0.1:${TAILSCALE_PROXY_PORT}\"\nexport ALL_PROXY=\"socks5h://127.0.0.1:${TAILSCALE_PROXY_PORT}\""
  fi
fi

if [ -z "$CONTROL_ENDPOINT" ]; then
  CONTROL_ENDPOINT="http://${CONTROL_TAILNET_IP}:${CONTROL_PORT}"
fi

log "Clone or refresh the ${PROJECT_SLUG} repository"
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "$REPO_URL" "$REPO_DIR"
else
  git -C "$REPO_DIR" fetch --all --prune
  git -C "$REPO_DIR" pull --ff-only
fi

TOKEN="${RESEARCH_OPS_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$WORKER_ENV_FILE" ]; then
  TOKEN="$(sed -n 's/^export RESEARCH_OPS_TOKEN="\(.*\)"$/\1/p' "$WORKER_ENV_FILE" | tail -1)"
fi
if [ -z "$TOKEN" ]; then
  read -r -s -p "RESEARCH_OPS_TOKEN for ${PROJECT_SLUG}: " TOKEN
  echo
fi
[ -n "$TOKEN" ] || die "empty token"

log "Persist project-scoped worker telemetry settings"
cat > "$WORKER_ENV_FILE" <<EOF
export RESEARCH_OPS_PROJECT="${PROJECT_SLUG}"
export RESEARCH_OPS_ENDPOINT="${CONTROL_ENDPOINT}"
export RESEARCH_OPS_TOKEN="${TOKEN}"
export RESEARCH_OPS_OWNER="${WORKER_NAME}"
export RESEARCH_OPS_STATE_DIR="${PERSIST_DIR}"
export RESEARCH_OPS_OUTBOX="${PERSIST_DIR}/outbox"
export RESEARCH_OPS_CHECKPOINT_DIR="${PERSIST_DIR}/checkpoints"
export RESEARCH_OPS_RUN_DIR="${PERSIST_DIR}/runs"
${PROXY_EXPORTS}
EOF
chmod 600 "$WORKER_ENV_FILE"
SOURCE_LINE="source ${WORKER_ENV_FILE}"
grep -qF "$SOURCE_LINE" "$HOME/.bashrc" 2>/dev/null || echo "$SOURCE_LINE" >> "$HOME/.bashrc"
# shellcheck disable=SC1090
source "$WORKER_ENV_FILE"

log "Verify the ${PROJECT_SLUG} control-plane link"
cd "$REPO_DIR"
python taskctl/taskctl.py health
python taskctl/taskctl.py show
if [ -n "$WORKER_INDEX" ]; then
  python taskctl/taskctl.py progress P0-tailnet \
    --current "$((WORKER_INDEX + 1))" --total 3 \
    --message "${WORKER_NAME} joined from ${WORKER_ROLE}" --metric "role=${WORKER_ROLE}"
  python taskctl/taskctl.py start P0-worker-bootstrap --total 2 --unit workers --force || true
  python taskctl/taskctl.py progress P0-worker-bootstrap \
    --current "$WORKER_INDEX" --total 2 \
    --message "${WORKER_NAME} (${WORKER_ROLE}) bootstrapped"
fi

cat <<EOF

Worker ready: ${WORKER_NAME} (${WORKER_ROLE})
Project:      ${PROJECT_SLUG}
Repository:   ${REPO_DIR}
Control API:  ${CONTROL_ENDPOINT}
Persistent telemetry/checkpoints: ${PERSIST_DIR}
Environment file: ${WORKER_ENV_FILE}
Tailscale mode: ${TAILSCALE_MODE}

Example detached task:
  cd ${REPO_DIR}
  nohup python worker/run_with_heartbeat.py \
    --task P0-ops-e2e --total 4 --unit checks --resume \
    -- python -u scripts/ops_demo_job.py --steps 4 \
    > logs/P0-ops-e2e.log 2>&1 &
EOF
