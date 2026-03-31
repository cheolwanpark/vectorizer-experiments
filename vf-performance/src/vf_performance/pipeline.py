"""TSVC discovery, LLVM VPlan analysis, and gem5 batch execution."""

from __future__ import annotations

import concurrent.futures
import os
import re
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .build import BuildError, BuildManager
from .gem5 import parse_gem5_total_cycles, parse_tsvc_kernel_cycles
from .models import (
    AppRuntimeConfig,
    BenchmarkAnalysis,
    LoopAnalysis,
    RunResult,
    SessionData,
    VFCost,
    VFRunRequest,
    VPlan,
    VerificationResult,
)
from .qemu import create_execution_backend, default_executor, default_qemu_state_dir, load_qemu_metadata
from .storage import (
    analysis_cache_key,
    cache_root_from_runtime,
    load_cached_analysis,
    load_cached_run,
    run_cache_key,
    save_cached_analysis,
    save_cached_run,
)

PREVEC_PASSES = (
    "mem2reg,instcombine,simplifycfg,loop-simplify,lcssa,indvars,"
    "loop-rotate,instcombine,simplifycfg"
)
LOOP_HEADER_RE = re.compile(r"^LV: Loop\[(\d+)\] path=(\w+) plans=(\d+)$", re.M)
PLAN_HEADER_RE = re.compile(r"^LV:\s+VPlan\[(\d+)\] VFs=\{([^}]+)\}$", re.M)
COST_LINE_RE = re.compile(r"^LV:\s+VF=(.+?) cost=(\d+)$", re.M)
SELECTION_RE = re.compile(r"^LV:\s+selected VF=(.+?) plan=(\d+)$", re.M)
CATEGORY_RE = re.compile(r"TSVC Category:\s*(.+)")
VF_NUMBER_RE = re.compile(r"(\d+)(?!.*\d)")


@dataclass(frozen=True)
class BenchmarkSpec:
    benchmark: str
    source_path: Path
    category: str


ProgressCallback = Callable[[str, dict], None]


class RuntimeValidationError(RuntimeError):
    """Raised when required runtime prerequisites are missing."""

    def __init__(self, errors: list[str], hints: list[str] | None = None):
        self.errors = errors
        self.hints = hints or []
        lines = ["Runtime validation failed:"]
        lines.extend(f"- {item}" for item in errors)
        if self.hints:
            lines.append("")
            lines.append("Hints:")
            lines.extend(f"- {item}" for item in self.hints)
        super().__init__("\n".join(lines))


def _first_path(candidates: list[Path | None]) -> Path | None:
    for candidate in candidates:
        if candidate is not None:
            return candidate
    return None


def resolve_rvv_root(root: str | None = None) -> Path:
    if root:
        return Path(root).resolve()
    local = Path.cwd() / "rvv-poc-main"
    if local.exists():
        return local.resolve()
    return (Path(__file__).resolve().parents[2] / "rvv-poc-main").resolve()


def resolve_llvm_tools(
    llvm_custom: str | None,
    rvv_root: Path,
    *,
    sysroot: str | None = None,
    gem5: str | None = None,
) -> dict[str, str]:
    preferred_roots: list[Path] = []
    for raw in [
        llvm_custom,
        os.environ.get("LLVM_CUSTOM"),
        os.environ.get("LLVM_BIN_DIR"),
        os.environ.get("LLVM_BUILD_DIR"),
    ]:
        if not raw:
            continue
        base = Path(raw).resolve()
        preferred_roots.extend([base, base / "bin"])
    legacy_roots = [
        rvv_root / "llvm-build" / "bin",
        rvv_root / "llvm-build",
    ]

    tools: dict[str, str] = {}
    for tool_name in ("clang", "opt"):
        for base in preferred_roots + legacy_roots:
            tool_path = base / tool_name
            if tool_path.exists():
                tools[tool_name] = str(tool_path)
                break
        else:
            found = shutil.which(tool_name)
            if found:
                tools[tool_name] = found
            elif preferred_roots:
                tools[tool_name] = str(preferred_roots[0] / tool_name)
            else:
                tools[tool_name] = str(legacy_roots[0] / tool_name)

    gem5_candidates = [
        Path(gem5).resolve() if gem5 else None,
        Path(os.environ["GEM5_DIR"]).resolve() / "build" / "RISCV" / "gem5.opt"
        if os.environ.get("GEM5_DIR")
        else None,
        rvv_root / "gem5" / "build" / "RISCV" / "gem5.opt",
    ]
    gem5_path = _first_path(gem5_candidates)
    tools["gem5"] = str(gem5_path or (rvv_root / "gem5" / "build" / "RISCV" / "gem5.opt"))

    sysroot_candidates = [
        Path(sysroot).resolve() if sysroot else None,
        Path(os.environ["SYSROOT"]).resolve() if os.environ.get("SYSROOT") else None,
        (
            Path(os.environ["RISCV_TOOLS_PREFIX"]).resolve()
            / "riscv64-unknown-linux-gnu"
            / "sysroot"
        )
        if os.environ.get("RISCV_TOOLS_PREFIX")
        else None,
        (
            Path(os.environ["RVV_TOOLCHAIN_PREFIX"]).resolve()
            / "riscv64-unknown-linux-gnu"
            / "sysroot"
        )
        if os.environ.get("RVV_TOOLCHAIN_PREFIX")
        else None,
        rvv_root / "chipyard" / ".conda-env" / "riscv-tools" / "riscv64-unknown-linux-gnu" / "sysroot",
        rvv_root / "riscv-tools-install" / "riscv64-unknown-linux-gnu" / "sysroot",
    ]
    sysroot_path = _first_path(sysroot_candidates)
    tools["sysroot"] = str(
        sysroot_path or (rvv_root / "chipyard" / ".conda-env" / "riscv-tools" / "riscv64-unknown-linux-gnu" / "sysroot")
    )
    return tools


def default_runtime_executor(executor: str | None = None) -> str:
    return executor or default_executor()


def parse_category(source_path: Path) -> str:
    text = source_path.read_text(errors="replace")
    match = CATEGORY_RE.search(text)
    return match.group(1).strip() if match else "unknown"


def discover_benchmarks(rvv_root: Path, filters: list[str] | None = None) -> list[BenchmarkSpec]:
    filters = [item for item in (filters or []) if item]
    loop_dir = rvv_root / "benchmarks" / "TSVC_2" / "src" / "loops"
    specs: list[BenchmarkSpec] = []
    requested = set(filters)
    for source_path in sorted(loop_dir.glob("*.c")):
        benchmark = source_path.stem
        if requested and benchmark not in requested:
            continue
        specs.append(
            BenchmarkSpec(
                benchmark=benchmark,
                source_path=source_path,
                category=parse_category(source_path),
            )
        )
    return specs


def parse_vplan_output(text: str) -> list[LoopAnalysis]:
    loops: list[LoopAnalysis] = []
    starts = list(LOOP_HEADER_RE.finditer(text))
    if not starts:
        return loops

    for idx, loop_match in enumerate(starts):
        start = loop_match.start()
        end = starts[idx + 1].start() if idx + 1 < len(starts) else len(text)
        block = text[start:end]
        plans: list[VPlan] = []
        plan_matches = list(PLAN_HEADER_RE.finditer(block))
        for plan_idx, plan_match in enumerate(plan_matches):
            pstart = plan_match.start()
            pend = plan_matches[plan_idx + 1].start() if plan_idx + 1 < len(plan_matches) else len(block)
            plan_block = block[pstart:pend]
            vfs = [item.strip() for item in plan_match.group(2).split(",")]
            costs = [
                VFCost(vf=cost_match.group(1), cost=int(cost_match.group(2)))
                for cost_match in COST_LINE_RE.finditer(plan_block)
            ]
            if not costs:
                costs = [VFCost(vf=vf, cost=None) for vf in vfs]
            plans.append(
                VPlan(
                    index=int(plan_match.group(1)),
                    vfs=vfs,
                    costs=costs,
                )
            )

        selected_match = SELECTION_RE.search(block)
        loops.append(
            LoopAnalysis(
                index=int(loop_match.group(1)),
                path=loop_match.group(2),
                plan_count=int(loop_match.group(3)),
                plans=plans,
                selected_vf=selected_match.group(1) if selected_match else None,
                selected_plan=int(selected_match.group(2)) if selected_match else None,
            )
        )
    return loops


def encode_use_vf(vf: str) -> str:
    text = vf.strip().lower()
    match = VF_NUMBER_RE.search(text)
    if match is None:
        raise ValueError(f"unable to encode VF value: {vf}")
    scale = match.group(1)
    if "vscale" in text:
        return f"scalable:{scale}"
    return f"fixed:{scale}"


def build_forced_vf_arg(analysis: BenchmarkAnalysis, target_loop_index: int, forced_vf: str) -> str:
    encoded = encode_use_vf(forced_vf)
    if not analysis.loops:
        return encoded
    max_index = max(loop.index for loop in analysis.loops)
    if max_index == 0:
        return encoded
    entries = ["-"] * (max_index + 1)
    entries[target_loop_index] = encoded
    return ",".join(entries)


def requested_vfs_for_loop(loop: LoopAnalysis) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for plan in loop.plans:
        for vf in plan.vfs:
            if vf not in seen:
                seen.add(vf)
                ordered.append(vf)
    return ordered


def select_cost(loop: LoopAnalysis, selected_plan: int | None, selected_vf: str | None) -> int | None:
    if selected_plan is None or selected_vf is None:
        return None
    for plan in loop.plans:
        if plan.index != selected_plan:
            continue
        for cost in plan.costs:
            if cost.vf == selected_vf:
                return cost.cost
    return None


def benchmark_requests(analysis: BenchmarkAnalysis) -> list[VFRunRequest]:
    requests: list[VFRunRequest] = [
        VFRunRequest(
            benchmark=analysis.benchmark,
            source_path=analysis.source_path,
            category=analysis.category,
            loop_index=None,
            requested_vf=None,
            mode="default",
        )
    ]
    for loop in analysis.loops:
        for vf in requested_vfs_for_loop(loop):
            requests.append(
                VFRunRequest(
                    benchmark=analysis.benchmark,
                    source_path=analysis.source_path,
                    category=analysis.category,
                    loop_index=loop.index,
                    requested_vf=vf,
                    mode="forced",
                )
            )
    return requests


def _sysroot_has_header(sysroot: Path, header_name: str) -> bool:
    candidates = [
        sysroot / "usr" / "include" / header_name,
        sysroot / "include" / header_name,
        sysroot / "riscv64-unknown-linux-gnu" / "include" / header_name,
    ]
    if any(path.exists() for path in candidates):
        return True
    try:
        next(sysroot.rglob(header_name))
        return True
    except StopIteration:
        return False


def validate_runtime(runtime: AppRuntimeConfig) -> None:
    rvv_root = Path(runtime.rvv_root)
    loop_dir = rvv_root / "benchmarks" / "TSVC_2" / "src" / "loops"
    errors: list[str] = []

    if not rvv_root.exists():
        errors.append(f"RVV root not found: {rvv_root}")
    if not loop_dir.exists():
        errors.append(f"TSVC loop directory not found: {loop_dir}")

    if runtime.executor == "qemu":
        state_dir = Path(runtime.qemu_state_dir or default_qemu_state_dir(runtime.cache_dir))
        try:
            metadata = load_qemu_metadata(state_dir)
        except FileNotFoundError:
            errors.append(f"QEMU metadata not found: {state_dir / 'metadata.json'}")
        else:
            if not rvv_root.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
                errors.append(f"qemu executor requires rvv_root inside the current project checkout: {rvv_root}")
            for field_name in ("clang", "opt", "sysroot", "gem5"):
                if not metadata.tools.get(field_name):
                    errors.append(f"guest tool path missing in metadata: {field_name}")
            if not metadata.guest_workspace:
                errors.append("guest workspace missing in metadata")
            else:
                runtime.guest_workspace = metadata.guest_workspace
            backend = None
            if not errors:
                try:
                    backend = create_execution_backend(runtime, cache_root_from_runtime(runtime))
                    backend.prepare(sync_repo=False)
                except Exception as exc:
                    errors.append(f"QEMU guest is not reachable: {exc}")
                if backend is not None:
                    checks = {
                        "clang": metadata.tools.get("clang", ""),
                        "opt": metadata.tools.get("opt", ""),
                        "gem5": metadata.tools.get("gem5", ""),
                    }
                    for tool_name, tool_path in checks.items():
                        result = backend.run(["test", "-x", tool_path], cwd=None)
                        if result.returncode != 0:
                            errors.append(f"guest tool not found: {tool_name} -> {tool_path}")
                    sysroot_path = metadata.tools.get("sysroot", "")
                    result = backend.run(["test", "-d", sysroot_path], cwd=None)
                    if result.returncode != 0:
                        errors.append(f"guest sysroot not found: {sysroot_path}")
                    result = backend.run(
                        ["test", "-f", f"{Path(metadata.tools.get('gem5', '')).parent.parent.parent / 'configs' / 'example' / 'se.py'}"],
                        cwd=None,
                    )
                    if result.returncode != 0:
                        errors.append("guest gem5 SE config not found")
    else:
        sysroot = Path(runtime.tools.get("sysroot", ""))
        gem5 = Path(runtime.tools.get("gem5", ""))
        for tool_name in ("clang", "opt"):
            tool_path = runtime.tools.get(tool_name, "")
            if not tool_path:
                errors.append(f"{tool_name} path is empty")
                continue
            resolved = shutil.which(tool_path) if not os.path.isabs(tool_path) else tool_path
            if not resolved or not Path(resolved).exists():
                errors.append(f"{tool_name} not found: {tool_path}")

        if not sysroot.exists():
            errors.append(f"sysroot not found: {sysroot}")
        elif not _sysroot_has_header(sysroot, "math.h"):
            errors.append(f"sysroot is missing standard C headers (math.h not found): {sysroot}")

        if not gem5.exists():
            errors.append(f"gem5 binary not found: {gem5}")
        else:
            se_script = gem5.parent.parent.parent / "configs" / "example" / "se.py"
            if not se_script.exists():
                errors.append(f"gem5 SE config not found: {se_script}")

    if loop_dir.exists() and runtime.bench_filters:
        available = {path.stem for path in loop_dir.glob("*.c")}
        unknown = sorted({item for item in runtime.bench_filters if item not in available})
        if unknown:
            errors.append(f"unknown benchmarks requested: {', '.join(unknown)}")

    if errors:
        if runtime.executor == "qemu":
            hints = [
                f"From {Path(__file__).resolve().parents[2]}, run ./setup.sh",
                f"Then rerun vf-performance with --executor=qemu",
            ]
        else:
            hints = [
                f"From {rvv_root}, run ./build.sh",
                f"Then source {rvv_root / 'env.sh'}",
                f"Then from {rvv_root}, run ./build-sim.sh gem5",
            ]
        raise RuntimeValidationError(errors, hints=hints)


class PipelineRunner:
    """Run analysis and gem5 execution for all selected TSVC loops."""

    def __init__(
        self,
        runtime: AppRuntimeConfig,
        on_progress: ProgressCallback | None = None,
        backend=None,
    ):
        self.runtime = runtime
        self.on_progress = on_progress
        self.cache_root = cache_root_from_runtime(runtime)
        self.backend = backend or create_execution_backend(runtime, self.cache_root)
        self.build_manager = BuildManager(runtime, self.cache_root, backend=self.backend)
        self.work_dir = self.cache_root / "work"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._prevec_cache: dict[str, Path] = {}

    def cleanup(self) -> None:
        self.backend.cleanup()

    def run(self) -> SessionData:
        self.backend.prepare(sync_repo=self.runtime.executor == "qemu")
        benchmarks = discover_benchmarks(Path(self.runtime.rvv_root), self.runtime.bench_filters)
        analyses = self._run_analyses(benchmarks)
        total_runs = sum(len(benchmark_requests(item)) for item in analyses if not item.error)

        runs: list[RunResult] = []
        completed = 0
        for analysis in analyses:
            if analysis.error:
                continue

            baseline: RunResult | None = None
            for request in benchmark_requests(analysis):
                run_result = self._run_request(analysis, request, baseline)
                runs.append(run_result)
                if request.mode == "default":
                    baseline = run_result
                completed += 1
                self._emit(
                    "run_completed",
                    run=run_result,
                    completed=completed,
                    total=total_runs,
                )
        return SessionData(analyses=analyses, runs=runs)

    def _run_analyses(self, benchmarks: list[BenchmarkSpec]) -> list[BenchmarkAnalysis]:
        results: list[BenchmarkAnalysis] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, self.runtime.jobs)) as executor:
            future_map = {executor.submit(self._load_or_analyze, spec): spec for spec in benchmarks}
            completed = 0
            total = len(future_map)
            for future in concurrent.futures.as_completed(future_map):
                analysis = future.result()
                results.append(analysis)
                completed += 1
                self._emit(
                    "analysis_completed",
                    analysis=analysis,
                    completed=completed,
                    total=total,
                )
        return sorted(results, key=lambda item: item.benchmark)

    def _load_or_analyze(self, spec: BenchmarkSpec) -> BenchmarkAnalysis:
        key = analysis_cache_key(self.runtime, spec.benchmark, str(spec.source_path))
        if not self.runtime.no_cache:
            cached = load_cached_analysis(self.cache_root, key)
            if cached is not None:
                return cached
        analysis = self._analyze_one(spec)
        save_cached_analysis(self.cache_root, key, analysis)
        return analysis

    def _analyze_one(self, spec: BenchmarkSpec) -> BenchmarkAnalysis:
        try:
            prevec_path = self._ensure_prevec(spec)
            cmd = [
                self.runtime.tools["opt"],
                "-mtriple=riscv64-unknown-linux-gnu",
                "-mcpu=generic-rv64",
                "-mattr=+v",
                "-passes=loop-vectorize",
                "-vplan-explain",
                "-disable-output",
                self.backend.command_path(prevec_path),
            ]
            result = self.backend.run(cmd, cwd=Path(self.runtime.rvv_root))
            output = result.stderr or result.stdout
            if result.returncode != 0:
                raise RuntimeError(output.strip() or "opt failed")
            return BenchmarkAnalysis(
                benchmark=spec.benchmark,
                source_path=str(spec.source_path),
                category=spec.category,
                loops=parse_vplan_output(output),
                raw_output=output,
            )
        except BuildError as exc:
            return BenchmarkAnalysis(
                benchmark=spec.benchmark,
                source_path=str(spec.source_path),
                category=spec.category,
                loops=[],
                raw_output=exc.output[:4000],
                error=str(exc),
            )
        except Exception as exc:
            return BenchmarkAnalysis(
                benchmark=spec.benchmark,
                source_path=str(spec.source_path),
                category=spec.category,
                loops=[],
                raw_output="",
                error=str(exc),
            )

    def _ensure_prevec(self, spec: BenchmarkSpec) -> Path:
        if spec.benchmark in self._prevec_cache:
            return self._prevec_cache[spec.benchmark]
        ir_path = self.build_manager.compile_to_ir(spec.benchmark, spec.source_path, self.work_dir)
        prevec_path = self.work_dir / f"{spec.benchmark}.prevec.ll"
        if not prevec_path.exists():
            cmd = [
                self.runtime.tools["opt"],
                "-mtriple=riscv64-unknown-linux-gnu",
                "-mcpu=generic-rv64",
                "-mattr=+v",
                f"-passes={PREVEC_PASSES}",
                "-S",
                self.backend.command_path(ir_path),
                "-o",
                self.backend.command_path(prevec_path),
            ]
            result = self.backend.run(cmd, cwd=Path(self.runtime.rvv_root))
            if result.returncode != 0:
                output = result.stdout + result.stderr
                raise RuntimeError(output.strip() or "opt prevec failed")
            self.backend.materialize_file(prevec_path)
        self._prevec_cache[spec.benchmark] = prevec_path
        return prevec_path

    def _run_request(
        self,
        analysis: BenchmarkAnalysis,
        request: VFRunRequest,
        baseline: RunResult | None,
    ) -> RunResult:
        key = run_cache_key(
            self.runtime,
            request.benchmark,
            request.source_path,
            request.loop_index,
            request.requested_vf,
            request.mode,
        )
        if not self.runtime.no_cache:
            cached = load_cached_run(self.cache_root, key)
            if cached is not None:
                cached.cache_hit = True
                return self._with_baseline(cached, baseline)

        if request.mode == "default":
            run_result = self._execute_default(request)
        else:
            run_result = self._execute_forced(analysis, request, baseline)

        save_cached_run(self.cache_root, key, run_result)
        return self._with_baseline(run_result, baseline)

    def _execute_default(self, request: VFRunRequest) -> RunResult:
        return self._compile_and_run(request, selected_vf=None, selected_plan=None, selected_cost=None)

    def _execute_forced(
        self,
        analysis: BenchmarkAnalysis,
        request: VFRunRequest,
        baseline: RunResult | None,
    ) -> RunResult:
        verification = self._verify_forced_vf(analysis, request.loop_index, request.requested_vf)
        if verification.status != "ok":
            return RunResult(
                benchmark=request.benchmark,
                category=request.category,
                source_path=request.source_path,
                loop_index=request.loop_index,
                requested_vf=request.requested_vf,
                mode=request.mode,
                selected_vf=verification.selected_vf,
                selected_plan=verification.selected_plan,
                selected_cost=verification.selected_cost,
                kernel_cycles=None,
                total_cycles=None,
                wall_time_s=0.0,
                status="VERIFY_FAIL",
                command=verification.command,
                artifact_path=None,
                log_path=None,
                out_dir=None,
                message=verification.message,
                error=None,
                stdout_excerpt=verification.raw_output[:4000],
            )
        return self._compile_and_run(
            request,
            selected_vf=verification.selected_vf,
            selected_plan=verification.selected_plan,
            selected_cost=verification.selected_cost,
            forced_vf_arg=build_forced_vf_arg(analysis, request.loop_index or 0, request.requested_vf or ""),
        )

    def _verify_forced_vf(
        self,
        analysis: BenchmarkAnalysis,
        loop_index: int | None,
        requested_vf: str | None,
    ) -> VerificationResult:
        if loop_index is None or requested_vf is None:
            raise ValueError("forced verification requires loop_index and requested_vf")
        spec = BenchmarkSpec(
            benchmark=analysis.benchmark,
            source_path=Path(analysis.source_path),
            category=analysis.category,
        )
        prevec_path = self._ensure_prevec(spec)
        vf_arg = build_forced_vf_arg(analysis, loop_index, requested_vf)
        cmd = [
            self.runtime.tools["opt"],
            "-mtriple=riscv64-unknown-linux-gnu",
            "-mcpu=generic-rv64",
            "-mattr=+v",
            "-passes=loop-vectorize",
            "-vplan-explain",
            "-disable-output",
            f"-vplan-use-vf={vf_arg}",
            self.backend.command_path(prevec_path),
        ]
        result = self.backend.run(cmd, cwd=Path(self.runtime.rvv_root))
        output = result.stderr or result.stdout
        if result.returncode != 0:
            return VerificationResult(
                benchmark=analysis.benchmark,
                loop_index=loop_index,
                requested_vf=requested_vf,
                selected_vf=None,
                selected_plan=None,
                selected_cost=None,
                status="error",
                message=output.strip() or "opt verification failed",
                raw_output=output,
                command=shlex.join(cmd),
            )

        loops = parse_vplan_output(output)
        target_loop = next((item for item in loops if item.index == loop_index), None)
        if target_loop is None:
            return VerificationResult(
                benchmark=analysis.benchmark,
                loop_index=loop_index,
                requested_vf=requested_vf,
                selected_vf=None,
                selected_plan=None,
                selected_cost=None,
                status="error",
                message=f"Loop[{loop_index}] not found in verification output",
                raw_output=output,
                command=shlex.join(cmd),
            )

        selected_cost = select_cost(target_loop, target_loop.selected_plan, target_loop.selected_vf)
        selected_vf = target_loop.selected_vf
        status = "ok" if selected_vf == requested_vf else "mismatch"
        message = None
        if status != "ok":
            message = f"requested {requested_vf}, selected {selected_vf or '-'}"
        return VerificationResult(
            benchmark=analysis.benchmark,
            loop_index=loop_index,
            requested_vf=requested_vf,
            selected_vf=selected_vf,
            selected_plan=target_loop.selected_plan,
            selected_cost=selected_cost,
            status=status,
            message=message,
            raw_output=output,
            command=shlex.join(cmd),
        )

    def _compile_and_run(
        self,
        request: VFRunRequest,
        *,
        selected_vf: str | None,
        selected_plan: int | None,
        selected_cost: int | None,
        forced_vf_arg: str | None = None,
    ) -> RunResult:
        cache_key = run_cache_key(
            self.runtime,
            request.benchmark,
            request.source_path,
            request.loop_index,
            request.requested_vf,
            request.mode,
        )
        log_path = self.cache_root / "logs" / f"{cache_key}.log"
        gem5_out_dir = self.cache_root / "gem5-out" / cache_key
        artifact_path: Path | None = None
        link_command = ""
        try:
            artifact_path, link_command = self.build_manager.build_binary(
                request.benchmark,
                Path(request.source_path),
                cache_key,
                forced_vf_arg=forced_vf_arg,
            )
            status, output, wall_time, total_cycles = self._run_gem5(artifact_path, gem5_out_dir)
            log_path.write_text(output)
            kernel_cycles = parse_tsvc_kernel_cycles(output)
            return RunResult(
                benchmark=request.benchmark,
                category=request.category,
                source_path=request.source_path,
                loop_index=request.loop_index,
                requested_vf=request.requested_vf,
                mode=request.mode,
                selected_vf=selected_vf,
                selected_plan=selected_plan,
                selected_cost=selected_cost,
                kernel_cycles=kernel_cycles,
                total_cycles=total_cycles,
                wall_time_s=wall_time,
                status=status,
                command=link_command,
                artifact_path=str(artifact_path),
                log_path=str(log_path),
                out_dir=str(gem5_out_dir),
                stdout_excerpt=output[:4000],
            )
        except BuildError as exc:
            log_path.write_text(exc.output)
            return RunResult(
                benchmark=request.benchmark,
                category=request.category,
                source_path=request.source_path,
                loop_index=request.loop_index,
                requested_vf=request.requested_vf,
                mode=request.mode,
                selected_vf=selected_vf,
                selected_plan=selected_plan,
                selected_cost=selected_cost,
                kernel_cycles=None,
                total_cycles=None,
                wall_time_s=0.0,
                status="BUILD_FAIL",
                command=exc.command,
                artifact_path=str(artifact_path) if artifact_path else None,
                log_path=str(log_path),
                out_dir=str(gem5_out_dir),
                error=str(exc),
                stdout_excerpt=exc.output[:4000],
            )
        except Exception as exc:
            if not log_path.exists():
                log_path.write_text(str(exc))
            return RunResult(
                benchmark=request.benchmark,
                category=request.category,
                source_path=request.source_path,
                loop_index=request.loop_index,
                requested_vf=request.requested_vf,
                mode=request.mode,
                selected_vf=selected_vf,
                selected_plan=selected_plan,
                selected_cost=selected_cost,
                kernel_cycles=None,
                total_cycles=None,
                wall_time_s=0.0,
                status="RUN_FAIL",
                command=link_command,
                artifact_path=str(artifact_path) if artifact_path else None,
                log_path=str(log_path),
                out_dir=str(gem5_out_dir),
                error=str(exc),
                stdout_excerpt=str(exc)[:4000],
            )

    def _run_gem5(self, artifact_path: Path, out_dir: Path) -> tuple[str, str, float, int | None]:
        gem5_path = self.runtime.tools["gem5"]
        se_script = str(Path(gem5_path).parent.parent.parent / "configs" / "example" / "se.py")
        cmd = [
            gem5_path,
            f"--outdir={self.backend.command_path(out_dir)}",
            se_script,
            f"--cpu-type={self.runtime.gem5_cpu_type}",
            f"--cmd={self.backend.command_path(artifact_path)}",
        ]

        start = time.time()
        result = self.backend.run(cmd, cwd=Path(self.runtime.rvv_root), timeout=600)
        wall_time = time.time() - start

        if self.runtime.executor == "qemu":
            self.backend.materialize_dir(out_dir)
        stats_path = out_dir / "stats.txt"
        stats_text = stats_path.read_text(errors="replace") if stats_path.exists() else None
        output = result.stdout + result.stderr
        total_cycles = parse_gem5_total_cycles(output, stats_text)

        status = "OK"
        if result.returncode == 124 or "TIMEOUT" in output:
            status = "TIMEOUT"
        elif result.returncode != 0:
            status = f"EXIT:{result.returncode}"
        return status, output, wall_time, total_cycles

    def _with_baseline(self, run_result: RunResult, baseline: RunResult | None) -> RunResult:
        if baseline is None or run_result.mode == "default":
            return run_result
        if baseline.kernel_cycles is None or run_result.kernel_cycles is None:
            return run_result
        run_result.delta_vs_default = run_result.kernel_cycles - baseline.kernel_cycles
        if run_result.kernel_cycles > 0:
            run_result.speedup_vs_default = baseline.kernel_cycles / run_result.kernel_cycles
        return run_result

    def _emit(self, kind: str, **payload: object) -> None:
        if self.on_progress:
            self.on_progress(kind, payload)


def default_runtime_config(args, rvv_root: Path, tools: dict[str, str]) -> AppRuntimeConfig:
    cache_dir = str((Path.cwd() / ".cache" / "vf-performance").resolve())
    return AppRuntimeConfig(
        rvv_root=str(rvv_root),
        llvm_custom=args.llvm_custom,
        len_1d=args.len,
        jobs=args.jobs or max(1, min(os.cpu_count() or 4, 8)),
        sim_jobs=args.sim_jobs,
        bench_filters=args.bench or [],
        no_cache=args.no_cache,
        cache_dir=cache_dir,
        tools=tools,
        executor=default_runtime_executor(getattr(args, "executor", None)),
        qemu_state_dir=getattr(args, "qemu_state_dir", None) or str(default_qemu_state_dir(cache_dir)),
        gem5_cpu_type="MinorCPU",
    )
