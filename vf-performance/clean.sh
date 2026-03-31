#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_ROOT="${REPO_ROOT}/.cache/vf-performance"
STATE_DIR="${CACHE_ROOT}/qemu"
PIDFILE="${STATE_DIR}/qemu.pid"

if [[ -f "${PIDFILE}" ]]; then
  pid="$(cat "${PIDFILE}" 2>/dev/null || true)"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    kill "${pid}" 2>/dev/null || true
    for _ in $(seq 1 30); do
      if ! kill -0 "${pid}" 2>/dev/null; then
        break
      fi
      sleep 1
    done
    if kill -0 "${pid}" 2>/dev/null; then
      kill -9 "${pid}" 2>/dev/null || true
    fi
  fi
fi

rm -rf "${CACHE_ROOT}"

echo "Removed ${CACHE_ROOT}"
echo "Next run will reprovision the managed QEMU guest from scratch."
