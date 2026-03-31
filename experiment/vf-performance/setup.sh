#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "setup.sh only supports macOS hosts." >&2
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required. Install it first: https://brew.sh" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_ROOT="${REPO_ROOT}/.cache/vf-performance"
STATE_DIR="${CACHE_ROOT}/qemu"
LLVM_CUSTOM_INPUT="${LLVM_CUSTOM:-}"
GUEST_USER="${GUEST_USER:-vf}"
GUEST_WORKSPACE="${GUEST_WORKSPACE:-/home/${GUEST_USER}/work/vf-performance}"
GUEST_CACHE_DIR="${GUEST_CACHE_DIR:-${GUEST_WORKSPACE}/.cache/vf-performance}"
GUEST_LLVM_PROJECT_DIR="${GUEST_LLVM_PROJECT_DIR:-${GUEST_WORKSPACE}/llvm-project-host}"
SSH_PORT="${SSH_PORT:-10022}"
QEMU_CPUS="${QEMU_CPUS:-4}"
QEMU_MEMORY_MIB="${QEMU_MEMORY_MIB:-8192}"
QEMU_SYSTEM="${QEMU_SYSTEM:-qemu-system-x86_64}"
QEMU_ACCEL="${QEMU_ACCEL:-tcg}"
GIT_SUBMODULE_DEPTH="${GIT_SUBMODULE_DEPTH:-1}"
SETUP_TARGETS_RAW="${SETUP_TARGETS:-saturn xiangshan t1}"
BASE_IMAGE_URL="${BASE_IMAGE_URL:-https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img}"

append_word() {
  local current="$1"
  local item="$2"
  if [[ -z "${current}" ]]; then
    printf '%s' "${item}"
    return 0
  fi
  case " ${current} " in
    *" ${item} "*) printf '%s' "${current}" ;;
    *) printf '%s %s' "${current}" "${item}" ;;
  esac
}

SETUP_TARGETS=""
SETUP_SUBMODULES=""
SETUP_TARGET_COUNT=0
for target in ${SETUP_TARGETS_RAW//,/ }; do
  group="${target%%.*}"
  if [[ -z "${group}" ]]; then
    continue
  fi
  SETUP_TARGETS="$(append_word "${SETUP_TARGETS}" "${target}")"
  SETUP_TARGET_COUNT=$((SETUP_TARGET_COUNT + 1))
  case "${group}" in
    saturn|ara)
      SETUP_SUBMODULES="$(append_word "${SETUP_SUBMODULES}" "chipyard")"
      ;;
    gem5)
      SETUP_SUBMODULES="$(append_word "${SETUP_SUBMODULES}" "gem5")"
      ;;
    xiangshan)
      for path in "XiangShan" "third-party/NEMU" "third-party/nexus-am"; do
        SETUP_SUBMODULES="$(append_word "${SETUP_SUBMODULES}" "${path}")"
      done
      ;;
    t1)
      SETUP_SUBMODULES="$(append_word "${SETUP_SUBMODULES}" "t1-micro58ae")"
      ;;
    vicuna)
      SETUP_SUBMODULES="$(append_word "${SETUP_SUBMODULES}" "vicuna")"
      ;;
    *)
      echo "Unsupported setup target: ${target}" >&2
      exit 1
      ;;
  esac
done

if [[ "${SETUP_TARGET_COUNT}" -eq 0 ]]; then
  echo "SETUP_TARGETS must include at least one simulator target." >&2
  exit 1
fi

resolve_llvm_project_root() {
  local raw="$1"
  local candidate

  if [[ -z "${raw}" ]]; then
    return 1
  fi

  candidate="$(cd "${raw}" 2>/dev/null && pwd || true)"
  if [[ -z "${candidate}" ]]; then
    return 1
  fi

  for probe in \
    "${candidate}" \
    "${candidate}/.." \
    "${candidate}/../.." \
    "${candidate}/../../.."
  do
    if [[ -f "${probe}/llvm/CMakeLists.txt" ]]; then
      cd "${probe}" && pwd
      return 0
    fi
  done

  return 1
}

if [[ -z "${LLVM_CUSTOM_INPUT}" ]]; then
  echo "LLVM_CUSTOM must be set to an llvm-project root, build dir, or bin dir." >&2
  exit 1
fi

LOCAL_LLVM_PROJECT="$(resolve_llvm_project_root "${LLVM_CUSTOM_INPUT}" || true)"

if [[ -z "${LOCAL_LLVM_PROJECT}" ]]; then
  echo "LLVM_CUSTOM must resolve to an llvm-project root containing llvm/CMakeLists.txt: ${LLVM_CUSTOM_INPUT}" >&2
  exit 1
fi

mkdir -p "${STATE_DIR}"

BASE_IMAGE="${STATE_DIR}/ubuntu-24.04-server-cloudimg-amd64.img"
DISK_IMAGE="${STATE_DIR}/guest.qcow2"
SEED_ISO="${STATE_DIR}/seed.iso"
PIDFILE="${STATE_DIR}/qemu.pid"
SERIAL_LOG="${STATE_DIR}/serial.log"
SSH_KEY="${STATE_DIR}/id_ed25519"
SSH_PUB="${SSH_KEY}.pub"
USER_DATA="${STATE_DIR}/user-data"
META_DATA="${STATE_DIR}/meta-data"
METADATA_JSON="${STATE_DIR}/metadata.json"

brew install uv qemu xorriso

cd "${REPO_ROOT}"
uv sync

if [[ ! -f "${SSH_KEY}" ]]; then
  ssh-keygen -q -t ed25519 -N "" -f "${SSH_KEY}"
fi

if [[ ! -f "${BASE_IMAGE}" ]]; then
  curl -L "${BASE_IMAGE_URL}" -o "${BASE_IMAGE}"
fi

if [[ ! -f "${DISK_IMAGE}" ]]; then
  qemu-img create -f qcow2 -F qcow2 -b "${BASE_IMAGE}" "${DISK_IMAGE}" 160G
fi

cat >"${USER_DATA}" <<EOF
#cloud-config
users:
  - default
  - name: ${GUEST_USER}
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: sudo
    ssh_authorized_keys:
      - $(cat "${SSH_PUB}")
package_update: true
packages:
  - openssh-server
runcmd:
  - mkdir -p ${GUEST_WORKSPACE}
  - chown -R ${GUEST_USER}:${GUEST_USER} /home/${GUEST_USER}
EOF

cat >"${META_DATA}" <<EOF
instance-id: vf-performance
local-hostname: vf-performance
EOF

xorriso -as mkisofs -volid cidata -joliet -rock \
  -output "${SEED_ISO}" \
  "${USER_DATA}" "${META_DATA}" >/dev/null 2>&1

shell_quote() {
  python3 -c 'import shlex, sys; print(shlex.quote(sys.argv[1]))' "$1"
}

ssh_base() {
  ssh \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o IdentitiesOnly=yes \
    -o LogLevel=ERROR \
    -i "${SSH_KEY}" \
    -p "${SSH_PORT}" \
    "${GUEST_USER}@127.0.0.1" "$@"
}

ssh_ready() {
  ssh \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o IdentitiesOnly=yes \
    -o LogLevel=ERROR \
    -o ConnectTimeout=5 \
    -i "${SSH_KEY}" \
    -p "${SSH_PORT}" \
    "${GUEST_USER}@127.0.0.1" true >/dev/null 2>&1
}

start_qemu() {
  if ssh_ready; then
    return
  fi
  rm -f "${PIDFILE}"
  "${QEMU_SYSTEM}" \
    -daemonize \
    -pidfile "${PIDFILE}" \
    -machine "q35,accel=${QEMU_ACCEL}" \
    -cpu max \
    -smp "${QEMU_CPUS}" \
    -m "${QEMU_MEMORY_MIB}" \
    -display none \
    -serial "file:${SERIAL_LOG}" \
    -netdev "user,id=net0,hostfwd=tcp:127.0.0.1:${SSH_PORT}-:22" \
    -device virtio-net-pci,netdev=net0 \
    -drive "if=virtio,format=qcow2,file=${DISK_IMAGE}" \
    -cdrom "${SEED_ISO}"
}

wait_for_ssh() {
  local retries=120
  until ssh_ready; do
    retries=$((retries - 1))
    if [[ "${retries}" -le 0 ]]; then
      echo "Timed out waiting for the guest SSH service." >&2
      exit 1
    fi
    sleep 5
  done
}

ssh_exec_retry() {
  local attempts=5
  local delay_s=5
  local attempt
  local output
  for attempt in $(seq 1 "${attempts}"); do
    if output="$(ssh_base "$@" 2>&1)"; then
      if [[ -n "${output}" ]]; then
        printf '%s\n' "${output}"
      fi
      return 0
    fi
    if [[ "${attempt}" -lt "${attempts}" ]]; then
      sleep "${delay_s}"
      wait_for_ssh
      continue
    fi
    if [[ -n "${output}" ]]; then
      printf '%s\n' "${output}" >&2
    fi
    return 1
  done
}

stream_tar_with_retry() {
  local source_root="$1"
  local remote_cmd="$2"
  shift 2
  local attempt
  local output

  for attempt in $(seq 1 5); do
    if output="$(
      COPYFILE_DISABLE=1 COPY_EXTENDED_ATTRIBUTES_DISABLE=1 tar \
        --disable-copyfile \
        --no-mac-metadata \
        "$@" \
        -C "${source_root}" -cf - . \
      | ssh_base "${remote_cmd}" 2>&1
    )"; then
      if [[ -n "${output}" ]]; then
        printf '%s\n' "${output}"
      fi
      return 0
    fi
    if [[ "${attempt}" -lt 5 ]]; then
      sleep 5
      wait_for_ssh
      continue
    fi
    if [[ -n "${output}" ]]; then
      printf '%s\n' "${output}" >&2
    fi
    return 1
  done
}

sync_repo() {
  stream_tar_with_retry "${REPO_ROOT}" \
    "mkdir -p '${GUEST_WORKSPACE}' && tar -xf - -C '${GUEST_WORKSPACE}'" \
    --exclude='.cache' \
    --exclude='.venv' \
    --exclude='__pycache__'
}

sync_local_llvm_project() {
  if [[ ! -d "${LOCAL_LLVM_PROJECT}" ]]; then
    echo "Resolved llvm-project root does not exist: ${LOCAL_LLVM_PROJECT}" >&2
    exit 1
  fi

  stream_tar_with_retry "${LOCAL_LLVM_PROJECT}" \
    "rm -rf '${GUEST_LLVM_PROJECT_DIR}' && mkdir -p '${GUEST_LLVM_PROJECT_DIR}' && tar -xf - -C '${GUEST_LLVM_PROJECT_DIR}'" \
    --exclude='.git' \
    --exclude='build' \
    --exclude='cmake-build-*' \
    --exclude='__pycache__'
}

run_guest_setup() {
  local script
  script=$(
    cat <<EOF
set -euo pipefail
cd $(shell_quote "${GUEST_WORKSPACE}")

bootstrap_rvv_repo() {
  (
    cd rvv-poc-main
    if [[ ! -d .git ]]; then
      git init
      git config user.name vf-performance
      git config user.email vf-performance@local
    fi

    want_path() {
      local candidate="\$1"
      local required
      for required in ${SETUP_SUBMODULES}; do
        if [[ "\${required}" == "\${candidate}" ]]; then
          return 0
        fi
      done
      return 1
    }

    while read -r key path; do
      name="\${key#submodule.}"
      name="\${name%.path}"
      if ! want_path "\${path}"; then
        continue
      fi
      url="\$(git config -f .gitmodules --get submodule.\${name}.url)"
      if git config --file .git/config --get "submodule.\${name}.url" >/dev/null 2>&1; then
        if [[ ${GIT_SUBMODULE_DEPTH} -gt 0 ]]; then
          git submodule update --init --depth ${GIT_SUBMODULE_DEPTH} --recommend-shallow --jobs 1 "\${path}"
        else
          git submodule update --init --jobs 1 "\${path}"
        fi
        continue
      fi
      rm -rf "\${path}"
      git submodule add --depth ${GIT_SUBMODULE_DEPTH} "\${url}" "\${path}"
      git config -f .gitmodules submodule.\${name}.shallow true
    done < <(git config -f .gitmodules --get-regexp '^submodule\\..*\\.path\$')
  )
}

bootstrap_rvv_repo
if [[ ! -f $(shell_quote "${GUEST_LLVM_PROJECT_DIR}/llvm/CMakeLists.txt") ]]; then
  echo "Guest local llvm-project is missing llvm/CMakeLists.txt at ${GUEST_LLVM_PROJECT_DIR}" >&2
  exit 1
fi
cd rvv-poc-main
export GIT_SUBMODULE_DEPTH=${GIT_SUBMODULE_DEPTH}
export BUILD_TARGETS=$(shell_quote "${SETUP_TARGETS}")
export USE_LOCAL_LLVM_PROJECT=1
export LLVM_DIR=${GUEST_LLVM_PROJECT_DIR}/llvm
./build.sh
source env.sh
./build-sim.sh ${SETUP_TARGETS}
EOF
  )
  ssh_exec_retry "bash -lc $(shell_quote "${script}")"
}

write_metadata() {
  local guest_rvv_root="${GUEST_WORKSPACE}/rvv-poc-main"
  local guest_clang="${guest_rvv_root}/llvm-build/bin/clang"
  local guest_opt="${guest_rvv_root}/llvm-build/bin/opt"
  local guest_gem5="${guest_rvv_root}/gem5/build/RISCV/gem5.opt"
  local guest_sysroot="${guest_rvv_root}/chipyard/.conda-env/riscv-tools/riscv64-unknown-linux-gnu/sysroot"

  local clang_version
  local opt_version
  local gem5_version
  clang_version="$(ssh_exec_retry "bash -lc $(shell_quote "$(shell_quote "${guest_clang}") --version | head -n 1")")"
  opt_version="$(ssh_exec_retry "bash -lc $(shell_quote "$(shell_quote "${guest_opt}") --version | head -n 1")")"
  gem5_version="$(ssh_exec_retry "bash -lc $(shell_quote "$(shell_quote "${guest_gem5}") --version | head -n 1 || true")")"

  export GUEST_USER SSH_PORT SSH_KEY GUEST_WORKSPACE GUEST_CACHE_DIR DISK_IMAGE SEED_ISO
  export PIDFILE SERIAL_LOG QEMU_SYSTEM QEMU_ACCEL QEMU_CPUS QEMU_MEMORY_MIB METADATA_JSON
  export GUEST_CLANG="${guest_clang}" GUEST_OPT="${guest_opt}" GUEST_GEM5="${guest_gem5}" GUEST_SYSROOT="${guest_sysroot}"
  export CLANG_VERSION="${clang_version}" OPT_VERSION="${opt_version}" GEM5_VERSION="${gem5_version}"
  python3 - <<'PY'
import json
import os
from pathlib import Path

payload = {
    "ssh_user": os.environ["GUEST_USER"],
    "ssh_port": int(os.environ["SSH_PORT"]),
    "ssh_key_path": str(Path(os.environ["SSH_KEY"]).resolve()),
    "guest_workspace": os.environ["GUEST_WORKSPACE"],
    "guest_cache_dir": os.environ["GUEST_CACHE_DIR"],
    "disk_path": str(Path(os.environ["DISK_IMAGE"]).resolve()),
    "seed_iso_path": str(Path(os.environ["SEED_ISO"]).resolve()),
    "pidfile": str(Path(os.environ["PIDFILE"]).resolve()),
    "serial_log": str(Path(os.environ["SERIAL_LOG"]).resolve()),
    "qemu_system": os.environ["QEMU_SYSTEM"],
    "accel": os.environ["QEMU_ACCEL"],
    "cpus": int(os.environ["QEMU_CPUS"]),
    "memory_mib": int(os.environ["QEMU_MEMORY_MIB"]),
    "tools": {
        "clang": os.environ["GUEST_CLANG"],
        "opt": os.environ["GUEST_OPT"],
        "gem5": os.environ["GUEST_GEM5"],
        "sysroot": os.environ["GUEST_SYSROOT"],
    },
    "tool_versions": {
        "clang": os.environ["CLANG_VERSION"],
        "opt": os.environ["OPT_VERSION"],
        "gem5": os.environ["GEM5_VERSION"],
    },
}
Path(os.environ["METADATA_JSON"]).write_text(json.dumps(payload, indent=2))
PY
}

start_qemu
wait_for_ssh
sync_repo
sync_local_llvm_project
run_guest_setup
write_metadata

echo "Managed QEMU guest is ready."
echo "Metadata: ${METADATA_JSON}"
