#!/usr/bin/env bash
# Build and smoke-test one frozen WHY-NOT competitor environment.
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: bootstrap_why_not_env.sh --baseline W0-LINX|W1-PRYM|W2-PRIMAT|W3-ABCMB [--repo DIR] [--source-root DIR]

The general solver-cpu environment must be bootstrapped first. Exact source
trees are stored persistently and are always checked against their frozen Git
revision before a smoke test is accepted.
EOF
}

BASELINE=""
REPO_DIR="${REPO_DIR:-}"
SOURCE_ROOT="${SOURCE_ROOT:-}"
while (($#)); do
  case "$1" in
    --baseline) BASELINE="${2:-}"; shift 2 ;;
    --repo) REPO_DIR="${2:-}"; shift 2 ;;
    --source-root) SOURCE_ROOT="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$BASELINE" in
  W0-LINX|W1-PRYM|W2-PRIMAT|W3-ABCMB) ;;
  *) echo "ERROR: unsupported baseline: $BASELINE" >&2; usage >&2; exit 2 ;;
esac

PROJECT_SLUG="${RESEARCH_OPS_PROJECT:-uncertainty}"
PERSIST_ROOT="${PERSIST_ROOT:-/root/autodl-fs/projects/${PROJECT_SLUG}}"
SCRATCH_ROOT="${SCRATCH_ROOT:-/root/autodl-tmp/projects/${PROJECT_SLUG}}"
REPO_DIR="${REPO_DIR:-${SCRATCH_ROOT}/repo}"
SOURCE_ROOT="${SOURCE_ROOT:-${PERSIST_ROOT}/external/why-not-v1}"
UV_VERSION="0.11.28"
UV_BIN="${PERSIST_ROOT}/tools/uv-${UV_VERSION}/bin/uv"
SOLVER_ENV="${SCRATCH_ROOT}/envs/solver-cpu"

[[ -d /root/autodl-fs && -d /root/autodl-tmp ]] || {
  echo "ERROR: AutoDL persistent and local data roots must both be mounted" >&2
  exit 1
}
[[ -x "$UV_BIN" && -x "${SOLVER_ENV}/bin/python" ]] || {
  echo "ERROR: bootstrap solver-cpu before WHY-NOT environments" >&2
  exit 1
}

if [[ ! -d "$SOURCE_ROOT" ]]; then
  bash "${REPO_DIR}/scripts/fetch_why_not_baselines.sh" "$SOURCE_ROOT"
fi

declare -A REVISIONS=(
  [LINX]=ec2e9d2ca455e8204137e884da29f5dd13a638fa
  [PRyMordial]=725d8a8db3ad5ea2630580d825c9d0d69ed76533
  [PRIMAT]=21ff8f39fa18e3937e9fdf386cfa982361bfdfce
  [ABCMB]=5eabbab4ed7e53f264e16024743d1ba517845c37
)
for source_name in LINX PRyMordial PRIMAT ABCMB; do
  actual="$(git -C "${SOURCE_ROOT}/${source_name}" rev-parse HEAD 2>/dev/null || true)"
  [[ "$actual" == "${REVISIONS[$source_name]}" ]] || {
    echo "ERROR: frozen revision mismatch for ${source_name}: ${actual:-missing}" >&2
    exit 1
  }
done

export UV_CACHE_DIR="${SCRATCH_ROOT}/uv-cache"
export UV_PYTHON_INSTALL_DIR="${PERSIST_ROOT}/python"
mkdir -p "$UV_CACHE_DIR" "${PERSIST_ROOT}/artifacts"

case "$BASELINE" in
  W0-LINX)
    PROJECT_DIR="${REPO_DIR}/environments/linx-v0.1.2"
    ENV_DIR="${SCRATCH_ROOT}/envs/why-not/linx-v0.1.2"
    export UV_PROJECT_ENVIRONMENT="$ENV_DIR"
    "$UV_BIN" sync --project "$PROJECT_DIR" --locked --no-dev --python 3.11.15
    "$UV_BIN" pip install \
      --python "${ENV_DIR}/bin/python" \
      --no-deps \
      --require-hashes \
      -r "${PROJECT_DIR}/interpax-sidecar.txt"
    ;;
  W1-PRYM)
    PROJECT_DIR="${REPO_DIR}/environments/solver-cpu"
    ENV_DIR="$SOLVER_ENV"
    ;;
  W2-PRIMAT)
    PROJECT_DIR="${REPO_DIR}/environments/solver-cpu"
    ENV_DIR="$SOLVER_ENV"
    "$UV_BIN" pip install \
      --python "${ENV_DIR}/bin/python" \
      --no-deps \
      --reinstall \
      "${SOURCE_ROOT}/PRIMAT"
    ;;
  W3-ABCMB)
    PROJECT_DIR="${REPO_DIR}/environments/abcmb-v0.3.1"
    ENV_DIR="${SCRATCH_ROOT}/envs/why-not/abcmb-v0.3.1"
    export UV_PROJECT_ENVIRONMENT="$ENV_DIR"
    "$UV_BIN" sync --project "$PROJECT_DIR" --locked --no-dev --python 3.11.15
    ;;
esac

OUTPUT="${PERSIST_ROOT}/artifacts/environment-${BASELINE}-$(hostname -s).json"
"${ENV_DIR}/bin/python" "${REPO_DIR}/scripts/why_not_environment_smoke.py" \
  --baseline "$BASELINE" \
  --source-root "$SOURCE_ROOT" \
  --lock "${PROJECT_DIR}/uv.lock" \
  --output "$OUTPUT"
echo "environment manifest: $OUTPUT"
