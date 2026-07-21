#!/usr/bin/env bash
# AutoDL specialization of the generic worker bootstrap.
set -Eeuo pipefail
export PERSIST_DIR="${PERSIST_DIR:-/root/autodl-fs/uncertainty-ops}"
export REPO_DIR="${REPO_DIR:-/root/uncertainty}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/bootstrap_worker.sh"
