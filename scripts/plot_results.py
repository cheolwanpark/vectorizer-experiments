#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import math
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_VFS_DB = "artifacts/vfs.db"
DEFAULT_OUTPUT_ROOT = "artifacts/plots"
DEFAULT_TOP_MISMATCH_BENCHES = 8
SUSPECT_COMPARE_ABS_THRESHOLD = 1_000_000.0
SUSPECT_COMPARE_RATIO_THRESHOLD = 100_000.0


def fail(message: str, exit_code: int = 2) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a single-file HTML report from vplan and emulate SQLite outputs."
    )
    parser.add_argument("--vfs-db", default=DEFAULT_VFS_DB, help="Path to artifacts/vfs.db")
    parser.add_argument(
        "--result-db",
        required=True,
        help="Path to emulate-result-*.sqlite or profile-result-*.sqlite",
    )
    parser.add_argument(
        "--output-html",
        default="",
        help="Output HTML path (defaults to artifacts/plots/<result-db-stem>.html)",
    )
    parser.add_argument(
        "--bench",
        action="append",
        default=[],
        help="Optional benchmark filter; may be passed more than once",
    )
    parser.add_argument(
        "--top-mismatch-benches",
        type=int,
        default=DEFAULT_TOP_MISMATCH_BENCHES,
        help="Deprecated compatibility flag; ignored.",
    )
    return parser.parse_args()


def resolve_input_path(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (root / value).resolve()
    if not path.exists():
        fail(f"input file not found: {path}")
    return path


def resolve_output_html(root: Path, explicit_path: str, result_db: Path) -> Path:
    if explicit_path:
        out_path = Path(explicit_path)
        if not out_path.is_absolute():
            out_path = (root / explicit_path).resolve()
    else:
        out_path = (root / DEFAULT_OUTPUT_ROOT / f"{result_db.stem}.html").resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def parse_cost(value: str) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_vf_factor(value: str) -> int | None:
    text = value.strip()
    if text.startswith("fixed:") or text.startswith("scalable:"):
        try:
            factor = int(text.split(":", 1)[1])
        except ValueError:
            return None
        return factor if factor > 0 else None
    return None


def parse_effective_cost(raw_cost: str, use_vf: str) -> float | None:
    cost = parse_cost(raw_cost)
    if cost is None:
        return None
    vf_factor = parse_vf_factor(use_vf)
    if vf_factor is None:
        return None
    return cost / vf_factor


def parse_vf_key(value: str) -> tuple[int, int, str]:
    text = value.strip()
    if text.startswith("fixed:"):
        return (0, int(text.split(":", 1)[1]), text)
    if text.startswith("scalable:"):
        return (1, int(text.split(":", 1)[1]), text)
    return (2, 0, text)


def display_vf(value: str) -> str:
    return value if value.strip() else "default"


def median(values: Sequence[float]) -> float:
    return float(statistics.median(values))


def dense_rank(values: dict[str, float]) -> dict[str, int]:
    ordered = sorted(values.items(), key=lambda item: (item[1], parse_vf_key(item[0])))
    rank_map: dict[str, int] = {}
    previous_value: float | None = None
    current_rank = 0
    for key, value in ordered:
        if previous_value is None or value != previous_value:
            current_rank += 1
            previous_value = value
        rank_map[key] = current_rank
    return rank_map


def pearson_correlation(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    x_den = math.sqrt(sum((x - x_mean) ** 2 for x in xs))
    y_den = math.sqrt(sum((y - y_mean) ** 2 for y in ys))
    if x_den == 0.0 or y_den == 0.0:
        return None
    return num / (x_den * y_den)


def linear_regression(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float, float | None] | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0.0:
        return None
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denom
    intercept = y_mean - slope * x_mean
    total_var = sum((y - y_mean) ** 2 for y in ys)
    if total_var == 0.0:
        r_squared = None
    else:
        residual_var = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
        r_squared = max(0.0, 1.0 - (residual_var / total_var))
    return slope, intercept, r_squared


def escape(value: object) -> str:
    return html.escape(str(value))




@dataclass
class VFCandidate:
    bench: str
    use_vf: str
    raw_vf: str
    raw_cost: str
    raw_compare: str
    compare: float | None
    selected: bool


@dataclass
class VPlanFailure:
    bench: str
    failure: str
    failure_message: str


@dataclass
class EmulateAggregate:
    bench: str
    use_vf: str
    kernel_samples: list[float]
    total_samples: list[float]

    def metric_samples(self, metric_name: str) -> list[float]:
        if metric_name == "kernel_cycles":
            return self.kernel_samples
        if metric_name == "total_cycles":
            return self.total_samples
        raise KeyError(metric_name)


@dataclass
class MetricPoint:
    bench: str
    use_vf: str
    selected: bool
    raw_cost: str
    raw_compare: str
    compare: float | None
    samples: list[float]
    median_value: float
    min_value: float
    max_value: float
    n_success: int
    compare_rank: int | None = None
    actual_rank: int | None = None


@dataclass
class BenchMetricSummary:
    bench: str
    metric_name: str
    points: list[MetricPoint]
    selected_vf: str | None
    compare_best_vf: str | None
    actual_best_vf: str | None
    max_abs_rank_delta: int | None
    selected_rank_delta: int | None
    spearman: float | None


@dataclass
class ReportData:
    vfs_db: Path
    result_db: Path
    result_stage: str
    result_target: str
    benches: list[str]
    candidates: dict[tuple[str, str], VFCandidate]
    candidate_counts: dict[str, int]
    vplan_failures: list[VPlanFailure]
    emulate_aggregates: dict[tuple[str, str], EmulateAggregate]
    emulate_failure_counts: Counter[str]
    metric_summaries: dict[str, list[BenchMetricSummary]]


def load_vfs_data(
    db_path: Path, bench_filter: set[str]
) -> tuple[dict[tuple[str, str], VFCandidate], dict[str, int], list[VPlanFailure]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(vfs)").fetchall()}
    has_compare = "compare" in columns
    select_compare = ", compare" if has_compare else ""
    rows = conn.execute(
        f"""
        SELECT bench, use_vf, raw_vf, cost{select_compare}, selected, failure, failure_message
        FROM vfs
        ORDER BY bench, use_vf
        """
    ).fetchall()
    conn.close()

    candidates: dict[tuple[str, str], VFCandidate] = {}
    candidate_counts: dict[str, int] = defaultdict(int)
    failures: list[VPlanFailure] = []
    for row in rows:
        bench = str(row["bench"])
        if bench_filter and bench not in bench_filter:
            continue
        failure = str(row["failure"] or "")
        use_vf = str(row["use_vf"] or "")
        if failure:
            failures.append(
                VPlanFailure(
                    bench=bench,
                    failure=failure,
                    failure_message=str(row["failure_message"] or ""),
                )
            )
            continue
        if not use_vf:
            continue
        candidates[(bench, use_vf)] = VFCandidate(
            bench=bench,
            use_vf=use_vf,
            raw_vf=str(row["raw_vf"] or ""),
            raw_cost=str(row["cost"] or ""),
            raw_compare=str(row["compare"] or "") if has_compare else "",
            compare=(
                parse_cost(str(row["compare"] or ""))
                if has_compare and str(row["compare"] or "").strip()
                else parse_effective_cost(str(row["cost"] or ""), use_vf)
            ),
            selected=bool(int(row["selected"] or 0)),
        )
        candidate_counts[bench] += 1
    return candidates, dict(candidate_counts), failures


_RESULT_STAGES = {"emulate", "profile"}


def load_result_metadata(db_path: Path) -> tuple[str, str]:
    """Return (stage, simulator_target) from the first non-vplan result row."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT stage, simulator_target FROM emulate_results "
        "WHERE stage IN ('emulate', 'profile') LIMIT 1"
    ).fetchone()
    conn.close()
    if row is None:
        return ("unknown", "unknown")
    return (str(row["stage"] or "unknown"), str(row["simulator_target"] or "unknown"))


def load_emulate_data(
    db_path: Path, bench_filter: set[str]
) -> tuple[dict[tuple[str, str], EmulateAggregate], Counter[str]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT stage, failure, bench, use_vf, kernel_cycles, total_cycles
        FROM emulate_results
        ORDER BY bench, use_vf
        """
    ).fetchall()
    conn.close()

    aggregates: dict[tuple[str, str], EmulateAggregate] = {}
    failure_counts: Counter[str] = Counter()
    for row in rows:
        if str(row["stage"] or "") not in _RESULT_STAGES:
            continue
        bench = str(row["bench"] or "")
        if bench_filter and bench not in bench_filter:
            continue
        failure = str(row["failure"] or "")
        if failure:
            failure_counts[failure] += 1
            continue
        use_vf = str(row["use_vf"] or "")
        key = (bench, use_vf)
        aggregate = aggregates.setdefault(
            key,
            EmulateAggregate(bench=bench, use_vf=use_vf, kernel_samples=[], total_samples=[]),
        )
        if row["kernel_cycles"] is not None:
            aggregate.kernel_samples.append(float(row["kernel_cycles"]))
        if row["total_cycles"] is not None:
            aggregate.total_samples.append(float(row["total_cycles"]))
    return aggregates, failure_counts


def build_metric_summaries(
    metric_name: str,
    candidates: dict[tuple[str, str], VFCandidate],
    aggregates: dict[tuple[str, str], EmulateAggregate],
) -> list[BenchMetricSummary]:
    points_by_bench: dict[str, list[MetricPoint]] = defaultdict(list)
    for (bench, use_vf), aggregate in aggregates.items():
        samples = aggregate.metric_samples(metric_name)
        if not samples:
            continue
        candidate = candidates.get((bench, use_vf))
        points_by_bench[bench].append(
            MetricPoint(
                bench=bench,
                use_vf=use_vf,
                selected=candidate.selected if candidate is not None else False,
                raw_cost=candidate.raw_cost if candidate is not None else "",
                raw_compare=candidate.raw_compare if candidate is not None else "",
                compare=candidate.compare if candidate is not None else None,
                samples=list(samples),
                median_value=median(samples),
                min_value=min(samples),
                max_value=max(samples),
                n_success=len(samples),
            )
        )

    summaries: list[BenchMetricSummary] = []
    for bench, points in sorted(points_by_bench.items()):
        selected_vf = next((point.use_vf for point in points if point.selected), None)
        rankable = [point for point in points if point.compare is not None]
        compare_best_vf = None
        actual_best_vf = None
        max_abs_rank_delta = None
        selected_rank_delta = None
        spearman = None
        if rankable:
            compare_rank_map = dense_rank({point.use_vf: float(point.compare) for point in rankable})
            actual_rank_map = dense_rank({point.use_vf: point.median_value for point in rankable})
            compare_best_vf = min(
                rankable, key=lambda point: (float(point.compare), parse_vf_key(point.use_vf))
            ).use_vf
            actual_best_vf = min(
                rankable, key=lambda point: (point.median_value, parse_vf_key(point.use_vf))
            ).use_vf
            deltas: list[int] = []
            ordered_compare_ranks: list[float] = []
            ordered_actual_ranks: list[float] = []
            for point in rankable:
                point.compare_rank = compare_rank_map[point.use_vf]
                point.actual_rank = actual_rank_map[point.use_vf]
                delta = point.actual_rank - point.compare_rank
                deltas.append(abs(delta))
                if point.use_vf == selected_vf:
                    selected_rank_delta = delta
                ordered_compare_ranks.append(float(point.compare_rank))
                ordered_actual_ranks.append(float(point.actual_rank))
            max_abs_rank_delta = max(deltas) if deltas else None
            spearman = pearson_correlation(ordered_compare_ranks, ordered_actual_ranks)
        else:
            actual_best_vf = min(
                points, key=lambda point: (point.median_value, parse_vf_key(point.use_vf))
            ).use_vf

        summaries.append(
            BenchMetricSummary(
                bench=bench,
                metric_name=metric_name,
                points=sorted(points, key=lambda point: parse_vf_key(point.use_vf)),
                selected_vf=selected_vf,
                compare_best_vf=compare_best_vf,
                actual_best_vf=actual_best_vf,
                max_abs_rank_delta=max_abs_rank_delta,
                selected_rank_delta=selected_rank_delta,
                spearman=spearman,
            )
        )
    return summaries


def load_report_data(vfs_db: Path, result_db: Path, bench_filter: set[str]) -> ReportData:
    candidates, candidate_counts, vplan_failures = load_vfs_data(vfs_db, bench_filter)
    result_stage, result_target = load_result_metadata(result_db)
    aggregates, emulate_failure_counts = load_emulate_data(result_db, bench_filter)
    metric_summaries = {
        "kernel_cycles": build_metric_summaries("kernel_cycles", candidates, aggregates),
        "total_cycles": build_metric_summaries("total_cycles", candidates, aggregates),
    }
    benches = sorted(
        {
            *candidate_counts.keys(),
            *(failure.bench for failure in vplan_failures),
            *(bench for bench, _ in aggregates.keys()),
        }
    )
    return ReportData(
        vfs_db=vfs_db,
        result_db=result_db,
        result_stage=result_stage,
        result_target=result_target,
        benches=benches,
        candidates=candidates,
        candidate_counts=candidate_counts,
        vplan_failures=vplan_failures,
        emulate_aggregates=aggregates,
        emulate_failure_counts=emulate_failure_counts,
        metric_summaries=metric_summaries,
    )


def build_coverage_data(data: ReportData) -> dict:
    emulate_success_benches = {bench for bench, _ in data.emulate_aggregates}
    candidate_benches = set(data.candidate_counts.keys())
    vplan_failure_by_bench: dict[str, str] = {}
    for failure in data.vplan_failures:
        vplan_failure_by_bench.setdefault(failure.bench, failure.failure)

    outcome: Counter[str] = Counter()
    for bench in data.benches:
        if bench in emulate_success_benches:
            outcome["Success"] += 1
        elif bench in candidate_benches:
            outcome[f"{data.result_stage.capitalize()} failed"] += 1
        elif bench in vplan_failure_by_bench:
            outcome[f"vplan: {vplan_failure_by_bench[bench]}"] += 1
        else:
            outcome["Unknown"] += 1

    candidate_dist: dict[str, int] = {}
    if data.candidate_counts:
        dist = Counter(data.candidate_counts.values())
        candidate_dist = {str(k): dist[k] for k in sorted(dist)}

    return {
        "outcome": dict(outcome),
        "candidate_distribution": candidate_dist,
    }


def rankable_points(summary: BenchMetricSummary) -> list[MetricPoint]:
    return [
        point
        for point in summary.points
        if point.compare_rank is not None and point.actual_rank is not None and point.compare is not None
    ]


def select_top_n_vfs(summary: BenchMetricSummary, n: int, *, by: str) -> set[str]:
    rankable = rankable_points(summary)
    if len(rankable) < n:
        return set()
    if by == "compare":
        ordered = sorted(rankable, key=lambda point: (float(point.compare), parse_vf_key(point.use_vf)))
    elif by == "latency":
        ordered = sorted(rankable, key=lambda point: (point.median_value, parse_vf_key(point.use_vf)))
    else:
        raise KeyError(by)
    return {point.use_vf for point in ordered[:n]}


def build_top_n_overlap_distributions(
    summaries: Iterable[BenchMetricSummary],
    *,
    max_n: int = 4,
) -> tuple[list[int], list[list[float]], list[int]]:
    summary_list = list(summaries)
    ns: list[int] = []
    distributions: list[list[float]] = []
    eligible_counts: list[int] = []
    for n in range(1, max_n + 1):
        ratios: list[float] = []
        for summary in summary_list:
            rankable = rankable_points(summary)
            if len(rankable) < n:
                continue
            predicted = select_top_n_vfs(summary, n, by="compare")
            actual = select_top_n_vfs(summary, n, by="latency")
            ratios.append(len(predicted & actual) / n)
        if not ratios:
            continue
        ns.append(n)
        distributions.append(ratios)
        eligible_counts.append(len(ratios))
    return ns, distributions, eligible_counts


def is_suspect_compare_outlier(point: MetricPoint) -> bool:
    if point.compare is None or point.compare < SUSPECT_COMPARE_ABS_THRESHOLD:
        return False
    effective_cost = parse_effective_cost(point.raw_cost, point.use_vf)
    if effective_cost is None or effective_cost <= 0.0:
        return False
    return (point.compare / effective_cost) >= SUSPECT_COMPARE_RATIO_THRESHOLD


def count_suspect_compare_outliers(summaries: Iterable[BenchMetricSummary]) -> int:
    return sum(
        1
        for summary in summaries
        for point in summary.points
        if point.compare is not None and is_suspect_compare_outlier(point)
    )


def list_plottable_benches(data: ReportData) -> list[str]:
    metric_maps = [
        {summary.bench: summary for summary in data.metric_summaries["kernel_cycles"]},
        {summary.bench: summary for summary in data.metric_summaries["total_cycles"]},
    ]
    benches: list[str] = []
    for bench in data.benches:
        if any(metric_map.get(bench) and metric_map[bench].points for metric_map in metric_maps):
            benches.append(bench)
    return benches


def build_scatter_data(
    summaries: list[BenchMetricSummary],
) -> dict:
    point_data: list[dict] = []
    for summary in summaries:
        for point in summary.points:
            if point.compare is None:
                continue
            vf_factor = parse_vf_factor(point.use_vf)
            vf_type = "fixed" if point.use_vf.startswith("fixed:") else "scalable"
            point_data.append(
                {
                    "x": point.compare,
                    "y": point.median_value,
                    "bench": point.bench,
                    "vf": point.use_vf,
                    "vfFactor": vf_factor,
                    "vfType": vf_type,
                    "isScalar": vf_factor == 1,
                    "selected": point.selected,
                    "suspect": is_suspect_compare_outlier(point),
                }
            )

    all_vfs = sorted({p["vf"] for p in point_data}, key=parse_vf_key)
    return {"points": point_data, "allVFs": all_vfs}


def build_ranking_data(metric_summaries: dict[str, list[BenchMetricSummary]]) -> dict:
    metric_names = ["kernel_cycles", "total_cycles"]
    spearman: dict[str, list[dict]] = {}
    for name in metric_names:
        spearman[name] = [
            {"bench": summary.bench, "value": summary.spearman}
            for summary in metric_summaries[name]
            if summary.spearman is not None
        ]

    overlap: dict[str, list[dict]] = {}
    for name in metric_names:
        ns, distributions, eligible_counts = build_top_n_overlap_distributions(
            metric_summaries[name]
        )
        buckets: list[dict] = []
        for n, ratios, count in zip(ns, distributions, eligible_counts):
            segments: list[dict] = []
            for overlap_count in range(0, n + 1):
                ratio_value = overlap_count / n
                bucket_count = sum(
                    1
                    for ratio in ratios
                    if math.isclose(ratio, ratio_value, rel_tol=1e-9, abs_tol=1e-9)
                )
                if bucket_count > 0:
                    segments.append(
                        {"overlap": overlap_count, "n": n, "share": bucket_count / count}
                    )
            buckets.append({"n": n, "eligible": count, "segments": segments})
        overlap[name] = buckets

    return {"spearman": spearman, "overlap": overlap}


def build_speedup_data(metric_summaries: dict[str, list[BenchMetricSummary]]) -> dict:
    result: dict[str, list[dict]] = {}
    for metric_name, summaries in metric_summaries.items():
        entries: list[dict] = []
        for summary in summaries:
            default_point: MetricPoint | None = None
            best_non_default: MetricPoint | None = None
            for point in summary.points:
                if not point.use_vf.strip():
                    default_point = point
                elif best_non_default is None or point.median_value < best_non_default.median_value:
                    best_non_default = point
            if default_point is None or best_non_default is None:
                continue
            if default_point.median_value <= 0:
                continue
            ratio = 1.0 - (best_non_default.median_value / default_point.median_value)
            ratio = max(0.0, min(1.0, ratio))
            entries.append(
                {
                    "bench": summary.bench,
                    "speedup": round(ratio, 4),
                    "bestVF": best_non_default.use_vf,
                    "defaultCycles": round(default_point.median_value),
                    "bestCycles": round(best_non_default.median_value),
                }
            )
        entries.sort(key=lambda e: -e["speedup"])
        result[metric_name] = entries
    return result


def build_bench_detail_data(
    summary: BenchMetricSummary | None,
) -> list[dict]:
    if summary is None or not summary.points:
        return []
    ordered = sorted(
        summary.points,
        key=lambda point: (point.median_value, parse_vf_key(point.use_vf)),
    )
    return [
        {
            "vf": point.use_vf,
            "label": display_vf(point.use_vf),
            "median": point.median_value,
            "min": point.min_value,
            "max": point.max_value,
            "compare": point.compare,
            "selected": point.selected,
        }
        for point in ordered
    ]


def metric_label(metric_name: str) -> str:
    if metric_name == "kernel_cycles":
        return "kernel_cycles"
    if metric_name == "total_cycles":
        return "total_cycles"
    return metric_name


def format_float(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def build_summary_cards(data: ReportData) -> list[tuple[str, str]]:
    kernel_summaries = data.metric_summaries["kernel_cycles"]
    comparable = [summary for summary in kernel_summaries if summary.actual_best_vf is not None]
    selected_matches = [
        summary
        for summary in comparable
        if summary.selected_vf and summary.selected_vf == summary.actual_best_vf
    ]
    kernel_spearmans = [summary.spearman for summary in kernel_summaries if summary.spearman is not None]
    avg_spearman = sum(kernel_spearmans) / len(kernel_spearmans) if kernel_spearmans else None
    top1_ns, top1_distributions, _ = build_top_n_overlap_distributions(kernel_summaries, max_n=1)
    top1_overlap = (sum(top1_distributions[0]) / len(top1_distributions[0])) if top1_ns and top1_distributions else None
    kernel_suspect_outliers = count_suspect_compare_outliers(kernel_summaries)
    outlier_suffix = "" if kernel_suspect_outliers == 1 else "s"
    speedup_ratios: list[float] = []
    for summary in kernel_summaries:
        default_pt = next((p for p in summary.points if not p.use_vf.strip()), None)
        best_nd = min(
            (p for p in summary.points if p.use_vf.strip()),
            key=lambda p: p.median_value,
            default=None,
        )
        if default_pt and best_nd and default_pt.median_value > 0:
            speedup_ratios.append(
                max(0.0, min(1.0, 1.0 - best_nd.median_value / default_pt.median_value))
            )
    median_speedup = format_float(
        statistics.median(speedup_ratios) if speedup_ratios else None, digits=2
    )
    stage_label = data.result_stage.capitalize()
    return [
        ("Stage", data.result_stage),
        ("Target", data.result_target),
        ("Benchmarks", str(len(data.benches))),
        ("Kernel comparable benches", str(len(comparable))),
        ("VPlan failures", str(len(data.vplan_failures))),
        (f"{stage_label} failures", str(sum(data.emulate_failure_counts.values()))),
        ("Selected VF matches actual best", f"{len(selected_matches)}/{len(comparable) or 0}"),
        ("Mean kernel Spearman", format_float(avg_spearman, digits=2)),
        ("Kernel top-1 overlap", format_float(top1_overlap, digits=2)),
        ("Median kernel speedup", median_speedup),
        ("Kernel scatter fit exclusions", f"{kernel_suspect_outliers} suspect compare outlier{outlier_suffix}"),
    ]


def build_detail_summary_text(summary: BenchMetricSummary | None, metric_name: str) -> str:
    if summary is None:
        return f"{metric_name}: no successful result rows"
    return (
        f"{metric_name}: selected={display_vf(summary.selected_vf) if summary.selected_vf is not None else '-'}, "
        f"compare-best={display_vf(summary.compare_best_vf) if summary.compare_best_vf is not None else '-'}, "
        f"latency-best={display_vf(summary.actual_best_vf) if summary.actual_best_vf is not None else '-'}, "
        f"spearman={format_float(summary.spearman, digits=2)}"
    )


_CSS = """
:root {
  color-scheme: light;
  --bg: #faf9f6;
  --bg-subtle: #f3f1ec;
  --card: #ffffff;
  --ink: #1c1c1e;
  --muted: #6b7280;
  --line: #e5e3de;
  --accent: #2563eb;
  --accent-2: #dc2626;
  --accent-3: #059669;
  --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
}
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  line-height: 1.6;
}
.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 24px;
  height: 48px;
  background: var(--card);
  border-bottom: 1px solid var(--line);
  box-shadow: var(--shadow);
}
.nav-title {
  font-weight: 600;
  font-size: 15px;
  white-space: nowrap;
}
.nav-links {
  display: flex;
  gap: 4px;
  overflow-x: auto;
}
.nav-link {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--muted);
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.nav-link:hover {
  background: var(--bg-subtle);
  color: var(--ink);
}
main {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px;
}
h1 {
  margin: 0 0 4px 0;
  font-size: 28px;
  font-weight: 600;
}
h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
}
h3 {
  margin: 16px 0 6px 0;
  font-size: 17px;
  font-weight: 600;
}
.subtitle {
  margin: 0 0 16px 0;
  color: var(--muted);
}
p { color: var(--muted); }
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  margin: 16px 0 24px 0;
}
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px 14px;
  box-shadow: var(--shadow);
}
.card-title {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 4px;
}
.card-value {
  font-size: 15px;
  font-weight: 600;
  word-break: break-word;
}
.section {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 18px;
  box-shadow: var(--shadow);
  overflow: hidden;
}
.section-accent { border-top: 2px solid var(--muted); }
.section-accent-kernel { border-top: 2px solid var(--accent); }
.section-accent-total { border-top: 2px solid var(--accent-2); }
.caption {
  margin-top: -2px;
  margin-bottom: 12px;
  font-size: 13px;
}
.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.chart-row > div {
  min-height: 320px;
}
.bench-picker {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin-bottom: 16px;
}
#bench-search {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 14px;
  font: inherit;
  font-size: 15px;
  background: #fff;
  color: var(--ink);
}
.bench-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.bench-btn {
  display: inline-block;
  padding: 6px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  color: var(--ink);
  font: inherit;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}
.bench-btn:hover { background: var(--bg-subtle); }
.bench-btn.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.bench-btn.hidden-btn { display: none; }
.hidden { display: none; }
.empty { padding: 12px 0 0 0; }
.bench-detail {
  background: var(--bg-subtle);
  border-radius: 10px;
  padding: 16px;
  margin-top: 14px;
}
.vf-toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 8px 0 12px 0;
  align-items: center;
}
.vf-toggle-btn, .vf-group-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  transition: opacity 0.12s;
  user-select: none;
}
.vf-toggle-btn { opacity: 0.35; }
.vf-toggle-btn.active { opacity: 1; font-weight: 600; }
.vf-group-btn { background: var(--bg-subtle); font-size: 12px; }
.vf-group-btn:hover { background: var(--line); }
.vf-sep { width: 1px; height: 22px; background: var(--line); margin: 0 4px; }
.vf-swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}
.scatter-stats {
  font-size: 13px;
  color: var(--muted);
  margin-top: 6px;
}
@media (max-width: 720px) {
  main { padding: 14px; }
  .section { padding: 14px; }
  .chart-row { grid-template-columns: 1fr; }
  .bench-picker { grid-template-columns: 1fr; }
  .top-nav { padding: 0 14px; }
}
"""

_APP_JS = r"""
(function() {
  'use strict';
  var D = JSON.parse(document.getElementById('report-data').textContent);
  var BASE = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: '#ffffff',
    font: {family: 'system-ui, -apple-system, sans-serif', size: 14, color: '#1c1c1e'},
    xaxis: {gridcolor: '#f0eeea', linecolor: '#e5e3de', tickfont: {size: 13, color: '#6b7280'}},
    yaxis: {gridcolor: '#f0eeea', linecolor: '#e5e3de', tickfont: {size: 13, color: '#6b7280'}},
    hoverlabel: {bgcolor: '#fff', bordercolor: '#e5e3de', font: {size: 14}},
    margin: {t: 36, r: 20, b: 50, l: 60}
  };
  var CFG = {responsive: true, displayModeBar: false};

  // -- Coverage pie charts --
  (function() {
    var outcome = D.coverage.outcome;
    var labels = Object.keys(outcome);
    var values = labels.map(function(k){return outcome[k];});
    var palette = ['#059669','#b45309','#dc2626','#9333ea','#c2410c','#be185d','#6d28d9','#0369a1'];
    var colors = labels.map(function(l, i){return i === 0 ? '#059669' : palette[1 + ((i-1) % (palette.length-1))];});
    var total = values.reduce(function(a,b){return a+b;}, 0);
    if (total === 0) {
      document.getElementById('chart-outcome').innerHTML = '<p style="color:#6b7280;padding:40px">No data.</p>';
    } else {
      Plotly.newPlot('chart-outcome', [{
        type: 'pie',
        labels: labels, values: values,
        marker: {colors: colors},
        textinfo: 'label+value+percent',
        textfont: {size: 14},
        hovertemplate: '%{label}: %{value} (%{percent})<extra></extra>',
        hole: 0.35,
        sort: false
      }], Object.assign({}, BASE, {
        title: {text: 'Pipeline outcomes', x: 0, font: {size: 16}},
        legend: {font: {size: 13}},
        margin: {t: 48, r: 20, b: 20, l: 20}
      }), CFG);
    }
  })();
  (function() {
    var dist = D.coverage.candidate_distribution;
    var counts = Object.keys(dist);
    if (!counts.length) {
      document.getElementById('chart-vf-distribution').innerHTML = '<p style="color:#6b7280;padding:40px">No candidate rows available.</p>';
      return;
    }
    var labels = counts.map(function(c){return c + ' VFs';});
    var values = counts.map(function(c){return dist[c];});
    Plotly.newPlot('chart-vf-distribution', [{
      type: 'pie',
      labels: labels, values: values,
      textinfo: 'label+value+percent',
      textfont: {size: 14},
      hovertemplate: '%{label}: %{value} benches (%{percent})<extra></extra>',
      hole: 0.35,
      sort: false
    }], Object.assign({}, BASE, {
      title: {text: 'VF candidates per bench', x: 0, font: {size: 16}},
      legend: {font: {size: 13}},
      margin: {t: 48, r: 20, b: 20, l: 20}
    }), CFG);
  })();

  // -- Scatter charts --
  function vfColor(factor, allVFs) {
    if (factor === 1) return '#999999';
    var factors = allVFs.map(function(v){var f=parseInt(v.split(':')[1]);return f>1?f:2;});
    var maxLog = Math.log2(Math.max.apply(null, factors));
    var minLog = 1;
    var t = maxLog > minLog ? (Math.log2(factor) - minLog) / (maxLog - minLog) : 0.5;
    t = Math.max(0, Math.min(1, t));
    var r = Math.round(191 - t * 161);
    var g = Math.round(219 - t * 161);
    var b = Math.round(254 - t * 116);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }

  function linReg(pts) {
    if (pts.length < 2) return null;
    var xM = 0, yM = 0;
    pts.forEach(function(p){xM+=p.x;yM+=p.y;});
    xM /= pts.length; yM /= pts.length;
    var num = 0, den = 0;
    pts.forEach(function(p){den+=(p.x-xM)*(p.x-xM);num+=(p.x-xM)*(p.y-yM);});
    if (den === 0) return null;
    var slope = num / den, intercept = yM - slope * xM;
    var totVar = 0, resVar = 0;
    pts.forEach(function(p){
      totVar += (p.y-yM)*(p.y-yM);
      resVar += (p.y-(slope*p.x+intercept))*(p.y-(slope*p.x+intercept));
    });
    var r2 = totVar === 0 ? null : Math.max(0, 1 - resVar / totVar);
    return {slope: slope, intercept: intercept, r2: r2};
  }

  function renderScatter(metricKey, containerId) {
    var sd = D.scatter[metricKey];
    var data = sd.points;
    var allVFs = sd.allVFs;
    if (!data.length) {
      document.getElementById(containerId).innerHTML = '<p style="color:#6b7280;padding:40px">No rows with both cost and latency.</p>';
      return;
    }
    var enabledVFs = {};
    allVFs.forEach(function(v){enabledVFs[v]=true;});

    function buildResult() {
      var traces = [];
      var byVF = {};
      data.forEach(function(p){
        if (!enabledVFs[p.vf]) return;
        if (!byVF[p.vf]) byVF[p.vf] = [];
        byVF[p.vf].push(p);
      });
      allVFs.forEach(function(vf){
        var pts = byVF[vf];
        if (!pts) return;
        var factor = parseInt(vf.split(':')[1]);
        var type = vf.split(':')[0];
        traces.push({
          type: 'scattergl', mode: 'markers', name: vf,
          x: pts.map(function(p){return p.x;}),
          y: pts.map(function(p){return p.y;}),
          text: pts.map(function(p){
            var t = p.bench + '<br>VF: ' + p.vf + '<br>compare: ' + p.x.toLocaleString() + '<br>median: ' + p.y.toLocaleString();
            if (p.selected) t += '<br><b>(LLVM selected)</b>';
            if (p.suspect) t += '<br><i>suspect outlier</i>';
            return t;
          }),
          hoverinfo: 'text',
          marker: {
            size: 10,
            color: vfColor(factor, allVFs),
            symbol: type === 'scalable' ? 'diamond' : 'circle',
            line: {width: pts.map(function(p){return p.suspect?2:0.5;}), color: pts.map(function(p){return p.suspect?'#dc2626':'rgba(0,0,0,0.2)';})}
          }
        });
      });

      // axis range from non-suspect points only
      var visible = data.filter(function(p){return enabledVFs[p.vf];});
      var nonSuspect = visible.filter(function(p){return !p.suspect;});
      var rangeSrc = nonSuspect.length > 0 ? nonSuspect : visible;
      var xVals = rangeSrc.map(function(p){return p.x;});
      var yVals = rangeSrc.map(function(p){return p.y;});
      var xMin = Math.min.apply(null, xVals), xMax = Math.max.apply(null, xVals);
      var yMin = Math.min.apply(null, yVals), yMax = Math.max.apply(null, yVals);
      var xPad = (xMax - xMin) * 0.06 || 1, yPad = (yMax - yMin) * 0.06 || 1;
      var axisRange = {
        xRange: [xMin - xPad, xMax + xPad],
        yRange: [yMin - yPad, yMax + yPad]
      };

      // regression line
      var fitPts = nonSuspect.length > 0 ? nonSuspect : visible;
      var reg = linReg(fitPts);
      var excluded = visible.length - (nonSuspect.length > 0 ? nonSuspect.length : 0);
      if (reg) {
        var fxMin = Math.min.apply(null, fitPts.map(function(p){return p.x;}));
        var fxMax = Math.max.apply(null, fitPts.map(function(p){return p.x;}));
        var label = 'fit';
        if (reg.r2 !== null) label += ' R\u00b2=' + reg.r2.toFixed(2);
        traces.push({
          type: 'scattergl', mode: 'lines', name: label,
          x: [fxMin, fxMax],
          y: [reg.slope * fxMin + reg.intercept, reg.slope * fxMax + reg.intercept],
          line: {color: '#888', width: 2, dash: 'dash'},
          hoverinfo: 'skip'
        });
      }

      // stats
      var statsEl = document.getElementById('scatter-stats-' + metricKey);
      var parts = [visible.length + ' points'];
      if (reg && reg.r2 !== null) parts.push('R\u00b2=' + reg.r2.toFixed(3));
      if (excluded > 0) parts.push(excluded + ' suspect outlier' + (excluded===1?'':'s') + ' excluded from fit');
      statsEl.textContent = parts.join(' \u00b7 ');

      return {traces: traces, axisRange: axisRange};
    }

    var layout = Object.assign({}, BASE, {
      height: 600,
      showlegend: true,
      legend: {font: {size: 13}, bgcolor: 'rgba(255,255,255,0.85)', bordercolor: '#e5e3de', borderwidth: 1, xanchor: 'right', x: 1, yanchor: 'top', y: 1},
      xaxis: Object.assign({}, BASE.xaxis, {title: {text: 'VPlan compare'}}),
      yaxis: Object.assign({}, BASE.yaxis, {title: {text: 'Median latency (cycles)'}})
    });

    function applyResult(r) {
      layout.xaxis.range = r.axisRange.xRange;
      layout.xaxis.autorange = false;
      layout.yaxis.range = r.axisRange.yRange;
      layout.yaxis.autorange = false;
    }
    var initial = buildResult();
    applyResult(initial);
    Plotly.newPlot(containerId, initial.traces, layout, CFG);

    // VF toggle buttons
    var row = document.getElementById('vf-toggles-' + metricKey);
    function mkBtn(text, cls, onClick) {
      var b = document.createElement('button');
      b.textContent = text; b.className = cls;
      b.addEventListener('click', onClick);
      row.appendChild(b);
      return b;
    }
    function refresh() {
      syncBtns();
      var r = buildResult();
      applyResult(r);
      Plotly.react(containerId, r.traces, layout, CFG);
    }
    mkBtn('All', 'vf-group-btn', function(){allVFs.forEach(function(v){enabledVFs[v]=true;});refresh();});
    mkBtn('Scalar', 'vf-group-btn', function(){allVFs.forEach(function(v){enabledVFs[v]=(v==='fixed:1');});refresh();});
    mkBtn('Vectorized', 'vf-group-btn', function(){allVFs.forEach(function(v){enabledVFs[v]=(parseInt(v.split(':')[1])>1);});refresh();});
    var sep = document.createElement('div'); sep.className = 'vf-sep'; row.appendChild(sep);

    var vfBtns = {};
    allVFs.forEach(function(vf){
      var factor = parseInt(vf.split(':')[1]);
      var type = vf.split(':')[0];
      var btn = document.createElement('button');
      btn.className = 'vf-toggle-btn active';
      var sw = document.createElement('span'); sw.className = 'vf-swatch';
      sw.style.background = vfColor(factor, allVFs);
      if (type === 'scalable') {sw.style.borderRadius='0';sw.style.transform='rotate(45deg)';}
      btn.appendChild(sw);
      btn.appendChild(document.createTextNode(' ' + vf));
      btn.addEventListener('click', function(){enabledVFs[vf]=!enabledVFs[vf];refresh();});
      row.appendChild(btn);
      vfBtns[vf] = btn;
    });
    function syncBtns() {
      allVFs.forEach(function(vf){
        if(enabledVFs[vf]) vfBtns[vf].classList.add('active');
        else vfBtns[vf].classList.remove('active');
      });
    }
  }
  renderScatter('kernel_cycles', 'chart-scatter-kernel_cycles');
  renderScatter('total_cycles', 'chart-scatter-total_cycles');

  // -- Ranking charts --
  (function() {
    var rank = D.ranking;
    var metrics = ['kernel_cycles', 'total_cycles'];
    var colors = {kernel_cycles: '#dc2626', total_cycles: '#2563eb'};

    // Spearman box + jitter
    var spearmanTraces = [];
    metrics.forEach(function(m) {
      var entries = rank.spearman[m];
      if (!entries.length) return;
      spearmanTraces.push({
        type: 'box', name: m,
        y: entries.map(function(e){return e.value;}),
        text: entries.map(function(e){return e.bench;}),
        boxpoints: 'all', jitter: 0.4, pointpos: 0,
        hovertemplate: '%{text}<br>Spearman: %{y:.3f}<extra>%{fullData.name}</extra>',
        marker: {color: colors[m], size: 6, opacity: 0.7},
        line: {color: colors[m]},
        fillcolor: colors[m] + '30'
      });
    });
    if (spearmanTraces.length) {
      Plotly.newPlot('chart-spearman', spearmanTraces, Object.assign({}, BASE, {
        title: {text: 'Per-bench Spearman distribution', x: 0, font: {size: 16}},
        yaxis: Object.assign({}, BASE.yaxis, {title: {text: 'Spearman rank correlation'}, autorange: true}),
        showlegend: false,
        shapes: [{type: 'line', x0: -0.5, x1: metrics.length - 0.5, y0: 0, y1: 0, line: {color: '#999', width: 1, dash: 'dot'}}]
      }), CFG);
    } else {
      document.getElementById('chart-spearman').innerHTML = '<p style="color:#6b7280;padding:40px">No rankable benches available.</p>';
    }

    // Top-N overlap stacked bar (drawn as shapes for exact positioning)
    var rdYlGn = ['#d73027','#f46d43','#fdae61','#fee08b','#d9ef8b','#a6d96a','#66bd63','#1a9850'];
    function overlapColor(overlap, n) {
      var t = n > 0 ? overlap / n : 0;
      var idx = Math.round(t * (rdYlGn.length - 1));
      return rdYlGn[Math.max(0, Math.min(rdYlGn.length - 1, idx))];
    }
    var shapes = [];
    var hasOverlap = false;
    var annotations = [];
    var halfW = 0.16;
    metrics.forEach(function(m, mi) {
      var buckets = rank.overlap[m];
      var offset = mi === 0 ? -0.18 : 0.18;
      buckets.forEach(function(b) {
        hasOverlap = true;
        var cx = b.n + offset;
        var bottom = 0;
        b.segments.forEach(function(seg) {
          shapes.push({
            type: 'rect', xref: 'x', yref: 'y',
            x0: cx - halfW, x1: cx + halfW,
            y0: bottom, y1: bottom + seg.share,
            fillcolor: overlapColor(seg.overlap, seg.n),
            line: {color: colors[m], width: 1.1}
          });
          if (seg.share >= 0.11) {
            annotations.push({
              x: cx, y: bottom + seg.share / 2,
              text: seg.overlap + '/' + seg.n,
              showarrow: false, font: {size: 14, color: '#222'}
            });
          }
          bottom += seg.share;
        });
        annotations.push({
          x: cx, y: 1.02,
          text: 'n=' + b.eligible,
          showarrow: false, font: {size: 14, color: colors[m]}
        });
      });
    });
    if (hasOverlap) {
      // legend entries for the two metrics
      var legendTraces = metrics.map(function(m) {
        return {
          type: 'scatter', mode: 'markers', name: m,
          x: [null], y: [null],
          marker: {size: 12, color: '#ddd', line: {color: colors[m], width: 2}, symbol: 'square'}
        };
      });
      Plotly.newPlot('chart-topn', legendTraces, Object.assign({}, BASE, {
        title: {text: 'Top-N overlap distribution (Top-1~4)', x: 0, font: {size: 16}},
        xaxis: Object.assign({}, BASE.xaxis, {
          title: {text: 'Top-N'},
          tickvals: [1,2,3,4], ticktext: ['Top-1','Top-2','Top-3','Top-4'],
          range: [0.5, 4.5]
        }),
        yaxis: Object.assign({}, BASE.yaxis, {title: {text: 'Bench share'}, range: [0, 1.08]}),
        shapes: shapes,
        annotations: annotations,
        legend: {font: {size: 13}}
      }), CFG);
    } else {
      document.getElementById('chart-topn').innerHTML = '<p style="color:#6b7280;padding:40px">No rankable benches available.</p>';
    }
  })();

  // -- Potential Speedup box + jitter --
  (function() {
    var colors = {kernel_cycles: '#dc2626', total_cycles: '#2563eb'};
    var metrics = ['kernel_cycles', 'total_cycles'];
    var traces = [];
    metrics.forEach(function(m) {
      var entries = D.speedup[m];
      if (!entries || !entries.length) return;
      traces.push({
        type: 'box', name: m,
        y: entries.map(function(e){return e.speedup;}),
        text: entries.map(function(e){
          return e.bench + '<br>speedup: ' + (e.speedup * 100).toFixed(1) + '%'
              + '<br>best VF: ' + e.bestVF
              + '<br>default: ' + e.defaultCycles.toLocaleString() + ' cycles'
              + '<br>best: ' + e.bestCycles.toLocaleString() + ' cycles';
        }),
        boxpoints: 'all', jitter: 0.4, pointpos: 0,
        hovertemplate: '%{text}<extra>%{fullData.name}</extra>',
        marker: {color: colors[m], size: 6, opacity: 0.7},
        line: {color: colors[m]},
        fillcolor: colors[m] + '30'
      });
    });
    if (traces.length) {
      Plotly.newPlot('chart-speedup', traces, Object.assign({}, BASE, {
        title: {text: 'Per-bench potential speedup distribution', x: 0, font: {size: 16}},
        yaxis: Object.assign({}, BASE.yaxis, {title: {text: 'Speedup ratio (1 \u2212 best/default)'}, range: [-0.05, 1.05]}),
        showlegend: false
      }), CFG);
    } else {
      document.getElementById('chart-speedup').innerHTML = '<p style="color:#6b7280;padding:40px">No speedup data available.</p>';
    }
  })();

  // -- Bench detail --
  (function() {
    var searchInput = document.getElementById('bench-search');
    var grid = document.getElementById('bench-grid');
    if (!searchInput || !grid) return;
    var btns = Array.from(grid.querySelectorAll('.bench-btn'));
    var sections = Array.from(document.querySelectorAll('.bench-detail'));
    var renderedBenches = {};
    var activeBtn = null;

    function hideAll() {
      sections.forEach(function(s){s.classList.add('hidden');});
    }

    function renderDetail(bench) {
      if (renderedBenches[bench]) return;
      renderedBenches[bench] = true;
      var bd = D.benchDetails[bench];
      if (!bd) return;

      ['kernel_cycles', 'total_cycles'].forEach(function(metric) {
        var prefix = metric === 'kernel_cycles' ? 'kernel' : 'total';
        var containerId = 'detail-' + prefix + '-' + bench;
        var el = document.getElementById(containerId);
        if (!el) return;
        var pts = bd[metric];
        if (!pts || !pts.length) {
          el.innerHTML = '<p style="color:#6b7280;padding:20px">No data for ' + metric + '.</p>';
          return;
        }
        var vfLabels = pts.map(function(p){return p.label;});
        var medians = pts.map(function(p){return p.median;});
        var compares = pts.map(function(p){return p.compare;});
        var barColors = pts.map(function(p){return p.selected ? '#dc2626' : '#2563eb';});
        var barTrace = {
          type: 'bar', name: 'median latency', x: vfLabels, y: medians,
          marker: {color: barColors, opacity: 0.78},
          text: medians.map(function(v){return Math.round(v).toString();}),
          textposition: 'auto',
          textfont: {size: 12, color: '#fff'},
          hovertemplate: '%{x}<br>median: %{y:,.0f}<extra></extra>'
        };
        var traces = [barTrace];
        var layout = Object.assign({}, BASE, {
          title: {text: bench + ': ' + metric + ' detail', x: 0, font: {size: 16}},
          xaxis: Object.assign({}, BASE.xaxis, {title: {text: 'VF'}}),
          yaxis: Object.assign({}, BASE.yaxis, {title: {text: 'Median latency (cycles)'}}),
          showlegend: true,
          legend: {font: {size: 13}}
        });
        var hasCompare = compares.some(function(c){return c !== null;});
        if (hasCompare) {
          var cVfs = [], cVals = [];
          pts.forEach(function(p){if(p.compare!==null){cVfs.push(p.label);cVals.push(p.compare);}});
          traces.push({
            type: 'scatter', mode: 'markers', name: 'VPlan compare',
            x: cVfs, y: cVals, yaxis: 'y2',
            marker: {color: '#1c1c1e', size: 10, symbol: 'circle'},
            hovertemplate: '%{x}<br>compare: %{y:,.0f}<extra></extra>'
          });
          layout.yaxis2 = {
            title: {text: 'VPlan compare'},
            overlaying: 'y', side: 'right',
            gridcolor: 'rgba(0,0,0,0)',
            tickfont: {size: 13, color: '#6b7280'}
          };
        }
        Plotly.newPlot(containerId, traces, layout, CFG);
      });
    }

    function selectBench(bench) {
      if (activeBtn) activeBtn.classList.remove('active');
      hideAll();
      var btn = grid.querySelector('.bench-btn[data-bench="' + CSS.escape(bench) + '"]');
      if (btn) { btn.classList.add('active'); activeBtn = btn; }
      var target = document.querySelector('.bench-detail[data-bench="' + CSS.escape(bench) + '"]');
      if (target) {
        target.classList.remove('hidden');
        renderDetail(bench);
        target.scrollIntoView({behavior: 'smooth', block: 'start'});
      }
    }

    btns.forEach(function(btn) {
      btn.addEventListener('click', function() { selectBench(btn.dataset.bench); });
    });

    searchInput.addEventListener('input', function() {
      var term = searchInput.value.trim().toLowerCase();
      btns.forEach(function(btn) {
        var match = !term || btn.dataset.bench.toLowerCase().includes(term);
        btn.classList.toggle('hidden-btn', !match);
      });
    });

    hideAll();
  })();

  // -- Smooth scroll for nav --
  document.querySelectorAll('.nav-link').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({behavior: 'smooth', block: 'start'});
      }
    });
  });
})();
"""


def render_html(data: ReportData, plots: dict) -> str:
    cards = build_summary_cards(data)
    plottable_benches = list_plottable_benches(data)

    kernel_map = {summary.bench: summary for summary in data.metric_summaries["kernel_cycles"]}
    total_map = {summary.bench: summary for summary in data.metric_summaries["total_cycles"]}
    vplan_failure_map: dict[str, list[VPlanFailure]] = defaultdict(list)
    for failure in data.vplan_failures:
        vplan_failure_map[failure.bench].append(failure)

    bench_captions: dict[str, str] = {}
    for bench in plottable_benches:
        kernel_summary = kernel_map.get(bench)
        total_summary = total_map.get(bench)
        failure_text = ""
        if vplan_failure_map.get(bench):
            failure_text = " | vplan failures: " + ", ".join(
                sorted({failure.failure for failure in vplan_failure_map[bench]})
            )
        bench_captions[bench] = (
            f"Candidates={data.candidate_counts.get(bench, 0)}"
            f". {build_detail_summary_text(kernel_summary, 'kernel_cycles')}"
            f". {build_detail_summary_text(total_summary, 'total_cycles')}"
            f"{failure_text}"
        )

    report_data = {
        "coverage": plots["coverage"],
        "scatter": {
            "kernel_cycles": plots["scatter:kernel_cycles"],
            "total_cycles": plots["scatter:total_cycles"],
        },
        "ranking": plots["ranking"],
        "speedup": plots["speedup"],
        "benchDetails": {
            bench: {
                "kernel_cycles": plots.get(f"detail:{bench}:kernel_cycles", []),
                "total_cycles": plots.get(f"detail:{bench}:total_cycles", []),
            }
            for bench in plottable_benches
        },
    }
    report_json = json.dumps(report_data, separators=(",", ":"))

    cards_html = []
    for title, value in cards:
        cards_html.append(
            f"<div class='card'><div class='card-title'>{escape(title)}</div>"
            f"<div class='card-value'>{escape(value)}</div></div>"
        )

    nav_items = [
        ("summary", "Summary"),
        ("coverage", "Coverage"),
        ("kernel-scatter", "Kernel"),
        ("total-scatter", "Total"),
        ("ranking", "Ranking"),
        ("speedup", "Speedup"),
        ("bench-detail", "Bench Detail"),
    ]
    nav_html = " ".join(
        f"<a href='#{anchor}' class='nav-link'>{label}</a>"
        for anchor, label in nav_items
    )

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8' />",
        "<meta name='viewport' content='width=device-width, initial-scale=1' />",
        f"<title>VPlan Cost Report ({escape(data.result_stage)} / {escape(data.result_target)})</title>",
        "<script src='https://cdn.plot.ly/plotly-2.35.2.min.js'></script>",
        "<style>",
        _CSS,
        "</style>",
        "</head>",
        "<body>",
        f"<nav class='top-nav'><span class='nav-title'>VPlan Report</span><div class='nav-links'>{nav_html}</div></nav>",
        "<main>",
        "<header id='summary'>",
        f"<h1>VPlan Cost vs Measured Latency</h1>",
        f"<p class='subtitle'>Interactive report comparing VPlan cost predictions against measured cycle counts."
        f" Stage: <strong>{escape(data.result_stage)}</strong>"
        f" &middot; Target: <strong>{escape(data.result_target)}</strong></p>",
        f"<div class='cards'>{''.join(cards_html)}</div>",
        "</header>",
        "<section class='section section-accent' id='coverage'>",
        "<h2>Coverage summary</h2>",
        "<p class='caption'>VPlan explain and measurement outcome breakdown including successes and failure reasons.</p>",
        "<div class='chart-row'><div id='chart-outcome'></div><div id='chart-vf-distribution'></div></div>",
        "</section>",
        "<section class='section section-accent-kernel' id='kernel-scatter'>",
        "<h2>VPlan compare vs latency (kernel_cycles)</h2>",
        "<p class='caption'>x = VPlan compare, y = median latency. "
        "Gray = scalar (VF 1), blue gradient = vectorized (darker = higher VF). "
        "Circle = fixed, diamond = scalable.</p>",
        "<div class='vf-toggle-row' id='vf-toggles-kernel_cycles'></div>",
        "<div id='chart-scatter-kernel_cycles'></div>",
        "<p class='scatter-stats' id='scatter-stats-kernel_cycles'></p>",
        "</section>",
        "<section class='section section-accent-total' id='total-scatter'>",
        "<h2>VPlan compare vs latency (total_cycles)</h2>",
        "<p class='caption'>x = VPlan compare, y = median latency. "
        "Gray = scalar (VF 1), blue gradient = vectorized (darker = higher VF). "
        "Circle = fixed, diamond = scalable.</p>",
        "<div class='vf-toggle-row' id='vf-toggles-total_cycles'></div>",
        "<div id='chart-scatter-total_cycles'></div>",
        "<p class='scatter-stats' id='scatter-stats-total_cycles'></p>",
        "</section>",
        "<section class='section section-accent' id='ranking'>",
        "<h2>Ranking quality overview</h2>",
        "<p class='caption'>Left: per-bench Spearman distribution. Right: 100%% stacked bars showing the share of benches at each overlap level for Top-1~Top-4.</p>",
        "<div id='chart-spearman'></div><div id='chart-topn'></div>",
        "</section>",
        "<section class='section section-accent' id='speedup'>",
        "<h2>Potential speedup</h2>",
        "<p class='caption'>Per-benchmark speedup ratio: 1 &minus; (best non-default cycles / default cycles). "
        "Higher = more improvement from vectorization. Sorted descending.</p>",
        "<div id='chart-speedup'></div>",
        "</section>",
        "<section class='section' id='bench-detail'>",
        "<h2>Bench detail</h2>",
    ]
    if plottable_benches:
        bench_btns = "".join(
            f"<button class='bench-btn' data-bench='{escape(b)}'>{escape(b)}</button>"
            for b in plottable_benches
        )
        html_parts.append(
            f"<p>Select a benchmark to reveal kernel/total detail. "
            f"({len(plottable_benches)} plottable benches)</p>"
            "<div class='bench-picker'>"
            "<input id='bench-search' type='search' placeholder='Filter benchmarks...' autocomplete='off' />"
            f"<div class='bench-grid' id='bench-grid'>{bench_btns}</div>"
            "</div>"
        )
        for bench in plottable_benches:
            html_parts.append(
                f"<div class='bench-detail hidden' data-bench='{escape(bench)}'>"
                f"<h3>Bench detail: {escape(bench)}</h3>"
                f"<p class='caption'>{escape(bench_captions[bench])}</p>"
                f"<div id='detail-kernel-{escape(bench)}'></div>"
                f"<div id='detail-total-{escape(bench)}'></div>"
                f"</div>"
            )
    else:
        html_parts.append("<p class='empty'>No benches with plottable detail are available.</p>")

    html_parts += [
        "</section>",
        "</main>",
        f"<script type='application/json' id='report-data'>{report_json}</script>",
        "<script>",
        _APP_JS,
        "</script>",
        "</body>",
        "</html>",
    ]
    return "".join(html_parts)


def generate_plots(data: ReportData) -> dict:
    plots: dict = {
        "coverage": build_coverage_data(data),
        "ranking": build_ranking_data(data.metric_summaries),
        "speedup": build_speedup_data(data.metric_summaries),
    }
    for metric_name, summaries in data.metric_summaries.items():
        plots[f"scatter:{metric_name}"] = build_scatter_data(summaries)

    kernel_map = {summary.bench: summary for summary in data.metric_summaries["kernel_cycles"]}
    total_map = {summary.bench: summary for summary in data.metric_summaries["total_cycles"]}
    for bench in list_plottable_benches(data):
        plots[f"detail:{bench}:kernel_cycles"] = build_bench_detail_data(kernel_map.get(bench))
        plots[f"detail:{bench}:total_cycles"] = build_bench_detail_data(total_map.get(bench))
    return plots


def main() -> None:
    args = parse_args()

    root = repo_root()
    bench_filter = {bench.strip() for bench in args.bench if bench.strip()}
    vfs_db = resolve_input_path(root, args.vfs_db)
    result_db = resolve_input_path(root, args.result_db)
    output_html = resolve_output_html(root, args.output_html, result_db)

    data = load_report_data(vfs_db, result_db, bench_filter)
    plots = generate_plots(data)
    report_html = render_html(data, plots)
    output_html.write_text(report_html, encoding="utf-8")
    print(f"wrote {output_html}")


if __name__ == "__main__":
    main()
