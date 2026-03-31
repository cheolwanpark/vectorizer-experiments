"""Compilation helpers for TSVC_2 loop binaries."""

from __future__ import annotations

import hashlib
import shlex
from pathlib import Path

from .models import AppRuntimeConfig
from .qemu import LocalExecutionBackend
from .storage import tool_version

TARGET = "riscv64-unknown-linux-gnu"
MARCH = "rv64gcv"
MABI = "lp64d"


class BuildError(RuntimeError):
    """Raised when a compile or link step fails."""

    def __init__(self, message: str, command: str, output: str):
        super().__init__(message)
        self.command = command
        self.output = output

    def __str__(self) -> str:
        tail = self.output.strip().splitlines()
        detail = tail[-1] if tail else ""
        if detail:
            return f"{super().__str__()}: {detail}"
        return super().__str__()


class BuildManager:
    """Build TSVC_2 support objects and per-loop binaries."""

    def __init__(self, runtime: AppRuntimeConfig, cache_root: Path, backend=None):
        self.runtime = runtime
        self.cache_root = cache_root
        self.rvv_root = Path(runtime.rvv_root)
        self.tsvc_src_dir = self.rvv_root / "benchmarks" / "TSVC_2" / "src"
        self.sysroot = self._resolve_sysroot()
        self.clang = runtime.tools["clang"]
        self.backend = backend or LocalExecutionBackend()
        self._support_dir = cache_root / "artifacts" / self._support_key()
        self._support_objects: list[Path] | None = None

    def _resolve_sysroot(self) -> Path:
        raw_sysroot = self.runtime.tools.get("sysroot")
        if raw_sysroot:
            return Path(raw_sysroot)
        return (
            self.rvv_root
            / "riscv-tools-install"
            / "riscv64-unknown-linux-gnu"
            / "sysroot"
        )

    def _support_key(self) -> str:
        payload = "|".join(
            [
                str(self.runtime.len_1d),
                self.clang,
                tool_version(self.clang),
                str(self.sysroot),
            ]
        )
        return f"support-{hashlib.sha256(payload.encode()).hexdigest()[:16]}"

    def common_flags(self, *, linker: bool = False) -> list[str]:
        flags = [
            self.clang,
            "-std=c99",
            "-target",
            TARGET,
            f"--sysroot={self.sysroot}",
            f"-march={MARCH}",
            f"-mabi={MABI}",
            f"-DLEN_1D={self.runtime.len_1d}",
            "-DTSVC_MEASURE_CYCLES",
            f"-I{self.tsvc_src_dir}",
        ]
        if linker:
            flags.append("-fuse-ld=lld")
        return flags

    def _support_compile_flags(self) -> list[str]:
        return self.common_flags() + [
            "-O2",
            "-fno-vectorize",
            "-fno-slp-vectorize",
            "-c",
        ]

    def _loop_compile_flags(self) -> list[str]:
        return self.common_flags() + [
            "-O3",
            "-fstrict-aliasing",
            "-ffp-contract=fast",
            "-c",
        ]

    def ensure_support_objects(self) -> list[Path]:
        if self._support_objects is not None:
            return self._support_objects

        self._support_dir.mkdir(parents=True, exist_ok=True)
        support_sources = [
            self.tsvc_src_dir / "dummy.c",
            self.tsvc_src_dir / "common.c",
            self.tsvc_src_dir / "data.c",
            self.tsvc_src_dir / "single_runner.c",
        ]
        built: list[Path] = []
        for source in support_sources:
            output = self._support_dir / f"{source.stem}.o"
            if not output.exists():
                cmd = self._support_compile_flags() + [self._cmd_path(source), "-o", self._cmd_path(output)]
                self._run_checked(cmd, cwd=self.tsvc_src_dir)
            built.append(output)
        self._support_objects = built
        return built

    def build_binary(
        self,
        benchmark: str,
        source_path: Path,
        cache_key: str,
        forced_vf_arg: str | None = None,
    ) -> tuple[Path, str]:
        build_dir = self.cache_root / "artifacts" / cache_key
        build_dir.mkdir(parents=True, exist_ok=True)
        support_objects = self.ensure_support_objects()
        loop_object = build_dir / f"{benchmark}.o"
        elf_path = build_dir / f"{benchmark}.elf"

        loop_cmd = self._loop_compile_flags()
        if forced_vf_arg:
            loop_cmd.extend(["-mllvm", f"-vplan-use-vf={forced_vf_arg}"])
        loop_cmd.extend([self._cmd_path(source_path), "-o", self._cmd_path(loop_object)])
        self._run_checked(loop_cmd, cwd=self.tsvc_src_dir)

        link_cmd = self.common_flags(linker=True) + [
            "-static",
            *(self._cmd_path(item) for item in support_objects),
            self._cmd_path(loop_object),
            "-lm",
            "-o",
            self._cmd_path(elf_path),
        ]
        self._run_checked(link_cmd, cwd=self.tsvc_src_dir)
        self.backend.materialize_file(elf_path)
        return elf_path, shlex.join(link_cmd)

    def compile_to_ir(self, benchmark: str, source_path: Path, work_dir: Path) -> Path:
        ir_path = work_dir / f"{benchmark}.ll"
        if ir_path.exists():
            return ir_path
        cmd = self.common_flags() + [
            "-O0",
            "-Xclang",
            "-disable-O0-optnone",
            "-S",
            "-emit-llvm",
            self._cmd_path(source_path),
            "-o",
            self._cmd_path(ir_path),
        ]
        self._run_checked(cmd, cwd=self.tsvc_src_dir)
        self.backend.materialize_file(ir_path)
        return ir_path

    def _run_checked(self, cmd: list[str], cwd: Path) -> None:
        result = self.backend.run(cmd, cwd=cwd)
        if result.returncode == 0:
            return
        output = result.stdout + result.stderr
        raise BuildError("command failed", shlex.join(cmd), output)

    def _cmd_path(self, path: Path) -> str:
        return self.backend.command_path(path)
