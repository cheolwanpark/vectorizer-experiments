"""Execution backends for local and managed-QEMU runs."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ExecResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class QemuMetadata:
    ssh_user: str
    ssh_port: int
    ssh_key_path: str
    guest_workspace: str
    guest_cache_dir: str
    disk_path: str
    seed_iso_path: str
    pidfile: str
    serial_log: str
    qemu_system: str = "qemu-system-x86_64"
    accel: str = "tcg"
    cpus: int = 4
    memory_mib: int = 8192
    tools: dict[str, str] = field(default_factory=dict)
    tool_versions: dict[str, str] = field(default_factory=dict)


def default_executor() -> str:
    return "qemu" if platform.system() == "Darwin" else "local"


def default_qemu_state_dir(cache_dir: str | Path | None = None) -> Path:
    root = Path(cache_dir) if cache_dir is not None else (PROJECT_ROOT / ".cache" / "vf-performance")
    return root / "qemu"


def metadata_path(state_dir: str | Path) -> Path:
    return Path(state_dir) / "metadata.json"


def load_qemu_metadata(state_dir: str | Path) -> QemuMetadata:
    path = metadata_path(state_dir)
    if not path.exists():
        raise FileNotFoundError(f"QEMU metadata not found: {path}")
    data = json.loads(path.read_text())
    return QemuMetadata(
        ssh_user=data["ssh_user"],
        ssh_port=int(data["ssh_port"]),
        ssh_key_path=data["ssh_key_path"],
        guest_workspace=data["guest_workspace"],
        guest_cache_dir=data.get("guest_cache_dir", f"{data['guest_workspace']}/.cache/vf-performance"),
        disk_path=data["disk_path"],
        seed_iso_path=data["seed_iso_path"],
        pidfile=data["pidfile"],
        serial_log=data["serial_log"],
        qemu_system=data.get("qemu_system", "qemu-system-x86_64"),
        accel=data.get("accel", "tcg"),
        cpus=int(data.get("cpus", 4)),
        memory_mib=int(data.get("memory_mib", 8192)),
        tools=dict(data.get("tools", {})),
        tool_versions=dict(data.get("tool_versions", {})),
    )


def resolve_qemu_tools(
    state_dir: str | Path,
) -> tuple[dict[str, str], str | None, dict[str, str]]:
    try:
        metadata = load_qemu_metadata(state_dir)
    except FileNotFoundError:
        return (
            {"clang": "", "opt": "", "sysroot": "", "gem5": ""},
            None,
            {},
        )
    return dict(metadata.tools), metadata.guest_workspace, dict(metadata.tool_versions)


class LocalExecutionBackend:
    """Run commands on the host."""

    def prepare(self, *, sync_repo: bool = False) -> None:
        return

    def cleanup(self) -> None:
        return

    def command_path(self, path: Path) -> str:
        return str(path)

    def run(
        self,
        cmd: list[str],
        *,
        cwd: Path | str | None = None,
        timeout: int | None = None,
    ) -> ExecResult:
        try:
            result = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd is not None else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return ExecResult(
                returncode=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )
        except subprocess.TimeoutExpired as exc:
            return ExecResult(
                returncode=124,
                stdout=(exc.stdout or ""),
                stderr=((exc.stderr or "") + "\nTIMEOUT"),
            )

    def materialize_file(self, path: Path) -> None:
        return

    def materialize_dir(self, path: Path) -> None:
        return


class QemuExecutionBackend:
    """Run commands inside a managed Linux guest over SSH."""

    def __init__(self, runtime, cache_root: Path):
        self.runtime = runtime
        self.cache_root = cache_root
        self.host_repo_root = PROJECT_ROOT.resolve()
        self.host_cache_root = cache_root.resolve()
        self.state_dir = Path(runtime.qemu_state_dir or default_qemu_state_dir(runtime.cache_dir)).resolve()
        self.metadata = load_qemu_metadata(self.state_dir)

    def prepare(self, *, sync_repo: bool = False) -> None:
        self.ensure_started()
        if sync_repo:
            self.sync_repo()

    def cleanup(self) -> None:
        return

    def command_path(self, path: Path) -> str:
        resolved = path.resolve()
        if resolved.is_relative_to(self.host_cache_root):
            relative = resolved.relative_to(self.host_cache_root)
            return str((Path(self.metadata.guest_cache_dir) / relative).as_posix())
        if resolved.is_relative_to(self.host_repo_root):
            relative = resolved.relative_to(self.host_repo_root)
            return str((Path(self.metadata.guest_workspace) / relative).as_posix())
        return str(path)

    def run(
        self,
        cmd: list[str],
        *,
        cwd: Path | str | None = None,
        timeout: int | None = None,
    ) -> ExecResult:
        self.ensure_started()
        if isinstance(cwd, Path):
            remote_cwd = self.command_path(cwd)
        else:
            remote_cwd = cwd
        script = shlex_join(cmd)
        if remote_cwd:
            script = f"cd {shell_quote(remote_cwd)} && {script}"
        return self._run_ssh_shell(script, timeout=timeout)

    def materialize_file(self, path: Path) -> None:
        remote_path = self.command_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        cmd = self._ssh_base() + [f"bash -lc {shell_quote(f'cat {shell_quote(remote_path)}')}"]
        with path.open("wb") as handle:
            result = subprocess.run(
                cmd,
                stdout=handle,
                stderr=subprocess.PIPE,
                check=False,
            )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or b"").decode(errors="replace").strip() or f"failed to fetch {remote_path}")

    def materialize_dir(self, path: Path) -> None:
        remote_path = self.command_path(path)
        shutil.rmtree(path, ignore_errors=True)
        path.parent.mkdir(parents=True, exist_ok=True)

        remote_parent = str(Path(remote_path).parent)
        remote_name = Path(remote_path).name
        ssh_cmd = self._ssh_base() + [
            f"bash -lc {shell_quote(f'test -d {shell_quote(remote_path)} && tar -C {shell_quote(remote_parent)} -cf - {shell_quote(remote_name)}')}"
        ]
        producer = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            consumer = subprocess.run(
                ["tar", "-xf", "-", "-C", str(path.parent)],
                stdin=producer.stdout,
                capture_output=True,
                check=False,
            )
        finally:
            if producer.stdout is not None:
                producer.stdout.close()
        stderr = producer.stderr.read().decode(errors="replace") if producer.stderr is not None else ""
        ssh_returncode = producer.wait()
        if ssh_returncode != 0:
            raise RuntimeError(stderr.strip() or f"failed to fetch directory {remote_path}")
        if consumer.returncode != 0:
            raise RuntimeError((consumer.stderr or b"").decode(errors="replace").strip() or f"failed to extract {remote_path}")

    def sync_repo(self) -> None:
        self.ensure_started()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="vf-sync-", suffix=".tar", dir=self.state_dir, delete=False) as handle:
            archive_path = Path(handle.name)
        try:
            with tarfile.open(archive_path, "w") as archive:
                for root, dirs, files in os_walk(self.host_repo_root):
                    root_path = Path(root)
                    relative_root = root_path.relative_to(self.host_repo_root)
                    dirs[:] = [
                        name for name in dirs
                        if name not in {".cache", ".venv", "__pycache__"}
                    ]
                    for file_name in files:
                        if file_name == ".DS_Store":
                            continue
                        file_path = root_path / file_name
                        relative_path = relative_root / file_name
                        archive.add(file_path, arcname=str(relative_path))
            script = f"mkdir -p {shell_quote(self.metadata.guest_workspace)} && tar -xf - -C {shell_quote(self.metadata.guest_workspace)}"
            cmd = self._ssh_base() + [f"bash -lc {shell_quote(script)}"]
            with archive_path.open("rb") as handle:
                result = subprocess.run(cmd, stdin=handle, capture_output=True, check=False)
            if result.returncode != 0:
                output = (result.stdout or b"") + (result.stderr or b"")
                raise RuntimeError(output.decode(errors="replace").strip() or "failed to sync repo to guest")
        finally:
            archive_path.unlink(missing_ok=True)

    def ensure_started(self) -> None:
        if self._ssh_ready():
            return

        serial_log = Path(self.metadata.serial_log)
        serial_log.parent.mkdir(parents=True, exist_ok=True)
        pidfile = Path(self.metadata.pidfile)
        pidfile.parent.mkdir(parents=True, exist_ok=True)

        machine = f"q35,accel={self.metadata.accel}"
        cmd = [
            self.metadata.qemu_system,
            "-daemonize",
            "-pidfile",
            self.metadata.pidfile,
            "-machine",
            machine,
            "-cpu",
            "max",
            "-smp",
            str(self.metadata.cpus),
            "-m",
            str(self.metadata.memory_mib),
            "-display",
            "none",
            "-serial",
            f"file:{self.metadata.serial_log}",
            "-netdev",
            f"user,id=net0,hostfwd=tcp:127.0.0.1:{self.metadata.ssh_port}-:22",
            "-device",
            "virtio-net-pci,netdev=net0",
            "-drive",
            f"if=virtio,format=qcow2,file={self.metadata.disk_path}",
            "-cdrom",
            self.metadata.seed_iso_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            output = (result.stdout or "") + (result.stderr or "")
            raise RuntimeError(output.strip() or "failed to start QEMU guest")

        deadline = time.time() + 180
        while time.time() < deadline:
            if self._ssh_ready():
                return
            time.sleep(2)
        raise RuntimeError("QEMU guest did not become reachable over SSH")

    def _ssh_ready(self) -> bool:
        result = subprocess.run(
            self._ssh_base()
            + [
                "-o",
                "ConnectTimeout=5",
                "true",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def _ssh_base(self) -> list[str]:
        return [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "LogLevel=ERROR",
            "-i",
            self.metadata.ssh_key_path,
            "-p",
            str(self.metadata.ssh_port),
            f"{self.metadata.ssh_user}@127.0.0.1",
        ]

    def _run_ssh_shell(self, script: str, *, timeout: int | None = None) -> ExecResult:
        try:
            result = subprocess.run(
                self._ssh_base() + [f"bash -lc {shell_quote(script)}"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return ExecResult(
                returncode=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )
        except subprocess.TimeoutExpired as exc:
            return ExecResult(
                returncode=124,
                stdout=(exc.stdout or ""),
                stderr=((exc.stderr or "") + "\nTIMEOUT"),
            )


def create_execution_backend(runtime, cache_root: Path):
    if runtime.executor == "qemu":
        return QemuExecutionBackend(runtime, cache_root)
    return LocalExecutionBackend()


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def shlex_join(parts: list[str]) -> str:
    return " ".join(shell_quote(part) for part in parts)


def os_walk(root: Path):
    import os

    return os.walk(root)
