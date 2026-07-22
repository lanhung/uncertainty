#!/usr/bin/env bash
# Build one project-scoped scientific environment from its exact uv lock.
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: bootstrap_science_env.sh --kind solver-cpu|train-gpu [--repo DIR]

The default AutoDL paths follow the shared-worker storage policy. Override
PERSIST_ROOT and SCRATCH_ROOT only with project-scoped locations.
EOF
}

KIND=""
REPO_DIR="${REPO_DIR:-}"
while (($#)); do
  case "$1" in
    --kind) KIND="${2:-}"; shift 2 ;;
    --repo) REPO_DIR="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$KIND" in
  solver-cpu|train-gpu) ;;
  *) echo "ERROR: --kind must be solver-cpu or train-gpu" >&2; exit 2 ;;
esac

PROJECT_SLUG="${RESEARCH_OPS_PROJECT:-uncertainty}"
PERSIST_ROOT="${PERSIST_ROOT:-/root/autodl-fs/projects/${PROJECT_SLUG}}"
SCRATCH_ROOT="${SCRATCH_ROOT:-/root/autodl-tmp/projects/${PROJECT_SLUG}}"
REPO_DIR="${REPO_DIR:-${SCRATCH_ROOT}/repo}"
PROJECT_DIR="${REPO_DIR}/environments/${KIND}"
LOCK_FILE="${PROJECT_DIR}/uv.lock"

[[ -d /root/autodl-fs && -d /root/autodl-tmp ]] || {
  echo "ERROR: AutoDL persistent and local data roots must both be mounted" >&2
  exit 1
}
[[ -f "$PROJECT_DIR/pyproject.toml" && -f "$LOCK_FILE" ]] || {
  echo "ERROR: checked-in ${KIND} project or lock is missing" >&2
  exit 1
}

UV_VERSION="0.11.28"
UV_TOOL_ROOT="${PERSIST_ROOT}/tools/uv-${UV_VERSION}"
UV_BIN="${UV_TOOL_ROOT}/bin/uv"
if [[ ! -x "$UV_BIN" ]]; then
  if [[ -e "$UV_TOOL_ROOT" ]]; then
    QUARANTINE="${UV_TOOL_ROOT}.incomplete.$(date -u +%Y%m%dT%H%M%SZ).$$"
    mv "$UV_TOOL_ROOT" "$QUARANTINE"
    echo "quarantined incomplete uv bootstrap: $QUARANTINE" >&2
  fi
  BOOTSTRAP_PYTHON=""
  # AutoDL's system Python may omit ensurepip/python3-venv. Prefer the
  # image-provided Miniconda interpreter only for this project-local uv
  # bootstrap; the scientific environment itself still uses pinned CPython.
  for candidate in /root/miniconda3/bin/python python3 /usr/bin/python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      BOOTSTRAP_PYTHON="$(command -v "$candidate")"
      break
    elif [[ -x "$candidate" ]]; then
      BOOTSTRAP_PYTHON="$candidate"
      break
    fi
  done
  [[ -n "$BOOTSTRAP_PYTHON" ]] || {
    echo "ERROR: no bootstrap Python interpreter was found" >&2
    exit 1
  }
  "$BOOTSTRAP_PYTHON" -m venv "$UV_TOOL_ROOT"
  "$UV_TOOL_ROOT/bin/python" -m pip install --disable-pip-version-check "uv==${UV_VERSION}"
fi
UV_VERSION_OUTPUT="$($UV_BIN --version)"
[[ "$(awk '{print $1, $2}' <<<"$UV_VERSION_OUTPUT")" == "uv ${UV_VERSION}" ]] || {
  echo "ERROR: unexpected uv version: $UV_VERSION_OUTPUT" >&2
  exit 1
}

export UV_CACHE_DIR="${SCRATCH_ROOT}/uv-cache"
export UV_PYTHON_INSTALL_DIR="${PERSIST_ROOT}/python"
export UV_PROJECT_ENVIRONMENT="${SCRATCH_ROOT}/envs/${KIND}"
mkdir -p "$UV_CACHE_DIR" "$UV_PYTHON_INSTALL_DIR" "$(dirname "$UV_PROJECT_ENVIRONMENT")"

"$UV_BIN" sync \
  --project "$PROJECT_DIR" \
  --locked \
  --no-dev \
  --python 3.11.15

OUTPUT="${PERSIST_ROOT}/artifacts/environment-${KIND}-$(hostname -s).json"
SMOKE_ARGS=(
  --kind "$KIND"
  --lock "$LOCK_FILE"
  --output "$OUTPUT"
)
"${UV_PROJECT_ENVIRONMENT}/bin/python" \
  "${REPO_DIR}/scripts/science_environment_smoke.py" \
  "${SMOKE_ARGS[@]}"
echo "environment manifest: $OUTPUT"
