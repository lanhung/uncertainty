#!/usr/bin/env bash
# Bootstrap one project-scoped control-plane instance on a shared, always-on
# Vultr host. Tested for Ubuntu/Debian.
set -Eeuo pipefail
umask 077

PROJECT_SLUG="${RESEARCH_OPS_PROJECT:-uncertainty}"
[[ "$PROJECT_SLUG" =~ ^[a-z0-9][a-z0-9-]{0,47}$ ]] || {
  echo "ERROR: RESEARCH_OPS_PROJECT must match [a-z0-9][a-z0-9-]{0,47}" >&2
  exit 1
}

REPO_URL="${REPO_URL:-git@github.com:lanhung/uncertainty.git}"
REPO_DIR="${REPO_DIR:-/root/${PROJECT_SLUG}}"
STATUS_REPO_DIR="${STATUS_REPO_DIR:-/root/${PROJECT_SLUG}-status}"
STATUS_BRANCH="${STATUS_BRANCH:-ops-status}"
ENV_DIR="${RESEARCH_OPS_ENV_DIR:-/etc/research-ops}"
ENV_FILE="${RESEARCH_OPS_ENV_FILE:-${ENV_DIR}/${PROJECT_SLUG}.env}"
STATE_DIR="${RESEARCH_OPS_STATE_DIR:-/var/lib/research-ops/${PROJECT_SLUG}}"
SERVICE_NAME="${RESEARCH_OPS_SERVICE_NAME:-research-ops-${PROJECT_SLUG}}"
PORT="${RESEARCH_OPS_PORT:-8787}"
TAILSCALE_HOSTNAME="${TAILSCALE_HOSTNAME:-research-control-01}"
SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

log(){ printf '\n==> %s\n' "$*"; }
die(){ echo "ERROR: $*" >&2; exit 1; }

if [ -z "${RESEARCH_OPS_PORT:-}" ] && [ -f "$ENV_FILE" ]; then
  EXISTING_PORT="$(sed -n 's/^RESEARCH_OPS_PORT=//p' "$ENV_FILE" | tail -1)"
  if [ -n "$EXISTING_PORT" ]; then PORT="$EXISTING_PORT"; fi
fi
[[ "$PORT" =~ ^[0-9]+$ ]] && [ "$PORT" -ge 1024 ] && [ "$PORT" -le 65535 ] || \
  die "RESEARCH_OPS_PORT must be an integer between 1024 and 65535"

log "Install shared control-host dependencies"
$SUDO apt-get update -y
$SUDO apt-get install -y python3 python3-venv python3-pip git curl ca-certificates iproute2

log "Install and join Tailscale once for the shared Vultr host"
if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
if ! tailscale ip -4 >/dev/null 2>&1; then
  if [ -n "${TAILSCALE_AUTHKEY:-}" ]; then
    $SUDO tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="$TAILSCALE_HOSTNAME"
  else
    echo "Tailscale needs authentication; follow the login URL below."
    $SUDO tailscale up --hostname="$TAILSCALE_HOSTNAME"
  fi
fi
TAILNET_IP="$(tailscale ip -4 | head -1)"
[ -n "$TAILNET_IP" ] || die "no Tailscale IPv4 address available"
echo "shared control-host tailnet IP: $TAILNET_IP"

if command -v ss >/dev/null 2>&1 && \
   ss -H -ltn "sport = :${PORT}" 2>/dev/null | grep -q . && \
   ! $SUDO systemctl is-active --quiet "${SERVICE_NAME}.service"; then
  die "port ${PORT} is already in use; assign a unique RESEARCH_OPS_PORT for ${PROJECT_SLUG}"
fi

log "Clone or refresh the ${PROJECT_SLUG} scientific repository"
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "$REPO_URL" "$REPO_DIR"
else
  git -C "$REPO_DIR" fetch --all --prune
  git -C "$REPO_DIR" pull --ff-only
fi
[ -f "$REPO_DIR/orchestrator/status_server.py" ] || \
  die "research-ops files are missing from $REPO_DIR"

log "Create an isolated Python environment for ${PROJECT_SLUG}"
python3 -m venv "$REPO_DIR/.ops-venv"
"$REPO_DIR/.ops-venv/bin/python" -m pip install --upgrade pip
"$REPO_DIR/.ops-venv/bin/pip" install -r "$REPO_DIR/requirements-ops.txt"

log "Prepare the project-specific status branch clone"
if [ ! -d "$STATUS_REPO_DIR/.git" ]; then
  if git ls-remote --exit-code --heads "$REPO_URL" "$STATUS_BRANCH" >/dev/null 2>&1; then
    git clone --branch "$STATUS_BRANCH" --single-branch "$REPO_URL" "$STATUS_REPO_DIR"
  else
    git clone "$REPO_URL" "$STATUS_REPO_DIR"
    git -C "$STATUS_REPO_DIR" checkout --orphan "$STATUS_BRANCH"
    git -C "$STATUS_REPO_DIR" rm -rf . >/dev/null 2>&1 || true
    find "$STATUS_REPO_DIR" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
    mkdir -p "$STATUS_REPO_DIR/docs" "$STATUS_REPO_DIR/state"
    : > "$STATUS_REPO_DIR/.nojekyll"
    cat > "$STATUS_REPO_DIR/README.md" <<EOF
# Automated research status snapshots for ${PROJECT_SLUG}

This branch is written only by the ${PROJECT_SLUG} research-ops instance.
Source code and scientific decisions live on main. Do not edit generated files manually.
EOF
    git -C "$STATUS_REPO_DIR" add .
    git -C "$STATUS_REPO_DIR" -c user.name=research-ops-bot \
      -c user.email=research-ops@users.noreply.github.com \
      commit -m "ops: initialize ${PROJECT_SLUG} status snapshot branch"
    git -C "$STATUS_REPO_DIR" push -u origin "$STATUS_BRANCH"
  fi
else
  git -C "$STATUS_REPO_DIR" fetch origin "$STATUS_BRANCH"
  git -C "$STATUS_REPO_DIR" checkout "$STATUS_BRANCH"
  git -C "$STATUS_REPO_DIR" pull --ff-only
fi

log "Create a project-specific root-only service environment"
TOKEN="${RESEARCH_OPS_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$ENV_FILE" ]; then
  TOKEN="$(sed -n 's/^RESEARCH_OPS_TOKEN=//p' "$ENV_FILE" | tail -1)"
fi
if [ -z "$TOKEN" ]; then
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
fi
$SUDO mkdir -p "$ENV_DIR" "$STATE_DIR"
$SUDO chmod 700 "$ENV_DIR" "$STATE_DIR"
$SUDO install -m 600 /dev/null "$ENV_FILE"
$SUDO tee "$ENV_FILE" >/dev/null <<EOF
RESEARCH_OPS_PROJECT=$PROJECT_SLUG
RESEARCH_OPS_TOKEN=$TOKEN
RESEARCH_OPS_HOST=0.0.0.0
RESEARCH_OPS_PORT=$PORT
RESEARCH_OPS_ENDPOINT=http://127.0.0.1:$PORT
RESEARCH_OPS_REPO_DIR=$REPO_DIR
RESEARCH_OPS_STATE_DIR=$STATE_DIR
RESEARCH_OPS_SNAPSHOT_REPO=$STATUS_REPO_DIR
EOF

log "Install and start ${SERVICE_NAME}.service"
SERVICE_TMP="$(mktemp)"
PROJECT_SLUG="$PROJECT_SLUG" REPO_DIR="$REPO_DIR" ENV_FILE="$ENV_FILE" \
PYTHON_BIN="$REPO_DIR/.ops-venv/bin/python" \
python3 - "$REPO_DIR/deploy/research-ops.service" "$SERVICE_TMP" <<'PY'
from __future__ import annotations

import os
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = {
    "@PROJECT@": os.environ["PROJECT_SLUG"],
    "@REPO_DIR@": os.environ["REPO_DIR"],
    "@ENV_FILE@": os.environ["ENV_FILE"],
    "@PYTHON@": os.environ["PYTHON_BIN"],
}
for key, value in replacements.items():
    source = source.replace(key, value)
Path(sys.argv[2]).write_text(source, encoding="utf-8")
PY
$SUDO install -m 644 "$SERVICE_TMP" "/etc/systemd/system/${SERVICE_NAME}.service"
rm -f "$SERVICE_TMP"
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now "${SERVICE_NAME}.service"

log "Health check and initial reconciliation"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null; then break; fi
  sleep 1
done
curl -fsS "http://127.0.0.1:${PORT}/healthz" | python3 -m json.tool
cd "$REPO_DIR"
python taskctl/taskctl.py reconcile
python taskctl/taskctl.py start P0-control-plane --total 5 --unit checks --force
python taskctl/taskctl.py done P0-control-plane \
  --message "project-isolated control service, auth, ledger, status branch and health check ready"
python taskctl/taskctl.py start P0-tailnet --total 3 --unit hosts --force
python taskctl/taskctl.py progress P0-tailnet --current 1 --total 3 \
  --message "$(hostname -s) hosts the ${PROJECT_SLUG} control instance"
python taskctl/taskctl.py snapshot || true

cat <<EOF

${PROJECT_SLUG} control-plane instance is ready on the shared Vultr host.

Live dashboard (private tailnet): http://${TAILNET_IP}:${PORT}/
Health:                           http://${TAILNET_IP}:${PORT}/healthz
Systemd service:                  ${SERVICE_NAME}.service
Secret environment:              ${ENV_FILE}  (mode 600)
SQLite state:                     ${STATE_DIR}/state.db
Status branch clone:              ${STATUS_REPO_DIR}
Status branch:                    ${STATUS_BRANCH}

Before bootstrapping AutoDL workers, securely copy RESEARCH_OPS_TOKEN from ${ENV_FILE}.
Do not paste the token into Git, issue comments, screenshots or shell history.

This Vultr host may run other projects, but each project must use a distinct:
  project slug, port, service name, environment file, state directory and status clone.
EOF