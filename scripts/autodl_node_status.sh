#!/usr/bin/env bash
# Human-readable snapshot before assigning a shared AutoDL node to a project.
set -Eeuo pipefail

LOCK_ROOT="${RESEARCH_WORKER_LOCK_ROOT:-/var/lock/research-workers}"

printf '=== identity ===\n'
printf 'time_utc: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'hostname: %s\n' "$(hostname -f 2>/dev/null || hostname)"
printf 'kernel: %s\n' "$(uname -srmo)"
printf 'uptime: %s\n' "$(uptime -p 2>/dev/null || true)"

printf '\n=== cpu and memory ===\n'
printf 'logical_cpus: %s\n' "$(nproc)"
lscpu 2>/dev/null | grep -E '^(Model name|Socket|Core|Thread|CPU\(s\)|NUMA node)' || true
free -h || true

printf '\n=== storage ===\n'
df -hT / /root/autodl-tmp /root/autodl-fs 2>/dev/null || df -hT /

printf '\n=== gpu ===\n'
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=index,name,uuid,memory.total,memory.used,utilization.gpu,temperature.gpu,driver_version \
    --format=csv,noheader 2>/dev/null || nvidia-smi
  printf '\nactive GPU processes:\n'
  nvidia-smi pmon -c 1 2>/dev/null || true
else
  echo 'nvidia-smi: unavailable'
fi

printf '\n=== active cross-project leases ===\n'
if compgen -G "${LOCK_ROOT}/*.json" >/dev/null; then
  for metadata in "${LOCK_ROOT}"/*.json; do
    printf '%s\n' "--- ${metadata}"
    cat "$metadata"
  done
else
  echo 'none'
fi

printf '\n=== likely scientific processes ===\n'
ps -eo pid,ppid,user,%cpu,%mem,etime,args --sort=-%cpu \
  | grep -E 'PID|python|julia|cobaya|montepython|class|parthe|alterbbn|linx|prymordial|run_with_heartbeat' \
  | head -40 || true

printf '\n=== project directories ===\n'
find /root/autodl-fs/projects /root/autodl-tmp/projects -mindepth 1 -maxdepth 2 -type d 2>/dev/null \
  | sort || true
