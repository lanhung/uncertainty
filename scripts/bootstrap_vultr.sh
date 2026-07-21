#!/usr/bin/env bash
# Bootstrap the always-on Vultr control plane. Tested for Ubuntu/Debian.
set -Eeuo pipefail
umask 077

REPO_URL="${REPO_URL:-git@github.com:lanhung/uncertainty.git}"
REPO_DIR="${REPO_DIR:-/root/uncertainty}"
STATUS_REPO_DIR="${STATUS_REPO_DIR:-/root/uncertainty-status}"
STATUS_BRANCH="${STATUS_BRANCH:-ops-status}"
PORT="${RESEARCH_OPS_PORT:-8787}"
ENV_FILE="${RESEARCH_OPS_ENV_FILE:-/etc/research-ops.env}"
TAILSCALE_HOSTNAME="${TAILSCALE_HOSTNAME:-uq-control-01}"
SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

log(){ printf '\n==> %s\n' "$*"; }
die(){ echo "ERROR: $*" >&2; exit 1; }

log "Install control-plane dependencies"
$SUDO apt-get update -y
$SUDO apt-get install -y python3 python3-venv python3-pip git curl ca-certificates

log "Install and join Tailscale"
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
echo "tailnet IP: $TAILNET_IP"

log "Clone or refresh the scientific repository"
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "$REPO_URL" "$REPO_DIR"
else
  git -C "$REPO_DIR" fetch --all --prune
  git -C "$REPO_DIR" pull --ff-only
fi
[ -f "$REPO_DIR/orchestrator/status_server.py" ] || die "research-ops files are missing from $REPO_DIR"

log "Create isolated Python environment"
python3 -m venv "$REPO_DIR/.ops-venv"
"$REPO_DIR/.ops-venv/bin/python" -m pip install --upgrade pip
"$REPO_DIR/.ops-venv/bin/pip" install -r "$REPO_DIR/requirements-ops.txt"

log "Prepare dedicated status branch clone"
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
    cat > "$STATUS_REPO_DIR/README.md" <<'EOF'
# Automated research status snapshots

This branch is written only by the research-ops control plane. Source code and
scientific decisions live on `main`. Do not edit generated files manually.
EOF
    git -C "$STATUS_REPO_DIR" add .
    git -C "$STATUS_REPO_DIR" -c user.name=research-ops-bot \
      -c user.email=research-ops@users.noreply.github.com \
      commit -m "ops: initialize status snapshot branch"
    git -C "$STATUS_REPO_DIR" push -u origin "$STATUS_BRANCH"
  fi
else
  git -C "$STATUS_REPO_DIR" fetch origin "$STATUS_BRANCH"
  git -C "$STATUS_REPO_DIR" checkout "$STATUS_BRANCH"
  git -C "$STATUS_REPO_DIR" pull --ff-only
fi

log "Create a root-only service environment"
TOKEN="${RESEARCH_OPS_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$ENV_FILE" ]; then
  TOKEN="$(sed -n 's/^RESEARCH_OPS_TOKEN=//p' "$ENV_FILE" | tail -1)"
fi
if [ -z "$TOKEN" ]; then
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
fi
$SUDO install -m 600 /dev/null "$ENV_FILE"
$SUDO tee "$ENV_FILE" >/dev/null <<EOF
RESEARCH_OPS_TOKEN=$TOKEN
RESEARCH_OPS_HOST=0.0.0.0
RESEARCH_OPS_PORT=$PORT
RESEARCH_OPS_ENDPOINT=http://127.0.0.1:$PORT
RESEARCH_OPS_REPO_DIR=$REPO_DIR
RESEARCH_OPS_STATE_DIR=/var/lib/research-ops
RESEARCH_OPS_SNAPSHOT_REPO=$STATUS_REPO_DIR
EOF
$SUDO mkdir -p /var/lib/research-ops
$SUDO chmod 700 /var/lib/research-ops

log "Install and start the systemd service"
SERVICE_TMP="$(mktemp)"
sed "s#/root/uncertainty#$REPO_DIR#g" "$REPO_DIR/deploy/research-ops.service" > "$SERVICE_TMP"
$SUDO install -m 644 "$SERVICE_TMP" /etc/systemd/system/research-ops.service
rm -f "$SERVICE_TMP"
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now research-ops.service

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
python taskctl/taskctl.py done P0-control-plane --message "control plane, auth, service, status branch and health check ready"
python taskctl/taskctl.py start P0-tailnet --total 3 --unit hosts --force
python taskctl/taskctl.py progress P0-tailnet --current 1 --total 3 --message "uq-control-01 joined tailnet"
python taskctl/taskctl.py snapshot || true

cat <<EOF

Control plane is ready.

Live dashboard (private tailnet): http://${TAILNET_IP}:${PORT}/
Health:                           http://${TAILNET_IP}:${PORT}/healthz
Secret environment:              ${ENV_FILE}  (mode 600)
Status branch:                   ${STATUS_BRANCH}

Before bootstrapping workers, securely copy RESEARCH_OPS_TOKEN from ${ENV_FILE}.
Do not paste the token into Git, issue comments, screenshots or shell history.
Configure GitHub Pages once: branch=${STATUS_BRANCH}, folder=/docs.

Recommended three-host names:
  uq-control-01  — this host
  uq-sim-01      — CPU-rich solver/Fisher worker
  uq-train-01    — training/validation worker (GPU only when useful)
EOF
