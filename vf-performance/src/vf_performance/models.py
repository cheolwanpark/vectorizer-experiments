"""Data models for VF analysis and gem5 execution results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class VFCost:
    vf: str
    cost: int | None


@dataclass
class VPlan:
    index: int
    vfs: list[str]
    costs: list[VFCost]


@dataclass
class LoopAnalysis:
    index: int
    path: str
    plan_count: int
    plans: list[VPlan]
    selected_vf: str | None = None
    selected_plan: int | None = None


@dataclass
class BenchmarkAnalysis:
    benchmark: str
    source_path: str
    category: str
    loops: list[LoopAnalysis]
    raw_output: str
    error: str | None = None


@dataclass
class VFRunRequest:
    benchmark: str
    source_path: str
    category: str
    loop_index: int | None
    requested_vf: str | None
    mode: str


@dataclass
class VerificationResult:
    benchmark: str
    loop_index: int | None
    requested_vf: str | None
    selected_vf: str | None
    selected_plan: int | None
    selected_cost: int | None
    status: str
    message: str | None
    raw_output: str
    command: str


@dataclass
class RunResult:
    benchmark: str
    category: str
    source_path: str
    loop_index: int | None
    requested_vf: str | None
    mode: str
    selected_vf: str | None
    selected_plan: int | None
    selected_cost: int | None
    kernel_cycles: int | None
    total_cycles: int | None
    wall_time_s: float
    status: str
    command: str
    artifact_path: str | None
    log_path: str | None
    out_dir: str | None
    message: str | None = None
    error: str | None = None
    cache_hit: bool = False
    stdout_excerpt: str = ""
    delta_vs_default: int | None = None
    speedup_vs_default: float | None = None


@dataclass
class SessionData:
    analyses: list[BenchmarkAnalysis] = field(default_factory=list)
    runs: list[RunResult] = field(default_factory=list)


@dataclass
class AppRuntimeConfig:
    rvv_root: str
    llvm_custom: str | None
    len_1d: int
    jobs: int
    sim_jobs: int
    bench_filters: list[str]
    no_cache: bool
    cache_dir: str
    tools: dict[str, str]
    gem5_cpu_type: str = "MinorCPU"


def _vfcost_from_dict(data: dict[str, Any]) -> VFCost:
    return VFCost(vf=data["vf"], cost=data.get("cost"))


def _vplan_from_dict(data: dict[str, Any]) -> VPlan:
    return VPlan(
        index=data["index"],
        vfs=list(data.get("vfs", [])),
        costs=[_vfcost_from_dict(item) for item in data.get("costs", [])],
    )


def _loop_from_dict(data: dict[str, Any]) -> LoopAnalysis:
    return LoopAnalysis(
        index=data["index"],
        path=data["path"],
        plan_count=data["plan_count"],
        plans=[_vplan_from_dict(item) for item in data.get("plans", [])],
        selected_vf=data.get("selected_vf"),
        selected_plan=data.get("selected_plan"),
    )


def analysis_from_dict(data: dict[str, Any]) -> BenchmarkAnalysis:
    return BenchmarkAnalysis(
        benchmark=data["benchmark"],
        source_path=data["source_path"],
        category=data.get("category", "unknown"),
        loops=[_loop_from_dict(item) for item in data.get("loops", [])],
        raw_output=data.get("raw_output", ""),
        error=data.get("error"),
    )


def run_from_dict(data: dict[str, Any]) -> RunResult:
    return RunResult(
        benchmark=data["benchmark"],
        category=data.get("category", "unknown"),
        source_path=data.get("source_path", ""),
        loop_index=data.get("loop_index"),
        requested_vf=data.get("requested_vf"),
        mode=data["mode"],
        selected_vf=data.get("selected_vf"),
        selected_plan=data.get("selected_plan"),
        selected_cost=data.get("selected_cost"),
        kernel_cycles=data.get("kernel_cycles"),
        total_cycles=data.get("total_cycles"),
        wall_time_s=float(data.get("wall_time_s", 0.0)),
        status=data.get("status", "UNKNOWN"),
        command=data.get("command", ""),
        artifact_path=data.get("artifact_path"),
        log_path=data.get("log_path"),
        out_dir=data.get("out_dir"),
        message=data.get("message"),
        error=data.get("error"),
        cache_hit=bool(data.get("cache_hit", False)),
        stdout_excerpt=data.get("stdout_excerpt", ""),
        delta_vs_default=data.get("delta_vs_default"),
        speedup_vs_default=data.get("speedup_vs_default"),
    )


def to_dict(value: Any) -> dict[str, Any]:
    return asdict(value)
