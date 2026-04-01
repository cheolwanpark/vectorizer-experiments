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
        help="Number of top mismatch benchmarks to include as drill-down sections",
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


def escape(value: object) -> str:
    return html.escape(str(value))


def require_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import colors as mcolors
        from matplotlib import pyplot as plt
    except ModuleNotFoundError:
        fail(
            "matplotlib is required to render this report.\n"
            "Run with: uv run --with matplotlib python scripts/plot_results.py ..."
        )
    return plt, mcolors


@dataclass
class VFCandidate:
    bench: str
    use_vf: str
    raw_vf: str
    raw_cost: str
    cost: float | None
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
    cost: float | None
    samples: list[float]
    median_value: float
    min_value: float
    max_value: float
    n_success: int
    best_ratio: float | None = None
    cost_rank: int | None = None
    actual_rank: int | None = None


@dataclass
class BenchMetricSummary:
    bench: str
    metric_name: str
    points: list[MetricPoint]
    selected_vf: str | None
    cost_best_vf: str | None
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
    rows = conn.execute(
        """
        SELECT bench, use_vf, raw_vf, cost, selected, failure, failure_message
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
            cost=parse_effective_cost(str(row["cost"] or ""), use_vf),
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
                cost=candidate.cost,
                samples=list(samples),
                median_value=median(samples),
                min_value=min(samples),
                max_value=max(samples),
                n_success=len(samples),
            )
        )

    summaries: list[BenchMetricSummary] = []
    for bench, points in sorted(points_by_bench.items()):
        best_median = min(point.median_value for point in points)
        for point in points:
            point.best_ratio = point.median_value / best_median if best_median else None

        selected_vf = next((point.use_vf for point in points if point.selected), None)
        rankable = [point for point in points if point.cost is not None]
        cost_best_vf = None
        actual_best_vf = None
        max_abs_rank_delta = None
        selected_rank_delta = None
        spearman = None
        if rankable:
            cost_rank_map = dense_rank({point.use_vf: float(point.cost) for point in rankable})
            actual_rank_map = dense_rank({point.use_vf: point.median_value for point in rankable})
            cost_best_vf = min(
                rankable, key=lambda point: (float(point.cost), parse_vf_key(point.use_vf))
            ).use_vf
            actual_best_vf = min(
                rankable, key=lambda point: (point.median_value, parse_vf_key(point.use_vf))
            ).use_vf
            deltas: list[int] = []
            ordered_cost_ranks: list[float] = []
            ordered_actual_ranks: list[float] = []
            for point in rankable:
                point.cost_rank = cost_rank_map[point.use_vf]
                point.actual_rank = actual_rank_map[point.use_vf]
                delta = point.actual_rank - point.cost_rank
                deltas.append(abs(delta))
                if point.use_vf == selected_vf:
                    selected_rank_delta = delta
                ordered_cost_ranks.append(float(point.cost_rank))
                ordered_actual_ranks.append(float(point.actual_rank))
            max_abs_rank_delta = max(deltas) if deltas else None
            spearman = pearson_correlation(ordered_cost_ranks, ordered_actual_ranks)
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
                cost_best_vf=cost_best_vf,
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
    plt, _ = require_matplotlib()
    fig, ax = plt.subplots(figsize=(8, 2.8))
    ax.axis("off")
    ax.set_title(title, loc="left")
    ax.text(0.01, 0.5, message, va="center", ha="left", transform=ax.transAxes, fontsize=11)
    data_url = figure_to_data_url(fig)
    plt.close(fig)
    return data_url


def render_coverage_summary(data: ReportData) -> str:
    plt, _ = require_matplotlib()
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


def build_heatmap_inputs(
    summaries: Iterable[BenchMetricSummary],
    *,
    value_kind: str,
) -> tuple[list[str], list[str], list[list[float]], list[tuple[int, int]]]:
    rows = list(summaries)
    if not rows:
        return [], [], [], []
    row_labels = [summary.bench for summary in rows]
    col_labels = sorted(
        {point.use_vf for summary in rows for point in summary.points},
        key=parse_vf_key,
    )
    matrix: list[list[float]] = []
    selected_cells: list[tuple[int, int]] = []
    for row_index, summary in enumerate(rows):
        point_map = {point.use_vf: point for point in summary.points}
        row_values: list[float] = []
        for col_index, use_vf in enumerate(col_labels):
            point = point_map.get(use_vf)
            value = math.nan
            if point is not None:
                if value_kind == "best_ratio":
                    value = float(point.best_ratio) if point.best_ratio is not None else math.nan
                elif value_kind == "rank_delta":
                    if point.cost_rank is not None and point.actual_rank is not None:
                        value = float(point.actual_rank - point.cost_rank)
                else:
                    raise KeyError(value_kind)
                if point.selected:
                    selected_cells.append((row_index, col_index))
            row_values.append(value)
        matrix.append(row_values)
    return row_labels, col_labels, matrix, selected_cells


def render_heatmap(
    summaries: list[BenchMetricSummary],
    *,
    title: str,
    value_kind: str,
) -> str:
    row_labels, col_labels, matrix, selected_cells = build_heatmap_inputs(
        summaries, value_kind=value_kind
    )
    if not row_labels or not col_labels:
        return make_placeholder_figure(title, "No comparable rows available.")

    plt, mcolors = require_matplotlib()
    n_rows = len(row_labels)
    n_cols = len(col_labels)
    fig, ax = plt.subplots(
        figsize=(max(8.0, 2.5 + n_cols * 0.9), max(5.0, 1.8 + n_rows * 0.28))
    )
    masked = [[math.nan if math.isnan(value) else value for value in row] for row in matrix]

    if value_kind == "rank_delta":
        finite = [value for row in matrix for value in row if not math.isnan(value)]
        limit = max(abs(value) for value in finite) if finite else 1.0
        cmap = plt.get_cmap("coolwarm").copy()
        cmap.set_bad("#F1F1F1")
        norm = mcolors.TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit)
        image = ax.imshow(masked, aspect="auto", cmap=cmap, norm=norm)
    else:
        finite = [value for row in matrix for value in row if not math.isnan(value)]
        vmax = max(finite) if finite else 1.0
        cmap = plt.get_cmap("viridis").copy()
        cmap.set_bad("#F1F1F1")
        image = ax.imshow(masked, aspect="auto", cmap=cmap, vmin=1.0, vmax=max(1.0, vmax))

    ax.set_title(title, loc="left")
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(col_labels, rotation=45, ha="right")
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(row_labels)
    ax.set_xlabel("VF")
    ax.set_ylabel("Benchmark")

    if n_rows * n_cols <= 250:
        for row_index, row in enumerate(matrix):
            for col_index, value in enumerate(row):
                if math.isnan(value):
                    continue
                text = f"{value:.2f}" if value_kind == "best_ratio" else f"{int(value):+d}"
                ax.text(col_index, row_index, text, ha="center", va="center", fontsize=8, color="white")

    if selected_cells:
        xs = [cell[1] for cell in selected_cells]
        ys = [cell[0] for cell in selected_cells]
        ax.scatter(xs, ys, marker="*", s=70, facecolors="none", edgecolors="white", linewidths=1.2)

    fig.colorbar(image, ax=ax, fraction=0.02, pad=0.02)
    data_url = figure_to_data_url(fig)
    plt.close(fig)
    return data_url


def render_scatter(summaries: list[BenchMetricSummary], *, title: str) -> str:
    selected_points: list[MetricPoint] = []
    other_points: list[MetricPoint] = []
    for summary in summaries:
        for point in summary.points:
            if point.cost is None or point.best_ratio is None:
                continue
            if point.selected:
                selected_points.append(point)
            else:
                other_points.append(point)
    if not selected_points and not other_points:
        return make_placeholder_figure(title, "No rows with both cost and latency are available.")

    plt, _ = require_matplotlib()
    fig, ax = plt.subplots(figsize=(8, 5))
    if other_points:
        ax.scatter(
            [point.cost for point in other_points],
            [point.best_ratio for point in other_points],
            label="non-selected",
            c="#3A86FF",
            alpha=0.7,
            s=35,
        )
    if selected_points:
        ax.scatter(
            [point.cost for point in selected_points],
            [point.best_ratio for point in selected_points],
            label="selected",
            c="#FB5607",
            alpha=0.9,
            s=45,
            marker="D",
        )
    ax.axhline(1.0, color="#666666", linestyle="--", linewidth=1)
    ax.set_title(title, loc="left")
    ax.set_xlabel("Effective VPlan cost (cost / VF)")
    ax.set_ylabel("Best ratio (1.0 = best in bench)")
    ax.legend(loc="best")
    data_url = figure_to_data_url(fig)
    plt.close(fig)
    return data_url


def render_bench_detail(summary: BenchMetricSummary) -> str:
    rankable = [point for point in summary.points if point.cost_rank is not None and point.actual_rank is not None]
    if not summary.points:
        return make_placeholder_figure(summary.bench, "No successful samples available.")

    ordered_points = sorted(
        summary.points,
        key=lambda point: (
            point.actual_rank if point.actual_rank is not None else 999,
            point.median_value,
            parse_vf_key(point.use_vf),
        ),
    )

    plt, _ = require_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    ax = axes[0]
    labels = [point.use_vf for point in ordered_points]
    samples = [point.samples for point in ordered_points]
    boxplot = ax.boxplot(samples, tick_labels=labels, patch_artist=True)
    for patch, point in zip(boxplot["boxes"], ordered_points):
        patch.set_facecolor("#FB5607" if point.selected else "#3A86FF")
        patch.set_alpha(0.45 if point.selected else 0.25)
    for index, point in enumerate(ordered_points, start=1):
        xs = [index] * len(point.samples)
        ax.scatter(xs, point.samples, s=12, c="#1D3557", alpha=0.6)
    ax.set_title(f"{summary.bench}: kernel_cycles distribution", loc="left")
    ax.set_xlabel("VF")
    ax.set_ylabel("Cycles")
    ax.tick_params(axis="x", rotation=45)

    ax = axes[1]
    if rankable:
        max_rank = max(
            max(point.cost_rank or 0, point.actual_rank or 0)
            for point in rankable
        )
        for point in sorted(rankable, key=lambda item: parse_vf_key(item.use_vf)):
            color = "#FB5607" if point.selected else "#3A86FF"
            ax.plot([0, 1], [point.cost_rank, point.actual_rank], color=color, linewidth=2, alpha=0.85)
            ax.scatter([0, 1], [point.cost_rank, point.actual_rank], color=color, s=40)
            ax.text(-0.05, point.cost_rank, point.use_vf, ha="right", va="center", fontsize=9)
            ax.text(1.05, point.actual_rank, point.use_vf, ha="left", va="center", fontsize=9)
        ax.set_xlim(-0.25, 1.25)
        ax.set_ylim(max_rank + 0.5, 0.5)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Effective cost rank", "Latency rank"])
        ax.set_yticks(range(1, max_rank + 1))
        ax.set_title(f"{summary.bench}: rank change", loc="left")
        ax.grid(axis="y", color="#DDDDDD", linewidth=0.8)
    else:
        ax.axis("off")
        ax.text(0.02, 0.5, "No rankable points with cost + latency.", transform=ax.transAxes, va="center")

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
    return [
        ("VFS DB", str(data.vfs_db)),
        ("Emulate DB", str(data.emulate_db)),
        ("Generated", datetime.now().isoformat(timespec="seconds")),
        ("Benchmarks", str(len(data.benches))),
        ("Kernel comparable benches", str(len(comparable))),
        ("VPlan failures", str(len(data.vplan_failures))),
        ("Emulate failures", str(sum(data.emulate_failure_counts.values()))),
        ("Selected VF matches actual best", f"{len(selected_matches)}/{len(comparable) or 0}"),
    ]


def build_top_mismatch_rows(summaries: list[BenchMetricSummary], limit: int) -> list[list[str]]:
    ordered = sorted(
        summaries,
        key=lambda summary: (
            summary.max_abs_rank_delta is None,
            -(summary.max_abs_rank_delta or -1),
            abs(summary.selected_rank_delta or 0),
            summary.bench,
        ),
    )
    rows: list[list[str]] = []
    for summary in ordered[:limit]:
        rows.append(
            [
                summary.bench,
                summary.selected_vf or "-",
                summary.cost_best_vf or "-",
                summary.actual_best_vf or "-",
                str(summary.max_abs_rank_delta) if summary.max_abs_rank_delta is not None else "-",
                str(summary.selected_rank_delta) if summary.selected_rank_delta is not None else "-",
                format_float(summary.spearman, digits=2),
            ]
        )
    return rows


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


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    if not rows:
        return "<p class='empty'>No rows.</p>"
    thead = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{escape(cell)}</td>" for cell in row)
        body_rows.append(f"<tr>{cells}</tr>")
    return "<table><thead><tr>" + thead + "</tr></thead><tbody>" + "".join(body_rows) + "</tbody></table>"


def render_image_section(title: str, data_url: str, caption: str = "") -> str:
    caption_html = f"<p class='caption'>{escape(caption)}</p>" if caption else ""
    return (
        "<section class='plot-section'>"
        f"<h2>{escape(title)}</h2>"
        f"{caption_html}"
        f"<img src='{data_url}' alt='{escape(title)}' />"
        "</section>"
    )


def render_html(data: ReportData, plots: dict[str, str], top_rows: list[list[str]], top_benches: list[str]) -> str:
    cards_html = render_cards(build_summary_cards(data))
    top_table = render_table(
        [
            "bench",
            "selected_vf",
            "cost_best_vf",
            "actual_best_vf",
            "max_abs_rank_delta",
            "selected_rank_delta",
            "spearman",
        ],
        top_rows,
    )

    detail_sections = []
    kernel_map = {summary.bench: summary for summary in data.metric_summaries["kernel_cycles"]}
    for bench in top_benches:
        summary = kernel_map.get(bench)
        if summary is None:
            continue
        title = f"Bench detail: {bench}"
        caption = (
            f"selected={summary.selected_vf or '-'}, cost-best={summary.cost_best_vf or '-'}, "
            f"actual-best={summary.actual_best_vf or '-'}"
        )
        detail_sections.append(render_image_section(title, plots[f"detail:{bench}"], caption))

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8' />",
        "<meta name='viewport' content='width=device-width, initial-scale=1' />",
        "<title>VPlan vs Emulate Report</title>",
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
          grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
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
        table {
          width: 100%;
          border-collapse: collapse;
          background: var(--card);
          border: 1px solid var(--line);
          border-radius: 12px;
          overflow: hidden;
        }
        th, td {
          padding: 10px 12px;
          border-bottom: 1px solid var(--line);
          text-align: left;
          font-size: 14px;
        }
        thead th {
          background: #ecebe5;
        }
        .empty {
          padding: 12px 0;
        }
        @media (max-width: 720px) {
          body {
            padding: 14px;
          }
          .plot-section {
            padding: 12px;
          }
        }
        """,
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<h1>VPlan Effective Cost vs Emulate Latency</h1>",
        "<p>Single-file HTML report with base64-embedded plot images.</p>",
        cards_html,
        render_image_section(
            "Coverage summary",
            plots["coverage"],
            "Failures and candidate coverage before reading cost-vs-latency plots.",
        ),
        render_image_section(
            "Best ratio heatmap: kernel_cycles",
            plots["best_ratio:kernel_cycles"],
            "Each cell is median(metric) / best median in the same bench. Selected VF is marked with a star.",
        ),
        render_image_section(
            "Best ratio heatmap: total_cycles",
            plots["best_ratio:total_cycles"],
            "Same view for total_cycles.",
        ),
        render_image_section(
            "Effective cost vs latency scatter: kernel_cycles",
            plots["scatter:kernel_cycles"],
            "Lower and closer to 1.0 is better. Orange diamonds are LLVM-selected VFs.",
        ),
        render_image_section(
            "Effective cost vs latency scatter: total_cycles",
            plots["scatter:total_cycles"],
            "Same view for total_cycles.",
        ),
        render_image_section(
            "Rank delta heatmap: kernel_cycles",
            plots["rank_delta:kernel_cycles"],
            "actual_rank - cost_rank. Positive means measured latency ranked worse than effective cost predicted.",
        ),
        render_image_section(
            "Rank delta heatmap: total_cycles",
            plots["rank_delta:total_cycles"],
            "Same view for total_cycles.",
        ),
        "<section class='plot-section'>",
        "<h2>Top mismatch benches</h2>",
        "<p>Kernel-based ranking gap between effective VPlan cost order (cost / VF) and measured latency order.</p>",
        top_table,
        "</section>",
        *detail_sections,
        "</main>",
        "</body>",
        "</html>",
    ]
    return "".join(html_parts)


def generate_plots(data: ReportData, top_mismatch_benches: int) -> tuple[dict[str, str], list[list[str]], list[str]]:
    plots = {
        "coverage": render_coverage_summary(data),
    }
    for metric_name, summaries in data.metric_summaries.items():
        label = metric_label(metric_name)
        plots[f"best_ratio:{metric_name}"] = render_heatmap(
            summaries,
            title=f"Best ratio heatmap ({label})",
            value_kind="best_ratio",
        )
        plots[f"scatter:{metric_name}"] = render_scatter(
            summaries,
            title=f"Effective cost vs latency ({label})",
        )
        plots[f"rank_delta:{metric_name}"] = render_heatmap(
            summaries,
            title=f"Rank delta heatmap ({label})",
            value_kind="rank_delta",
        )

    kernel_summaries = data.metric_summaries["kernel_cycles"]
    top_rows = build_top_mismatch_rows(kernel_summaries, top_mismatch_benches)
    top_benches = [row[0] for row in top_rows]
    kernel_map = {summary.bench: summary for summary in kernel_summaries}
    for bench in top_benches:
        summary = kernel_map.get(bench)
        if summary is None:
            continue
        plots[f"detail:{bench}"] = render_bench_detail(summary)
    return plots, top_rows, top_benches


def main() -> None:
    args = parse_args()
    if args.top_mismatch_benches <= 0:
        fail("--top-mismatch-benches must be a positive integer")

    root = repo_root()
    bench_filter = {bench.strip() for bench in args.bench if bench.strip()}
    vfs_db = resolve_input_path(root, args.vfs_db)
    emulate_db = resolve_latest_emulate_db(root, args.emulate_db)
    output_html = resolve_output_html(root, args.output_html, emulate_db)

    data = load_report_data(vfs_db, emulate_db, bench_filter)
    plots, top_rows, top_benches = generate_plots(data, args.top_mismatch_benches)
    report_html = render_html(data, plots, top_rows, top_benches)
    output_html.write_text(report_html, encoding="utf-8")
    print(f"wrote {output_html}")


if __name__ == "__main__":
    main()
