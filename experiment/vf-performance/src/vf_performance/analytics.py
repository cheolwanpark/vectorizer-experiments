"""Analytics for TUI and exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import BenchmarkAnalysis, RunResult


@dataclass
class OverviewStats:
    total_benchmarks: int
    analyzed_ok: int
    analyzed_failed: int
    total_runs: int
    completed_runs: int
    failed_runs: int
    cache_hits: int
    agreement_count: int


@dataclass
class BenchmarkRow:
    benchmark: str
    category: str
    loop_count: int
    vf_count: int
    default_cycles: int | None
    best_cost_vf: str | None
    best_cost: int | None
    best_latency_vf: str | None
    best_latency_cycles: int | None
    mismatch: bool


@dataclass
class CostLatencyRow:
    benchmark: str
    category: str
    loop_index: int
    best_cost_vf: str | None
    best_cost: int | None
    best_latency_vf: str | None
    best_latency_cycles: int | None
    matches: bool
    candidate_count: int


def compute_overview(analyses: list[BenchmarkAnalysis], runs: list[RunResult]) -> OverviewStats:
    agreement = 0
    for row in compute_cost_latency_rows(analyses, runs):
        if row.matches and row.best_cost_vf is not None:
            agreement += 1

    completed = sum(1 for run in runs if run.status in {"OK", "PASS"})
    failed = sum(1 for run in runs if run.status not in {"OK", "PASS"})
    return OverviewStats(
        total_benchmarks=len(analyses),
        analyzed_ok=sum(1 for item in analyses if not item.error),
        analyzed_failed=sum(1 for item in analyses if item.error),
        total_runs=len(runs),
        completed_runs=completed,
        failed_runs=failed,
        cache_hits=sum(1 for run in runs if run.cache_hit),
        agreement_count=agreement,
    )


def compute_benchmark_rows(
    analyses: list[BenchmarkAnalysis], runs: list[RunResult]
) -> list[BenchmarkRow]:
    rows: list[BenchmarkRow] = []
    run_map: dict[str, list[RunResult]] = {}
    for run in runs:
        run_map.setdefault(run.benchmark, []).append(run)

    for analysis in sorted(analyses, key=lambda item: item.benchmark):
        bench_runs = run_map.get(analysis.benchmark, [])
        baseline = next((run for run in bench_runs if run.mode == "default"), None)
        forced = [run for run in bench_runs if run.mode == "forced" and run.kernel_cycles is not None]
        best_cost_run = min(
            (run for run in forced if run.selected_cost is not None),
            key=lambda item: item.selected_cost,
            default=None,
        )
        best_latency_run = min(
            forced,
            key=lambda item: item.kernel_cycles if item.kernel_cycles is not None else float("inf"),
            default=None,
        )
        vf_values = {
            cost.vf
            for loop in analysis.loops
            for plan in loop.plans
            for cost in plan.costs
        }
        rows.append(
            BenchmarkRow(
                benchmark=analysis.benchmark,
                category=analysis.category,
                loop_count=len(analysis.loops),
                vf_count=len(vf_values),
                default_cycles=baseline.kernel_cycles if baseline else None,
                best_cost_vf=best_cost_run.selected_vf or best_cost_run.requested_vf if best_cost_run else None,
                best_cost=best_cost_run.selected_cost if best_cost_run else None,
                best_latency_vf=best_latency_run.selected_vf or best_latency_run.requested_vf if best_latency_run else None,
                best_latency_cycles=best_latency_run.kernel_cycles if best_latency_run else None,
                mismatch=bool(
                    best_cost_run
                    and best_latency_run
                    and (best_cost_run.selected_vf or best_cost_run.requested_vf)
                    != (best_latency_run.selected_vf or best_latency_run.requested_vf)
                ),
            )
        )
    return rows


def compute_cost_latency_rows(
    analyses: list[BenchmarkAnalysis], runs: Iterable[RunResult]
) -> list[CostLatencyRow]:
    run_groups: dict[tuple[str, int], list[RunResult]] = {}
    for run in runs:
        if run.mode != "forced" or run.loop_index is None or run.kernel_cycles is None:
            continue
        run_groups.setdefault((run.benchmark, run.loop_index), []).append(run)

    analysis_map = {item.benchmark: item for item in analyses}
    rows: list[CostLatencyRow] = []
    for (benchmark, loop_index), items in sorted(run_groups.items()):
        analysis = analysis_map.get(benchmark)
        category = analysis.category if analysis else "unknown"
        best_cost_run = min(
            (item for item in items if item.selected_cost is not None),
            key=lambda item: item.selected_cost,
            default=None,
        )
        best_latency_run = min(items, key=lambda item: item.kernel_cycles or float("inf"), default=None)
        rows.append(
            CostLatencyRow(
                benchmark=benchmark,
                category=category,
                loop_index=loop_index,
                best_cost_vf=best_cost_run.selected_vf or best_cost_run.requested_vf if best_cost_run else None,
                best_cost=best_cost_run.selected_cost if best_cost_run else None,
                best_latency_vf=best_latency_run.selected_vf or best_latency_run.requested_vf if best_latency_run else None,
                best_latency_cycles=best_latency_run.kernel_cycles if best_latency_run else None,
                matches=bool(
                    best_cost_run
                    and best_latency_run
                    and (best_cost_run.selected_vf or best_cost_run.requested_vf)
                    == (best_latency_run.selected_vf or best_latency_run.requested_vf)
                ),
                candidate_count=len(items),
            )
        )
    return rows


def build_run_detail(run: RunResult) -> str:
    lines = [
        f"Benchmark: {run.benchmark}",
        f"Category: {run.category}",
        f"Mode: {run.mode}",
        f"Loop: {run.loop_index if run.loop_index is not None else '-'}",
        f"Requested VF: {run.requested_vf or '-'}",
        f"Selected VF: {run.selected_vf or '-'}",
        f"Selected Plan: {run.selected_plan if run.selected_plan is not None else '-'}",
        f"Selected Cost: {run.selected_cost if run.selected_cost is not None else '-'}",
        f"Kernel Cycles: {run.kernel_cycles if run.kernel_cycles is not None else '-'}",
        f"Total Cycles: {run.total_cycles if run.total_cycles is not None else '-'}",
        f"Wall Time: {run.wall_time_s:.2f}s",
        f"Status: {run.status}",
        f"Cache Hit: {'yes' if run.cache_hit else 'no'}",
    ]
    if run.delta_vs_default is not None:
        lines.append(f"Delta vs Default: {run.delta_vs_default}")
    if run.speedup_vs_default is not None:
        lines.append(f"Speedup vs Default: {run.speedup_vs_default:.3f}")
    if run.message:
        lines.append(f"Message: {run.message}")
    if run.error:
        lines.append(f"Error: {run.error}")
    if run.artifact_path:
        lines.append(f"ELF: {run.artifact_path}")
    if run.log_path:
        lines.append(f"Log: {run.log_path}")
    if run.out_dir:
        lines.append(f"gem5 outdir: {run.out_dir}")
    if run.command:
        lines.extend(["", "--- Command ---", run.command])
    if run.stdout_excerpt:
        lines.extend(["", "--- Output ---", run.stdout_excerpt])
    return "\n".join(lines)


def build_analysis_detail(analysis: BenchmarkAnalysis) -> str:
    lines = [
        f"Benchmark: {analysis.benchmark}",
        f"Category: {analysis.category}",
        f"Source: {analysis.source_path}",
    ]
    if analysis.error:
        lines.append(f"Error: {analysis.error}")
    else:
        lines.append(f"Loops: {len(analysis.loops)}")
        for loop in analysis.loops:
            lines.append(f"  Loop[{loop.index}] path={loop.path} plans={loop.plan_count}")
            for plan in loop.plans:
                cost_summary = ", ".join(
                    f"{entry.vf}={entry.cost if entry.cost is not None else 'n/a'}"
                    for entry in plan.costs
                )
                lines.append(
                    f"    VPlan[{plan.index}] VFs={{{', '.join(plan.vfs)}}} costs=[{cost_summary}]"
                )
            if loop.selected_vf:
                lines.append(f"    selected VF={loop.selected_vf} plan={loop.selected_plan}")
    if analysis.raw_output:
        lines.extend(["", "--- Raw Output ---", analysis.raw_output[:4000]])
    return "\n".join(lines)
