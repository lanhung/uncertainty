#!/usr/bin/env bash
# Configure project-safe, key-based SSH aliases from the shared Vultr host to
# two replaceable AutoDL instances. The live inventory is intentionally local
# and gitignored.
set -Eeuo pipefail
umask 077

INVENTORY="deploy/hosts.local.env"
INSTALL_KEYS=0
HARDEN_KEYS="${HARDEN_AUTHORIZED_KEYS:-1}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/setup_control_autodl_ssh.sh [--inventory PATH] [--install]

Without --install the script creates one key pair per worker and writes SSH
aliases. With --install it also invokes ssh-copy-id interactively, verifies
BatchMode login, and prefixes the installed key with restrictions that disable
agent, X11 and TCP forwarding.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --inventory)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      INVENTORY="$2"
      shift 2
      ;;
    --install)
      INSTALL_KEYS=1
      shift
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

[ -f "$INVENTORY" ] || {
  echo "Missing $INVENTORY. Copy deploy/hosts.local.env.example first." >&2
  exit 1
}
# shellcheck disable=SC1090
source "$INVENTORY"

PROJECT_SLUG="${PROJECT_SLUG:-uncertainty}"
KEY_DIR="${AUTODL_KEY_DIR:-${HOME}/.ssh/research-workers}"
SSH_DIR="${HOME}/.ssh"
SSH_CONFIG="${SSH_DIR}/config"
WORKER_CONFIG="${SSH_DIR}/research-workers.conf"
INCLUDE_LINE="Include ${WORKER_CONFIG}"
CONTROL_PATH_DIR="${SSH_CONTROL_PATH_DIR:-${SSH_DIR}}"
WORKER_PREFIXES=(AUTODL1 AUTODL2)
if [ -n "${AUTODL3_ALIAS:-}${AUTODL3_HOST:-}${AUTODL3_PORT:-}${AUTODL3_USER:-}" ]; then
  WORKER_PREFIXES+=(AUTODL3)
fi

for command_name in ssh ssh-keygen ssh-copy-id awk grep install; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "Required command not found: $command_name" >&2
    exit 1
  }
done

install -d -m 700 "$SSH_DIR" "$KEY_DIR" "$CONTROL_PATH_DIR"
touch "$SSH_CONFIG" "$WORKER_CONFIG" "${SSH_DIR}/known_hosts"
chmod 600 "$SSH_CONFIG" "$WORKER_CONFIG" "${SSH_DIR}/known_hosts"

if ! grep -Fxq "$INCLUDE_LINE" "$SSH_CONFIG"; then
  temporary_config="$(mktemp)"
  {
    printf '%s\n' "$INCLUDE_LINE"
    cat "$SSH_CONFIG"
  } > "$temporary_config"
  install -m 600 "$temporary_config" "$SSH_CONFIG"
  rm -f "$temporary_config"
fi

required_for_node() {
  local prefix="$1"
  local variable
  for variable in ALIAS HOST PORT USER; do
    local name="${prefix}_${variable}"
    [ -n "${!name:-}" ] || {
      echo "Missing ${name} in ${INVENTORY}" >&2
      exit 1
    }
  done
}

key_path_for() {
  local alias_name="$1"
  printf '%s/%s_ed25519' "$KEY_DIR" "$alias_name"
}

create_key_for() {
  local prefix="$1"
  local alias_var="${prefix}_ALIAS"
  local alias_name="${!alias_var}"
  local key_path
  key_path="$(key_path_for "$alias_name")"
  if [ ! -f "$key_path" ]; then
    ssh-keygen -q -t ed25519 -N '' \
      -C "${PROJECT_SLUG}:shared-control->${alias_name}" \
      -f "$key_path"
  fi
  chmod 600 "$key_path"
  chmod 644 "${key_path}.pub"
}

write_worker_config() {
  : > "$WORKER_CONFIG"
  local prefix
  for prefix in "${WORKER_PREFIXES[@]}"; do
    local alias_var="${prefix}_ALIAS"
    local host_var="${prefix}_HOST"
    local port_var="${prefix}_PORT"
    local user_var="${prefix}_USER"
    local alias_name="${!alias_var}"
    local host_name="${!host_var}"
    local port="${!port_var}"
    local user_name="${!user_var}"
    local key_path
    key_path="$(key_path_for "$alias_name")"
    cat >> "$WORKER_CONFIG" <<EOF
Host ${alias_name}
  HostName ${host_name}
  Port ${port}
  User ${user_name}
  IdentityFile ${key_path}
  IdentitiesOnly yes
  PreferredAuthentications publickey
  PasswordAuthentication no
  StrictHostKeyChecking yes
  UserKnownHostsFile ${SSH_DIR}/known_hosts
  ForwardAgent no
  ClearAllForwardings yes
  ServerAliveInterval 30
  ServerAliveCountMax 6
  ConnectTimeout 20
  ControlMaster auto
  ControlPersist 10m
  ControlPath ${CONTROL_PATH_DIR}/cm-%C
  Compression yes

EOF
  done
  chmod 600 "$WORKER_CONFIG"
}

install_key_for() {
  local prefix="$1"
  local alias_var="${prefix}_ALIAS"
  local host_var="${prefix}_HOST"
  local port_var="${prefix}_PORT"
  local user_var="${prefix}_USER"
  local alias_name="${!alias_var}"
  local host_name="${!host_var}"
  local port="${!port_var}"
  local user_name="${!user_var}"
  local key_path
  key_path="$(key_path_for "$alias_name")"

  cat <<EOF

Installing ${key_path}.pub on ${user_name}@${host_name}:${port}.
Before accepting a new host key, compare its fingerprint with the value shown
inside the AutoDL instance or provider console. Do not use StrictHostKeyChecking=no.
EOF
  ssh-copy-id -i "${key_path}.pub" -p "$port" \
    -o StrictHostKeyChecking=ask "${user_name}@${host_name}"

  ssh -o BatchMode=yes "$alias_name" \
    'printf "key-login-ok host=%s user=%s\n" "$(hostname -s)" "$(id -un)"'

  if [ "$HARDEN_KEYS" = "1" ]; then
    local key_type key_body options
    key_type="$(awk '{print $1}' "${key_path}.pub")"
    key_body="$(awk '{print $2}' "${key_path}.pub")"
    options='no-agent-forwarding,no-port-forwarding,no-X11-forwarding,no-user-rc'
    ssh "$alias_name" python3 - "$key_type" "$key_body" "$options" <<'PY'
from __future__ import annotations

import os
import sys
from pathlib import Path

key_type, key_body, options = sys.argv[1:]
path = Path.home() / ".ssh" / "authorized_keys"
path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
updated: list[str] = []
found = False
for raw in lines:
    fields = raw.split()
    match_index = None
    for index in range(len(fields) - 1):
        if fields[index] == key_type and fields[index + 1] == key_body:
            match_index = index
            break
    if match_index is None:
        updated.append(raw)
        continue
    updated.append(f"{options} " + " ".join(fields[match_index:]))
    found = True
if not found:
    raise SystemExit("installed public key was not found in authorized_keys")
temporary = path.with_suffix(".tmp")
temporary.write_text("\n".join(updated) + "\n", encoding="utf-8")
os.chmod(temporary, 0o600)
temporary.replace(path)
PY
    ssh -O exit "$alias_name" >/dev/null 2>&1 || true
    ssh -o BatchMode=yes "$alias_name" 'echo restricted-key-login-ok'
  fi
}

for prefix in "${WORKER_PREFIXES[@]}"; do
  required_for_node "$prefix"
  create_key_for "$prefix"
done
write_worker_config

if [ "$INSTALL_KEYS" = "1" ]; then
  for prefix in "${WORKER_PREFIXES[@]}"; do
    install_key_for "$prefix"
  done
else
  echo "SSH aliases and node-specific key pairs are ready."
  echo
  echo "Review public keys:"
  for prefix in "${WORKER_PREFIXES[@]}"; do
    alias_var="${prefix}_ALIAS"
    echo "  cat $(key_path_for "${!alias_var}").pub"
  done
  cat <<EOF
Install them interactively after checking host fingerprints:
  bash scripts/setup_control_autodl_ssh.sh --inventory ${INVENTORY} --install
EOF
fi

echo
echo "SSH configuration: ${WORKER_CONFIG}"
echo "Test commands:"
for prefix in "${WORKER_PREFIXES[@]}"; do
  alias_var="${prefix}_ALIAS"
  echo "  ssh ${!alias_var} hostname"
done
cat <<'EOF'

No worker-to-worker key is created. AutoDL nodes should not gain lateral SSH
access to each other or a private key that can log back into the Vultr host.
EOF
