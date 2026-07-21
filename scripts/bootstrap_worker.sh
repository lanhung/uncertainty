#!/usr/bin/env bash
# Bootstrap one project namespace on an AutoDL/HPC/VM worker that may also serve
# other projects. Tailscale is host-scoped; telemetry/checkpoints are project-scoped.
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
WORKER_ROLE="${WORKER_ROLE:-elastic}"
WORKER_CAPABILITIES="${WORKER_CAPABILITIES:-}"
WORKER_INDEX="${WORKER_INDEX:-}"
PERSIST_DIR="${PERSIST_DIR:-/var/lib/research-ops-worker/${PROJECT_SLUG}}"
WORKER_ENV_FILE="${WORKER_ENV_FILE:-${HOME}/.research-ops-${PROJECT_SLUG}.env}"
AUTO_SOURCE_WORKER_ENV="${AUTO_SOURCE_WORKER_ENV:-0}"
RESEARCH_WORKER_LOCK_ROOT="${RESEARCH_WORKER_LOCK_ROOT:-/var/lock/research-workers}"

# A physical worker has one Tailscale identity even when several projects use it.
# Persistent state may live on reliable storage, but Unix sockets/PIDs belong on
# a node-local runtime filesystem.
TAILSCALE_MODE="${TAILSCALE_MODE:-auto}"
TAILSCALE_HOSTNAME="${TAILSCALE_HOSTNAME:-$(hostname -s)}"
TAILSCALE_STATE_DIR="${TAILSCALE_STATE_DIR:-${PERSIST_DIR}/tailscale-state}"
TAILSCALE_RUNTIME_DIR="${TAILSCALE_RUNTIME_DIR:-${PERSIST_DIR}/tailscale-runtime}"
TAILSCALE_PROXY_PORT="${TAILSCALE_PROXY_PORT:-1055}"
TAILSCALE_EPHEMERAL="${TAILSCALE_EPHEMERAL:-0}"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

log(){ printf '\n==> %s\n' "$*"; }
die(){ echo "ERROR: $*" >&2; exit 1; }

case "$TAILSCALE_MODE" in
  auto|kernel|userspace|skip) ;;
  *) die "TAILSCALE_MODE must be auto, kernel, userspace or skip" ;;
esac
case "$AUTO_SOURCE_WORKER_ENV" in 0|1) ;; *) die "AUTO_SOURCE_WORKER_ENV must be 0 or 1" ;; esac
case "$TAILSCALE_EPHEMERAL" in 0|1) ;; *) die "TAILSCALE_EPHEMERAL must be 0 or 1" ;; esac
if [ -z "$CONTROL_ENDPOINT" ] && [ -z "$CONTROL_TAILNET_IP" ]; then
  die "set CONTROL_TAILNET_IP or an explicit RESEARCH_OPS_ENDPOINT"
fi

log "Install minimal shared-worker dependencies"
$SUDO apt-get update -y
$SUDO apt-get install -y python3 git curl ca-certificates util-linux
mkdir -p \
  "$PERSIST_DIR" \
  "$(dirname "$WORKER_ENV_FILE")" \
  "$(dirname "$REPO_DIR")" \
  "$RESEARCH_WORKER_LOCK_ROOT"
chmod 700 "$PERSIST_DIR" "$(dirname "$WORKER_ENV_FILE")" "$RESEARCH_WORKER_LOCK_ROOT" 2>/dev/null || true

PROXY_EXPORTS=""
if [ "$TAILSCALE_MODE" != "skip" ]; then
  log "Install or reuse the host-scoped Tailscale connection"
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
        $SUDO tailscale up --auth-key="$TAILSCALE_AUTHKEY" --hostname="$TAILSCALE_HOSTNAME"
      else
        echo "Tailscale needs authentication; follow the login URL below."
        $SUDO tailscale up --hostname="$TAILSCALE_HOSTNAME"
      fi
    fi
  else
    TS_RUNTIME_DIR="$TAILSCALE_RUNTIME_DIR"
    TS_STATE_DIR="$TAILSCALE_STATE_DIR"
    TS_SOCKET="${TS_RUNTIME_DIR}/tailscaled.sock"
    TS_PID_FILE="${TS_RUNTIME_DIR}/tailscaled.pid"
    TS_LOG="${TS_RUNTIME_DIR}/tailscaled.log"
    TS_STATE="${TS_STATE_DIR}/tailscaled.state"
    if [ "$TAILSCALE_EPHEMERAL" = "1" ]; then TS_STATE="mem:"; fi
    mkdir -p "$TS_RUNTIME_DIR" "$TS_STATE_DIR"
    chmod 700 "$TS_RUNTIME_DIR" "$TS_STATE_DIR"

    existing_pid="$(cat "$TS_PID_FILE" 2>/dev/null || true)"
    if [ -z "$existing_pid" ] || ! kill -0 "$existing_pid" 2>/dev/null || [ ! -S "$TS_SOCKET" ]; then
      rm -f "$TS_SOCKET" "$TS_PID_FILE"
      nohup tailscaled \
        --tun=userspace-networking \
        --state="$TS_STATE" \
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
          --auth-key="$TAILSCALE_AUTHKEY" --hostname="$TAILSCALE_HOSTNAME"
      else
        echo "Tailscale userspace mode needs authentication; follow the login URL below."
        tailscale --socket="$TS_SOCKET" up --hostname="$TAILSCALE_HOSTNAME"
      fi
    fi
    PROXY_EXPORTS="$(cat <<EOF
export HTTP_PROXY=\"http://127.0.0.1:${TAILSCALE_PROXY_PORT}\"
export HTTPS_PROXY=\"http://127.0.0.1:${TAILSCALE_PROXY_PORT}\"
export http_proxy=\"http://127.0.0.1:${TAILSCALE_PROXY_PORT}\"
export https_proxy=\"http://127.0.0.1:${TAILSCALE_PROXY_PORT}\"
export ALL_PROXY=\"socks5h://127.0.0.1:${TAILSCALE_PROXY_PORT}\"
EOF
)"
  fi
fi

if [ -z "$CONTROL_ENDPOINT" ]; then
  CONTROL_ENDPOINT="http://${CONTROL_TAILNET_IP}:${CONTROL_PORT}"
fi

log "Clone or refresh the ${PROJECT_SLUG} repository namespace"
if [ ! -d "$REPO_DIR/.git" ]; then
  if [ -e "$REPO_DIR" ] && [ -n "$(find "$REPO_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
    die "$REPO_DIR exists and is not an empty Git repository"
  fi
  git clone "$REPO_URL" "$REPO_DIR"
else
  git -C "$REPO_DIR" fetch --all --prune
  git -C "$REPO_DIR" pull --ff-only
fi
mkdir -p "$REPO_DIR/logs"

TOKEN="${RESEARCH_OPS_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$WORKER_ENV_FILE" ]; then
  TOKEN="$(sed -n 's/^export RESEARCH_OPS_TOKEN="\(.*\)"$/\1/p' "$WORKER_ENV_FILE" | tail -1)"
fi
if [ -z "$TOKEN" ]; then
  read -r -s -p "RESEARCH_OPS_TOKEN for ${PROJECT_SLUG}: " TOKEN
  echo
fi
[ -n "$TOKEN" ] || die "empty token"

log "Persist only this project's telemetry and checkpoint settings"
cat > "$WORKER_ENV_FILE" <<EOF
export RESEARCH_OPS_PROJECT="${PROJECT_SLUG}"
export RESEARCH_OPS_ENDPOINT="${CONTROL_ENDPOINT}"
export RESEARCH_OPS_TOKEN="${TOKEN}"
export RESEARCH_OPS_OWNER="${WORKER_NAME}"
export RESEARCH_OPS_WORKER_ROLE="${WORKER_ROLE}"
export RESEARCH_OPS_WORKER_CAPABILITIES="${WORKER_CAPABILITIES}"
export RESEARCH_OPS_STATE_DIR="${PERSIST_DIR}"
export RESEARCH_OPS_OUTBOX="${PERSIST_DIR}/outbox"
export RESEARCH_OPS_CHECKPOINT_DIR="${PERSIST_DIR}/checkpoints"
export RESEARCH_OPS_RUN_DIR="${PERSIST_DIR}/runs"
export RESEARCH_WORKER_LOCK_ROOT="${RESEARCH_WORKER_LOCK_ROOT}"
${PROXY_EXPORTS}
EOF
chmod 600 "$WORKER_ENV_FILE"

# Shared workers must not globally source every project's token. Explicit source
# is the default; AUTO_SOURCE_WORKER_ENV=1 is reserved for a dedicated worker.
if [ "$AUTO_SOURCE_WORKER_ENV" = "1" ]; then
  SOURCE_LINE="source ${WORKER_ENV_FILE}"
  grep -qF "$SOURCE_LINE" "$HOME/.bashrc" 2>/dev/null || echo "$SOURCE_LINE" >> "$HOME/.bashrc"
fi
# shellcheck disable=SC1090
source "$WORKER_ENV_FILE"

log "Verify the ${PROJECT_SLUG} control-plane link"
cd "$REPO_DIR"
python taskctl/taskctl.py health
python taskctl/taskctl.py show
if [ -n "$WORKER_INDEX" ]; then
  python taskctl/taskctl.py progress P0-tailnet \
    --current "$((WORKER_INDEX + 1))" --total 3 \
    --message "${WORKER_NAME} joined as elastic role=${WORKER_ROLE}"
  python taskctl/taskctl.py start P0-worker-bootstrap --total 2 --unit workers --force || true
  python taskctl/taskctl.py progress P0-worker-bootstrap \
    --current "$WORKER_INDEX" --total 2 \
    --message "${WORKER_NAME} role=${WORKER_ROLE}; ${WORKER_CAPABILITIES:-capabilities-not-recorded}"
fi

cat <<EOF

Worker project namespace ready: ${WORKER_NAME}
Project:       ${PROJECT_SLUG}
Logical role:  ${WORKER_ROLE} (may change between tasks)
Repository:    ${REPO_DIR}
Control API:   ${CONTROL_ENDPOINT}
Persistent project state/checkpoints: ${PERSIST_DIR}
Environment file: ${WORKER_ENV_FILE}
Tailscale host identity: ${TAILSCALE_HOSTNAME}
Tailscale mode: ${TAILSCALE_MODE}
Tailscale persistent state: ${TAILSCALE_STATE_DIR}
Tailscale local runtime: ${TAILSCALE_RUNTIME_DIR}
Cross-project lock root: ${RESEARCH_WORKER_LOCK_ROOT}

Activate this project explicitly in each shell:
  source ${WORKER_ENV_FILE}

Do not add every project env file to .bashrc on a shared AutoDL instance.
Use scripts/with_resource_lease.sh before exclusive GPU or CPU-heavy work.
EOF
