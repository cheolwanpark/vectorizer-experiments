#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import html
import io
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
DEFAULT_EMULATE_GLOB = "artifacts/emulate-result-*.sqlite"
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
        "--emulate-db",
        default="",
        help="Path to emulate-result-*.sqlite (defaults to latest matching file)",
    )
    parser.add_argument(
        "--output-html",
        default="",
        help="Output HTML path (defaults to artifacts/plots/<emulate-db-stem>.html)",
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


def resolve_latest_emulate_db(root: Path, explicit_path: str) -> Path:
    if explicit_path:
        return resolve_input_path(root, explicit_path)
    candidates = sorted((root / "artifacts").glob("emulate-result-*.sqlite"))
    if not candidates:
        fail(
            "no emulate-result-*.sqlite file found under artifacts/\n"
            "Run `make emulate-all` first or pass --emulate-db."
        )
    return candidates[-1].resolve()


def resolve_output_html(root: Path, explicit_path: str, emulate_db: Path) -> Path:
    if explicit_path:
        out_path = Path(explicit_path)
        if not out_path.is_absolute():
            out_path = (root / explicit_path).resolve()
    else:
        out_path = (root / DEFAULT_OUTPUT_ROOT / f"{emulate_db.stem}.html").resolve()
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


def require_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
    except ModuleNotFoundError:
        fail(
            "matplotlib is required to render this report.\n"
            "Run with: uv run --with matplotlib python scripts/plot_results.py ..."
        )
    return plt


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
    emulate_db: Path
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
        if str(row["stage"] or "") != "emulate":
            continue
        bench = str(row["bench"] or "")
        if bench_filter and bench not in bench_filter:
            continue
        failure = str(row["failure"] or "")
        if failure:
            failure_counts[failure] += 1
            continue
        use_vf = str(row["use_vf"] or "")
        if not use_vf:
            continue
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
        if candidate is None:
            continue
        points_by_bench[bench].append(
            MetricPoint(
                bench=bench,
                use_vf=use_vf,
                selected=candidate.selected,
                raw_cost=candidate.raw_cost,
                raw_compare=candidate.raw_compare,
                compare=candidate.compare,
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


def load_report_data(vfs_db: Path, emulate_db: Path, bench_filter: set[str]) -> ReportData:
    candidates, candidate_counts, vplan_failures = load_vfs_data(vfs_db, bench_filter)
    aggregates, emulate_failure_counts = load_emulate_data(emulate_db, bench_filter)
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
        emulate_db=emulate_db,
        benches=benches,
        candidates=candidates,
        candidate_counts=candidate_counts,
        vplan_failures=vplan_failures,
        emulate_aggregates=aggregates,
        emulate_failure_counts=emulate_failure_counts,
        metric_summaries=metric_summaries,
    )


def figure_to_data_url(fig) -> str:
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    fig.clf()
    return f"data:image/png;base64,{encoded}"


def make_placeholder_figure(title: str, message: str) -> str:
    plt = require_matplotlib()
    fig, ax = plt.subplots(figsize=(8, 2.8))
    ax.axis("off")
    ax.set_title(title, loc="left")
    ax.text(0.01, 0.5, message, va="center", ha="left", transform=ax.transAxes, fontsize=11)
    data_url = figure_to_data_url(fig)
    plt.close(fig)
    return data_url


def render_coverage_summary(data: ReportData) -> str:
    plt = require_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

    reason_counts: Counter[str] = Counter()
    for failure in data.vplan_failures:
        reason_counts[f"vplan:{failure.failure}"] += 1
    for reason, count in data.emulate_failure_counts.items():
        reason_counts[f"emulate:{reason}"] += count

    ax = axes[0]
    if reason_counts:
        labels = list(reason_counts.keys())
        values = [reason_counts[label] for label in labels]
        ax.barh(labels, values, color="#B85C38")
        ax.set_title("Failure Counts", loc="left")
        ax.set_xlabel("Rows")
    else:
        ax.axis("off")
        ax.text(0.02, 0.5, "No failures recorded.", transform=ax.transAxes, va="center")

    ax = axes[1]
    if data.candidate_counts:
        dist = Counter(data.candidate_counts.values())
        labels = sorted(dist)
        values = [dist[label] for label in labels]
        ax.bar(labels, values, color="#3A86FF")
        ax.set_title("VF Candidate Count Per Bench", loc="left")
        ax.set_xlabel("Candidate count")
        ax.set_ylabel("Bench count")
    else:
        ax.axis("off")
        ax.text(0.02, 0.5, "No candidate rows available.", transform=ax.transAxes, va="center")

    data_url = figure_to_data_url(fig)
    plt.close(fig)
    return data_url


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


def render_scatter(summaries: list[BenchMetricSummary], *, title: str) -> str:
    selected_points: list[MetricPoint] = []
    other_points: list[MetricPoint] = []
    for summary in summaries:
        for point in summary.points:
            if point.compare is None:
                continue
            if point.selected:
                selected_points.append(point)
            else:
                other_points.append(point)
    all_points = other_points + selected_points
    if not all_points:
        return make_placeholder_figure(title, "No rows with both cost and latency are available.")

    candidate_fit_points = [point for point in all_points if not is_suspect_compare_outlier(point)]
    fit_points = candidate_fit_points or all_points
    excluded_from_fit = len(all_points) - len(fit_points) if candidate_fit_points else 0

    plt = require_matplotlib()
    fig, ax = plt.subplots(figsize=(8, 5))
    if other_points:
        ax.scatter(
            [point.compare for point in other_points],
            [point.median_value for point in other_points],
            label="non-selected",
            c="#3A86FF",
            alpha=0.7,
            s=35,
        )
    if selected_points:
        ax.scatter(
            [point.compare for point in selected_points],
            [point.median_value for point in selected_points],
            label="selected",
            c="#FB5607",
            alpha=0.9,
            s=45,
            marker="D",
        )

    fit = linear_regression(
        [float(point.compare) for point in fit_points],
        [point.median_value for point in fit_points],
    )
    if fit is not None:
        slope, intercept, r_squared = fit
        x_min = min(float(point.compare) for point in fit_points)
        x_max = max(float(point.compare) for point in fit_points)
        if x_min == x_max:
            x_max = x_min + 1.0
        xs = [x_min, x_max]
        ys = [slope * x + intercept for x in xs]
        label = "linear fit"
        if excluded_from_fit:
            suffix = "" if excluded_from_fit == 1 else "s"
            label += f" (excl. {excluded_from_fit} suspect outlier{suffix}"
        else:
            label += " ("
        if r_squared is not None:
            label += f"R²={r_squared:.2f}"
        else:
            label += "R²=n/a"
        label += ")"
        ax.plot(xs, ys, color="#222222", linewidth=2, linestyle="--", label=label)

    if excluded_from_fit:
        x_min = min(float(point.compare) for point in fit_points)
        x_max = max(float(point.compare) for point in fit_points)
        if x_min == x_max:
            x_max = x_min + 1.0
        x_pad = max((x_max - x_min) * 0.05, 0.1)
        ax.set_xlim(x_min - x_pad, x_max + x_pad)
        suffix = "" if excluded_from_fit == 1 else "s"
        ax.text(
            0.02,
            0.98,
            f"{excluded_from_fit} suspect compare outlier{suffix} omitted from fit/x-range",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            color="#5d6470",
            bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#d8d8d4", "pad": 4},
        )

    ax.set_title(title, loc="left")
    ax.set_xlabel("VPlan compare")
    ax.set_ylabel("Median latency (cycles)")
    ax.legend(loc="best")
    ax.grid(color="#E6E6E6", linewidth=0.8)
    data_url = figure_to_data_url(fig)
    plt.close(fig)
    return data_url


def render_ranking_quality(metric_summaries: dict[str, list[BenchMetricSummary]]) -> str:
    plt = require_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    metric_defs = [
        ("kernel_cycles", "kernel_cycles", "#FB5607"),
        ("total_cycles", "total_cycles", "#3A86FF"),
    ]

    ax = axes[0]
    spearman_values = [
        [summary.spearman for summary in metric_summaries[metric_name] if summary.spearman is not None]
        for metric_name, _, _ in metric_defs
    ]
    if any(values for values in spearman_values):
        labels = [label for _, label, _ in metric_defs]
        boxplot = ax.boxplot(
            [values if values else [math.nan] for values in spearman_values],
            tick_labels=labels,
            patch_artist=True,
        )
        for patch, (_, _, color) in zip(boxplot["boxes"], metric_defs):
            patch.set_facecolor(color)
            patch.set_alpha(0.25)
        for idx, ((_, _, color), values) in enumerate(zip(metric_defs, spearman_values), start=1):
            for offset, value in enumerate(values):
                jitter = ((offset % 7) - 3) * 0.025
                ax.scatter(idx + jitter, value, color=color, s=28, alpha=0.85)
        ax.axhline(0.0, color="#999999", linewidth=1, linestyle=":")
        ax.set_ylim(-1.05, 1.05)
        ax.set_ylabel("Spearman rank correlation")
        ax.set_title("Per-bench Spearman distribution", loc="left")
        ax.grid(axis="y", color="#E6E6E6", linewidth=0.8)
    else:
        ax.axis("off")
        ax.text(0.02, 0.5, "No rankable benches available.", transform=ax.transAxes, va="center")

    ax = axes[1]
    has_overlap = False
    cmap = plt.get_cmap("RdYlGn")
    bar_width = 0.32
    metric_offsets = [-0.18, 0.18]
    metric_hatches = ["", "//"]
    for metric_index, (metric_name, _, color) in enumerate(metric_defs):
        ns, distributions, eligible_counts = build_top_n_overlap_distributions(metric_summaries[metric_name])
        for n, ratios, count in zip(ns, distributions, eligible_counts):
            has_overlap = True
            position = n + metric_offsets[metric_index]
            bottom = 0.0
            for overlap_count in range(0, n + 1):
                ratio_value = overlap_count / n
                bucket_count = sum(
                    1
                    for ratio in ratios
                    if math.isclose(ratio, ratio_value, rel_tol=1e-9, abs_tol=1e-9)
                )
                if bucket_count == 0:
                    continue
                height = bucket_count / count
                fill_color = cmap(overlap_count / max(1, n))
                ax.bar(
                    position,
                    height,
                    width=bar_width,
                    bottom=bottom,
                    color=fill_color,
                    edgecolor=color,
                    linewidth=1.1,
                    hatch=metric_hatches[metric_index],
                    alpha=0.88,
                )
                if height >= 0.11:
                    ax.text(
                        position,
                        bottom + height / 2,
                        f"{overlap_count}/{n}",
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="#222222",
                    )
                bottom += height
            ax.text(position, 1.02, f"n={count}", ha="center", va="bottom", fontsize=8, color=color)
    if has_overlap:
        ax.set_title("Top-N overlap distribution (Top-1~4)", loc="left")
        ax.set_xlabel("Top-N")
        ax.set_ylabel("Bench share")
        ax.set_ylim(0.0, 1.05)
        ax.set_xticks([1, 2, 3, 4])
        ax.set_xticklabels(["Top-1", "Top-2", "Top-3", "Top-4"])
        ax.grid(axis="y", color="#E6E6E6", linewidth=0.8)
        handles = [
            plt.Rectangle((0, 0), 1, 1, facecolor="#DDDDDD", edgecolor=color, hatch=hatch, linewidth=1.1)
            for (_, _, color), hatch in zip(metric_defs, metric_hatches)
        ]
        ax.legend(handles, [label for _, label, _ in metric_defs], loc="lower right")
    else:
        ax.axis("off")
        ax.text(0.02, 0.5, "No rankable benches available.", transform=ax.transAxes, va="center")

    data_url = figure_to_data_url(fig)
    plt.close(fig)
    return data_url


def render_metric_detail_axis(ax, summary: BenchMetricSummary | None, *, title: str) -> None:
    if summary is None or not summary.points:
        ax.axis("off")
        ax.set_title(title, loc="left")
        ax.text(0.02, 0.5, "No successful emulate samples for this metric.", transform=ax.transAxes, va="center")
        return

    ordered_points = sorted(
        summary.points,
        key=lambda point: (point.median_value, parse_vf_key(point.use_vf)),
    )
    x_positions = list(range(len(ordered_points)))
    max_latency = max(point.median_value for point in ordered_points)
    for x_index, point in enumerate(ordered_points):
        color = "#FB5607" if point.selected else "#3A86FF"
        ax.bar(x_index, point.median_value, width=0.72, color=color, alpha=0.78)
        inside_threshold = max_latency * 0.18
        if point.median_value >= inside_threshold:
            label_y = point.median_value - max_latency * 0.05
            label_va = "top"
            label_color = "white"
        else:
            label_y = point.median_value + max_latency * 0.02
            label_va = "bottom"
            label_color = "#222222"
        ax.text(
            x_index,
            label_y,
            f"{point.median_value:.0f}",
            ha="center",
            va=label_va,
            fontsize=8,
            color=label_color,
            fontweight="bold",
        )

    ax.set_title(title, loc="left")
    ax.set_xticks(x_positions)
    ax.set_xticklabels([point.use_vf for point in ordered_points], rotation=45, ha="right")
    ax.set_ylabel("Median latency (cycles)")
    ax.grid(axis="y", color="#E6E6E6", linewidth=0.8)

    compare_points = [
        (x_index, point.compare) for x_index, point in enumerate(ordered_points) if point.compare is not None
    ]
    ax2 = ax.twinx()
    if compare_points:
        ax2.scatter(
            [x_index for x_index, _ in compare_points],
            [float(compare) for _, compare in compare_points],
            color="#222222",
            marker="o",
            s=42,
            alpha=0.9,
        )
        ax2.set_ylabel("VPlan compare")
    else:
        ax2.set_yticks([])
        ax2.set_ylabel("VPlan compare unavailable")


def render_bench_detail(
    bench: str,
    kernel_summary: BenchMetricSummary | None,
    total_summary: BenchMetricSummary | None,
) -> str:
    plt = require_matplotlib()
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=False)
    render_metric_detail_axis(axes[0], kernel_summary, title=f"{bench}: kernel_cycles detail")
    render_metric_detail_axis(axes[1], total_summary, title=f"{bench}: total_cycles detail")
    axes[1].set_xlabel("VF")
    data_url = figure_to_data_url(fig)
    plt.close(fig)
    return data_url


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
    return [
        ("VFS DB", str(data.vfs_db)),
        ("Emulate DB", str(data.emulate_db)),
        ("Generated", datetime.now().isoformat(timespec="seconds")),
        ("Benchmarks", str(len(data.benches))),
        ("Kernel comparable benches", str(len(comparable))),
        ("VPlan failures", str(len(data.vplan_failures))),
        ("Emulate failures", str(sum(data.emulate_failure_counts.values()))),
        ("Selected VF matches actual best", f"{len(selected_matches)}/{len(comparable) or 0}"),
        ("Mean kernel Spearman", format_float(avg_spearman, digits=2)),
        ("Kernel top-1 overlap", format_float(top1_overlap, digits=2)),
        ("Kernel scatter fit exclusions", f"{kernel_suspect_outliers} suspect compare outlier{outlier_suffix}"),
    ]


def render_cards(cards: list[tuple[str, str]]) -> str:
    items = []
    for title, value in cards:
        items.append(
            "<div class='card'>"
            f"<div class='card-title'>{escape(title)}</div>"
            f"<div class='card-value'>{escape(value)}</div>"
            "</div>"
        )
    return "<div class='cards'>" + "".join(items) + "</div>"


def render_image_section(title: str, data_url: str, caption: str = "") -> str:
    caption_html = f"<p class='caption'>{escape(caption)}</p>" if caption else ""
    return (
        "<section class='plot-section'>"
        f"<h2>{escape(title)}</h2>"
        f"{caption_html}"
        f"<img src='{data_url}' alt='{escape(title)}' />"
        "</section>"
    )


def build_detail_summary_text(summary: BenchMetricSummary | None, metric_name: str) -> str:
    if summary is None:
        return f"{metric_name}: no successful emulate rows"
    return (
        f"{metric_name}: selected={summary.selected_vf or '-'}, "
        f"compare-best={summary.compare_best_vf or '-'}, "
        f"latency-best={summary.actual_best_vf or '-'}, "
        f"spearman={format_float(summary.spearman, digits=2)}"
    )


def render_bench_picker(benches: Sequence[str]) -> str:
    if not benches:
        return (
            "<section class='plot-section'>"
            "<h2>Bench detail</h2>"
            "<p class='empty'>No benches with plottable detail are available.</p>"
            "</section>"
        )
    options = ["<option value=''>-- Select a bench --</option>"]
    for bench in benches:
        options.append(f"<option value='{escape(bench)}'>{escape(bench)}</option>")
    return (
        "<section class='plot-section'>"
        "<h2>Bench detail</h2>"
        f"<p>Search benches, then select one to reveal kernel/total detail with latency-sorted VF order. ({len(benches)} plottable benches)</p>"
        "<div class='bench-picker'>"
        "<input id='bench-search' type='search' placeholder='Search bench...' autocomplete='off' />"
        f"<select id='bench-select' size='12'>{''.join(options)}</select>"
        "</div>"
        "<p id='bench-empty' class='empty'>Select a bench to show detail.</p>"
        "</section>"
    )


def render_html(data: ReportData, plots: dict[str, str]) -> str:
    cards_html = render_cards(build_summary_cards(data))
    plottable_benches = list_plottable_benches(data)

    kernel_map = {summary.bench: summary for summary in data.metric_summaries["kernel_cycles"]}
    total_map = {summary.bench: summary for summary in data.metric_summaries["total_cycles"]}
    vplan_failure_map: dict[str, list[VPlanFailure]] = defaultdict(list)
    for failure in data.vplan_failures:
        vplan_failure_map[failure.bench].append(failure)

    detail_sections = []
    for bench in plottable_benches:
        kernel_summary = kernel_map.get(bench)
        total_summary = total_map.get(bench)
        failure_text = ""
        if vplan_failure_map.get(bench):
            failure_text = " | vplan failures: " + ", ".join(
                sorted({failure.failure for failure in vplan_failure_map[bench]})
            )
        caption = (
            f"Candidates={data.candidate_counts.get(bench, 0)}"
            f". {build_detail_summary_text(kernel_summary, 'kernel_cycles')}"
            f". {build_detail_summary_text(total_summary, 'total_cycles')}"
            f"{failure_text}"
        )
        detail_sections.append(
            "<section class='plot-section bench-detail hidden' "
            f"id='detail-{escape(bench)}' data-bench='{escape(bench)}'>"
            f"<h2>Bench detail: {escape(bench)}</h2>"
            f"<p class='caption'>{escape(caption)}</p>"
            f"<img src='{plots[f'detail:{bench}']}' alt='{escape(f'Bench detail: {bench}')}' />"
            "</section>"
        )

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8' />",
        "<meta name='viewport' content='width=device-width, initial-scale=1' />",
        "<title>VPlan Compare vs Emulate Report</title>",
        "<style>",
        """
        :root {
          color-scheme: light;
          --bg: #f7f7f5;
          --card: #ffffff;
          --ink: #1e1f24;
          --muted: #5d6470;
          --line: #d8d8d4;
          --accent: #3a86ff;
          --accent-2: #fb5607;
        }
        body {
          margin: 0;
          padding: 24px;
          background: linear-gradient(180deg, #f7f7f5 0%, #f1efe9 100%);
          color: var(--ink);
          font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        }
        main {
          max-width: 1440px;
          margin: 0 auto;
        }
        h1, h2 {
          margin: 0 0 12px 0;
        }
        p {
          color: var(--muted);
          line-height: 1.5;
        }
        .cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 12px;
          margin: 20px 0 28px 0;
        }
        .card {
          background: var(--card);
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 14px 16px;
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.04);
        }
        .card-title {
          font-size: 12px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--muted);
          margin-bottom: 6px;
        }
        .card-value {
          font-size: 16px;
          font-weight: 600;
          word-break: break-word;
        }
        .plot-section {
          background: var(--card);
          border: 1px solid var(--line);
          border-radius: 16px;
          padding: 18px;
          margin-bottom: 22px;
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.04);
        }
        .plot-section img {
          width: 100%;
          height: auto;
          display: block;
          border-radius: 10px;
          background: #fff;
        }
        .caption {
          margin-top: -2px;
          margin-bottom: 14px;
        }
        .bench-picker {
          display: grid;
          grid-template-columns: minmax(220px, 360px);
          gap: 12px;
        }
        #bench-search,
        #bench-select {
          width: 100%;
          border: 1px solid var(--line);
          border-radius: 10px;
          padding: 10px 12px;
          box-sizing: border-box;
          font: inherit;
          background: #fff;
          color: var(--ink);
        }
        #bench-select {
          min-height: 280px;
        }
        .hidden {
          display: none;
        }
        .empty {
          padding: 12px 0 0 0;
        }
        @media (max-width: 720px) {
          body {
            padding: 14px;
          }
          .plot-section {
            padding: 12px;
          }
          .bench-picker {
            grid-template-columns: 1fr;
          }
        }
        """,
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<h1>VPlan Compare vs Emulate Latency</h1>",
        "<p>Single-file HTML report with base64-embedded plot images.</p>",
        cards_html,
        render_image_section(
            "Coverage summary",
            plots["coverage"],
            "Failures and candidate coverage before reading compare-vs-latency plots.",
        ),
        render_image_section(
            "VPlan compare vs latency scatter: kernel_cycles",
            plots["scatter:kernel_cycles"],
            "x uses the VPlan compare value as-is, y uses measured median latency. Dashed line is a linear fit for comparison.",
        ),
        render_image_section(
            "VPlan compare vs latency scatter: total_cycles",
            plots["scatter:total_cycles"],
            "Same view for total_cycles.",
        ),
        render_image_section(
            "Ranking quality overview",
            plots["ranking_quality"],
            "Left: per-bench Spearman distribution. Right: 100% stacked bars showing the share of benches at each overlap level for Top-1~Top-4.",
        ),
        render_bench_picker(plottable_benches),
        *detail_sections,
        "</main>",
        "<script>",
        """
        (() => {
          const searchInput = document.getElementById('bench-search');
          const select = document.getElementById('bench-select');
          const empty = document.getElementById('bench-empty');
          const sections = Array.from(document.querySelectorAll('.bench-detail'));

          function hideAll() {
            sections.forEach((section) => section.classList.add('hidden'));
          }

          function showSelected() {
            const value = select.value;
            hideAll();
            if (!value) {
              empty.classList.remove('hidden');
              return;
            }
            empty.classList.add('hidden');
            const target = document.querySelector(`.bench-detail[data-bench="${CSS.escape(value)}"]`);
            if (target) {
              target.classList.remove('hidden');
              target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
          }

          function applyFilter() {
            const term = searchInput.value.trim().toLowerCase();
            const currentValue = select.value;
            let hasVisibleSelected = false;
            Array.from(select.options).forEach((option, index) => {
              if (index === 0) {
                option.hidden = false;
                return;
              }
              const visible = !term || option.value.toLowerCase().includes(term);
              option.hidden = !visible;
              if (visible && option.value === currentValue) {
                hasVisibleSelected = true;
              }
            });
            if (!hasVisibleSelected) {
              select.value = '';
            }
            showSelected();
          }

          searchInput.addEventListener('input', applyFilter);
          select.addEventListener('change', showSelected);
          hideAll();
        })();
        """,
        "</script>",
        "</body>",
        "</html>",
    ]
    return "".join(html_parts)


def generate_plots(data: ReportData) -> dict[str, str]:
    plots = {
        "coverage": render_coverage_summary(data),
        "ranking_quality": render_ranking_quality(data.metric_summaries),
    }
    for metric_name, summaries in data.metric_summaries.items():
        label = metric_label(metric_name)
        plots[f"scatter:{metric_name}"] = render_scatter(
            summaries,
            title=f"VPlan compare vs latency ({label})",
        )

    kernel_map = {summary.bench: summary for summary in data.metric_summaries["kernel_cycles"]}
    total_map = {summary.bench: summary for summary in data.metric_summaries["total_cycles"]}
    for bench in list_plottable_benches(data):
        plots[f"detail:{bench}"] = render_bench_detail(
            bench,
            kernel_map.get(bench),
            total_map.get(bench),
        )
    return plots


def main() -> None:
    args = parse_args()

    root = repo_root()
    bench_filter = {bench.strip() for bench in args.bench if bench.strip()}
    vfs_db = resolve_input_path(root, args.vfs_db)
    emulate_db = resolve_latest_emulate_db(root, args.emulate_db)
    output_html = resolve_output_html(root, args.output_html, emulate_db)

    data = load_report_data(vfs_db, emulate_db, bench_filter)
    plots = generate_plots(data)
    report_html = render_html(data, plots)
    output_html.write_text(report_html, encoding="utf-8")
    print(f"wrote {output_html}")


if __name__ == "__main__":
    main()
