#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

try:
    import cairo
except ModuleNotFoundError:
    cairo = None

try:
    import plot_results
except ModuleNotFoundError:
    from scripts import plot_results


DEFAULT_OUTPUT_ROOT = "artifacts/plots"
DEFAULT_PREFIX = "rvv-intel-kernel"
DEFAULT_MAX_TOPN = 4

COLORS = {
    "rvv": "#dc2626",
    "rvv_fill": "#dc262633",
    "intel": "#2563eb",
    "intel_fill": "#2563eb33",
    "axis": "#111827",
    "grid": "#d1d5db",
    "muted": "#6b7280",
    "bound": "#9ca3af",
}

TOPN_COLORS = [
    "#a61e2d",
    "#fff9b0",
    "#bfe07f",
    "#2f6f3e",
]


@dataclass
class Dataset:
    label: str
    result_db: Path
    vfs_db: Path
    report: plot_results.ReportData


@dataclass
class BoxStats:
    values: list[float]
    minimum: float
    q1: float
    median: float
    q3: float
    maximum: float
    lower_whisker: float
    upper_whisker: float


def fail(message: str, exit_code: int = 2) -> "NoReturn":
    print(message)
    raise SystemExit(exit_code)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate RVV-vs-Intel comparison PNG plots from emulate/profile SQLite outputs."
    )
    parser.add_argument("--emulate-db", default="", help="Path to emulate-result-*.sqlite")
    parser.add_argument("--profile-db", default="", help="Path to profile-result-*.sqlite")
    parser.add_argument("--emulate-vfs-db", default="", help="Optional RVV vfs DB override")
    parser.add_argument("--profile-vfs-db", default="", help="Optional Intel vfs DB override")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_ROOT, help="Output directory")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX, help="Output filename prefix")
    parser.add_argument("--max-topn", type=int, default=DEFAULT_MAX_TOPN, help="Max Top-N bucket")
    return parser.parse_args()


def resolve_input_path(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (root / value).resolve()
    if not path.exists():
        fail(f"input file not found: {path}")
    return path


def resolve_latest_result_db(root: Path, pattern: str) -> Path:
    matches = sorted((root / "artifacts").glob(pattern))
    if not matches:
        fail(f"no files matched artifacts/{pattern}")
    return matches[-1].resolve()


def resolve_vfs_db(root: Path, explicit: str, result_db: Path) -> Path:
    if explicit:
        return resolve_input_path(root, explicit)
    _, target = plot_results.load_result_metadata(result_db)
    suffix = plot_results._TARGET_TO_VFS_SUFFIX.get(target, plot_results._DEFAULT_VFS_SUFFIX)
    return resolve_input_path(root, f"artifacts/vfs-{suffix}.db")


def load_dataset(root: Path, label: str, result_value: str, vfs_value: str) -> Dataset:
    if result_value:
        result_db = resolve_input_path(root, result_value)
    else:
        pattern = "emulate-result-*.sqlite" if label == "rvv" else "profile-result-*.sqlite"
        result_db = resolve_latest_result_db(root, pattern)
    vfs_db = resolve_vfs_db(root, vfs_value, result_db)
    report = plot_results.load_report_data(vfs_db, result_db, set())
    return Dataset(label=label, result_db=result_db, vfs_db=vfs_db, report=report)


def speedup_values(dataset: Dataset) -> list[float]:
    entries = plot_results.build_speedup_data(dataset.report.metric_summaries)["kernel_cycles"]
    return [float(entry["speedup"]) for entry in entries]


def spearman_values(dataset: Dataset) -> list[float]:
    return [
        float(summary.spearman)
        for summary in dataset.report.metric_summaries["kernel_cycles"]
        if summary.spearman is not None
    ]


def topn_distributions(dataset: Dataset, max_topn: int) -> tuple[list[int], list[list[float]], list[int]]:
    return plot_results.build_top_n_overlap_distributions(
        dataset.report.metric_summaries["kernel_cycles"],
        max_n=max_topn,
    )


def quartiles(values: list[float]) -> tuple[float, float, float]:
    ordered = sorted(values)
    med = statistics.median(ordered)
    half = len(ordered) // 2
    if len(ordered) % 2 == 0:
        lower = ordered[:half]
        upper = ordered[half:]
    else:
        lower = ordered[:half]
        upper = ordered[half + 1 :]
    q1 = statistics.median(lower) if lower else ordered[0]
    q3 = statistics.median(upper) if upper else ordered[-1]
    return q1, med, q3


def compute_box_stats(values: list[float]) -> BoxStats:
    if not values:
        fail("cannot render box plot with no data")
    ordered = sorted(values)
    q1, med, q3 = quartiles(ordered)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    inliers = [value for value in ordered if lower_bound <= value <= upper_bound]
    return BoxStats(
        values=ordered,
        minimum=ordered[0],
        q1=q1,
        median=med,
        q3=q3,
        maximum=ordered[-1],
        lower_whisker=inliers[0] if inliers else ordered[0],
        upper_whisker=inliers[-1] if inliers else ordered[-1],
    )


def place_label_rows(
    desired_rows: list[tuple[str, float]],
    *,
    min_y: float,
    max_y: float,
    gap: float,
) -> list[tuple[str, float]]:
    if not desired_rows:
        return []
    placed: list[list[object]] = [[text, min(max(y, min_y), max_y)] for text, y in desired_rows]
    for index in range(1, len(placed)):
        prev_y = float(placed[index - 1][1])
        placed[index][1] = max(float(placed[index][1]), prev_y + gap)
    overflow = float(placed[-1][1]) - max_y
    if overflow > 0:
        for item in placed:
            item[1] = float(item[1]) - overflow
    for index in range(len(placed) - 2, -1, -1):
        next_y = float(placed[index + 1][1])
        placed[index][1] = min(float(placed[index][1]), next_y - gap)
    underflow = min_y - float(placed[0][1])
    if underflow > 0:
        for item in placed:
            item[1] = float(item[1]) + underflow
    return [(str(text), float(y)) for text, y in placed]


def require_cairo() -> None:
    if cairo is None:
        fail("pycairo is required to render PNG plots.")


def set_color(ctx: "cairo.Context", hex_color: str, alpha: float = 1.0) -> None:
    value = hex_color.lstrip("#")
    r = int(value[0:2], 16) / 255.0
    g = int(value[2:4], 16) / 255.0
    b = int(value[4:6], 16) / 255.0
    ctx.set_source_rgba(r, g, b, alpha)


def draw_text(
    ctx: "cairo.Context",
    x: float,
    y: float,
    text: str,
    *,
    size: float,
    color: str,
    anchor: str = "start",
    bold: bool = False,
) -> None:
    ctx.save()
    set_color(ctx, color)
    ctx.select_font_face(
        "Helvetica",
        cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
    )
    ctx.set_font_size(size)
    ext = ctx.text_extents(text)
    dx = 0.0
    if anchor == "middle":
        dx = -(ext.width / 2.0 + ext.x_bearing)
    elif anchor == "end":
        dx = -(ext.width + ext.x_bearing)
    ctx.move_to(x + dx, y)
    ctx.show_text(text)
    ctx.restore()


def draw_text_box(
    ctx: "cairo.Context",
    x: float,
    y: float,
    text: str,
    *,
    size: float,
    text_color: str,
    anchor: str = "middle",
    bold: bool = False,
    box_fill: str = "#ffffff",
    box_alpha: float = 0.72,
    pad_x: float = 6.0,
    pad_y: float = 4.0,
) -> None:
    ctx.save()
    ctx.select_font_face(
        "Helvetica",
        cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
    )
    ctx.set_font_size(size)
    ext = ctx.text_extents(text)
    box_x = x
    if anchor == "middle":
        box_x = x - (ext.width / 2.0 + ext.x_bearing) - pad_x
    elif anchor == "end":
        box_x = x - (ext.width + ext.x_bearing) - pad_x
    else:
        box_x = x + ext.x_bearing - pad_x
    box_y = y + ext.y_bearing - pad_y
    box_w = ext.width + pad_x * 2.0
    box_h = ext.height + pad_y * 2.0
    draw_rect(ctx, box_x, box_y, box_w, box_h, fill=box_fill, fill_alpha=box_alpha, stroke=None)
    ctx.restore()
    draw_text(ctx, x, y, text, size=size, color=text_color, anchor=anchor, bold=bold)


def draw_line(
    ctx: "cairo.Context",
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: str,
    width: float = 2.0,
    dash: tuple[float, ...] = (),
) -> None:
    ctx.save()
    set_color(ctx, color)
    ctx.set_line_width(width)
    ctx.set_dash(dash)
    ctx.move_to(x1, y1)
    ctx.line_to(x2, y2)
    ctx.stroke()
    ctx.restore()


def draw_rect(
    ctx: "cairo.Context",
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: str | None = None,
    fill_alpha: float = 1.0,
    stroke: str | None = None,
    stroke_width: float = 2.0,
) -> None:
    ctx.save()
    ctx.rectangle(x, y, width, height)
    if fill is not None:
        set_color(ctx, fill, fill_alpha)
        if stroke is not None:
            ctx.fill_preserve()
        else:
            ctx.fill()
    if stroke is not None:
        set_color(ctx, stroke)
        ctx.set_line_width(stroke_width)
        ctx.stroke()
    ctx.restore()


def draw_circle(ctx: "cairo.Context", x: float, y: float, radius: float, *, color: str, alpha: float = 1.0) -> None:
    ctx.save()
    set_color(ctx, color, alpha)
    ctx.arc(x, y, radius, 0.0, 2.0 * math.pi)
    ctx.fill()
    ctx.restore()


def scale_linear(value: float, domain_min: float, domain_max: float, range_min: float, range_max: float) -> float:
    if domain_max == domain_min:
        return (range_min + range_max) / 2.0
    t = (value - domain_min) / (domain_max - domain_min)
    return range_min + t * (range_max - range_min)


def render_boxplot_png(
    png_path: Path,
    *,
    title: str,
    y_label: str,
    left_label: str,
    left_values: list[float],
    right_label: str,
    right_values: list[float],
    left_color: str,
    left_fill: str,
    right_color: str,
    right_fill: str,
    y_min: float,
    y_max: float,
) -> None:
    require_cairo()
    width = 2504
    height = 1136
    left = 140
    right = 120
    top = 90
    bottom = 120
    plot_w = width - left - right
    plot_h = height - top - bottom
    x0 = left
    y0 = height - bottom

    left_stats = compute_box_stats(left_values)
    right_stats = compute_box_stats(right_values)

    def py(value: float) -> float:
        return scale_linear(value, y_min, y_max, y0, y0 - plot_h)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()

    draw_text(ctx, width / 2.0, 50, title, size=34, color=COLORS["axis"], anchor="middle")

    for tick in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        y = py(tick)
        draw_line(ctx, x0, y, x0 + plot_w, y, color=COLORS["grid"], width=1)
        draw_text(ctx, x0 - 16, y + 6, f"{tick:.1f}", size=16, color=COLORS["axis"], anchor="end")

    draw_line(ctx, x0, y0, x0 + plot_w, y0, color=COLORS["axis"], width=2)
    draw_line(ctx, x0, top, x0, y0, color=COLORS["axis"], width=2)
    draw_text(ctx, 34, top + plot_h / 2.0, y_label, size=24, color=COLORS["axis"])

    draw_line(ctx, x0, py(0.0), x0 + plot_w, py(0.0), color=COLORS["bound"], width=2, dash=(6, 4))
    draw_line(ctx, x0, py(1.0), x0 + plot_w, py(1.0), color=COLORS["bound"], width=2, dash=(6, 4))
    draw_text(ctx, x0 + plot_w - 8, py(1.0) - 4, "upper bound=1.000", size=16, color=COLORS["bound"], anchor="end")
    draw_text(ctx, x0 + plot_w - 8, py(0.0) + 22, "lower bound=0.000", size=16, color=COLORS["bound"], anchor="end")

    centers = [x0 + plot_w * 0.28, x0 + plot_w * 0.72]
    box_width = plot_w * 0.14

    def render_group(center: float, label: str, stats: BoxStats, stroke: str, fill: str, side: str) -> None:
        box_left = center - box_width / 2.0
        box_right = center + box_width / 2.0
        draw_line(ctx, center, py(stats.lower_whisker), center, py(stats.q1), color=stroke, width=4)
        draw_line(ctx, center, py(stats.q3), center, py(stats.upper_whisker), color=stroke, width=4)
        draw_line(ctx, box_left + 20, py(stats.lower_whisker), box_right - 20, py(stats.lower_whisker), color=stroke, width=4)
        draw_line(ctx, box_left + 20, py(stats.upper_whisker), box_right - 20, py(stats.upper_whisker), color=stroke, width=4)
        draw_rect(
            ctx,
            box_left,
            py(stats.q3),
            box_width,
            py(stats.q1) - py(stats.q3),
            fill=fill,
            fill_alpha=0.28,
            stroke=stroke,
            stroke_width=4,
        )
        draw_line(ctx, box_left, py(stats.median), box_right, py(stats.median), color=stroke, width=4)

        for index, value in enumerate(stats.values):
            jitter = ((index % 9) - 4) * 3.8
            draw_circle(ctx, center + jitter, py(value), 5.5, color=stroke, alpha=0.55)

        draw_text(ctx, center, y0 + 40, label, size=24, color=COLORS["axis"], anchor="middle")
        label_x = box_right + 120 if side == "right" else box_left - 120
        anchor = "start" if side == "right" else "end"
        labels = place_label_rows(
            [
                (f"n={len(stats.values)}", top + 28),
                (f"max={stats.maximum:.3f}", py(stats.maximum) + 4),
                (f"upper fence={stats.upper_whisker:.3f}", py(stats.upper_whisker) + 4),
                (f"q3={stats.q3:.3f}", py(stats.q3) + 4),
                (f"median={stats.median:.3f}", py(stats.median) + 4),
                (f"min={stats.minimum:.3f}", py(stats.minimum) + 4),
            ],
            min_y=top + 24,
            max_y=y0 - 12,
            gap=24,
        )
        for text, label_y in labels:
            draw_text(ctx, label_x, label_y, text, size=16 if text.startswith("n=") else 15, color=stroke, anchor=anchor, bold=True)

    render_group(centers[0], left_label, left_stats, left_color, left_fill, "left")
    render_group(centers[1], right_label, right_stats, right_color, right_fill, "right")
    surface.write_to_png(str(png_path))


def render_topn_png(
    png_path: Path,
    *,
    title: str,
    rvv_ns: list[int],
    rvv_distributions: list[list[float]],
    rvv_eligible: list[int],
    intel_ns: list[int],
    intel_distributions: list[list[float]],
    intel_eligible: list[int],
) -> None:
    require_cairo()
    if rvv_ns != intel_ns:
        fail("RVV and Intel Top-N buckets do not align; cannot render Top-N plot.")
    ns = rvv_ns

    width = 2504
    height = 1136
    left = 90
    right = 50
    top = 88
    bottom = 90
    plot_w = width - left - right
    plot_h = height - top - bottom
    x0 = left
    y0 = height - bottom

    def py(value: float) -> float:
        return scale_linear(value, 0.0, 1.0, y0, y0 - plot_h)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()

    draw_text(ctx, width / 2.0, 36, title, size=32, color=COLORS["axis"], anchor="middle")

    for tick in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        y = py(tick)
        draw_line(ctx, x0, y, x0 + plot_w, y, color=COLORS["grid"], width=1)
        draw_text(ctx, x0 - 14, y + 6, f"{tick:.1f}", size=15, color=COLORS["axis"], anchor="end")

    draw_line(ctx, x0, y0, x0 + plot_w, y0, color=COLORS["axis"], width=2)
    draw_line(ctx, x0, top, x0, y0, color=COLORS["axis"], width=2)
    draw_text(ctx, 42, top + plot_h / 2.0, "Bench share", size=22, color=COLORS["axis"])

    group_gap = plot_w / max(1, len(ns))
    bar_width = group_gap * 0.33

    def histogram(distribution: list[float], n: int) -> list[float]:
        shares = [0.0] * (n + 1)
        if not distribution:
            return shares
        for ratio in distribution:
            overlap = int(round(ratio * n))
            shares[max(0, min(n, overlap))] += 1.0 / len(distribution)
        return shares

    for idx, n in enumerate(ns):
        group_center = x0 + group_gap * (idx + 0.5)
        rvv_center = group_center - bar_width * 0.55
        intel_center = group_center + bar_width * 0.55

        draw_text(ctx, group_center, y0 + 38, f"Top-{n}", size=18, color=COLORS["axis"], anchor="middle")

        for center, label, border, shares, eligible in [
            (rvv_center, "RVV", COLORS["rvv"], histogram(rvv_distributions[idx], n), rvv_eligible[idx]),
            (intel_center, "Intel", COLORS["intel"], histogram(intel_distributions[idx], n), intel_eligible[idx]),
        ]:
            draw_text_box(ctx, center, top - 24, label, size=18, text_color=border, anchor="middle", bold=True)
            draw_text_box(ctx, center, top - 2, f"n={eligible}", size=15, text_color=border, anchor="middle", bold=True)

            bottom_share = 0.0
            for overlap in range(0, n + 1):
                share = shares[overlap]
                if share <= 0.0:
                    continue
                y_top = py(bottom_share + share)
                y_bottom = py(bottom_share)
                color = TOPN_COLORS[min(overlap, len(TOPN_COLORS) - 1)]
                draw_rect(
                    ctx,
                    center - bar_width / 2.0,
                    y_top,
                    bar_width,
                    y_bottom - y_top,
                    fill=color,
                    stroke=None,
                )
                if share >= 0.08:
                    draw_text_box(
                        ctx,
                        center,
                        (y_top + y_bottom) / 2.0 - 2,
                        f"{overlap}/{n}",
                        size=14,
                        text_color=COLORS["axis"],
                        anchor="middle",
                        bold=True,
                    )
                    draw_text_box(
                        ctx,
                        center,
                        (y_top + y_bottom) / 2.0 + 16,
                        f"{share * 100:.0f}%",
                        size=13,
                        text_color=COLORS["axis"],
                        anchor="middle",
                        box_alpha=0.58,
                    )
                bottom_share += share

            draw_rect(
                ctx,
                center - bar_width / 2.0,
                py(1.0),
                bar_width,
                py(0.0) - py(1.0),
                fill=None,
                stroke=border,
                stroke_width=2.5,
            )
            draw_text_box(
                ctx,
                center + bar_width / 2.0 + 26,
                py(1.0) + 4,
                "100%",
                size=14,
                text_color=border,
                anchor="start",
                bold=False,
            )

    surface.write_to_png(str(png_path))


def main() -> None:
    args = parse_args()
    root = repo_root()
    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = (root / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    for stem in ("speedup", "spearman", "topn"):
        (out_dir / f"{args.prefix}-{stem}.svg").unlink(missing_ok=True)

    rvv = load_dataset(root, "rvv", args.emulate_db, args.emulate_vfs_db)
    intel = load_dataset(root, "intel", args.profile_db, args.profile_vfs_db)

    render_boxplot_png(
        out_dir / f"{args.prefix}-speedup.png",
        title="Kernel Potential Speedup: RVV vs Intel",
        y_label="1 - best / default",
        left_label="RVV",
        left_values=speedup_values(rvv),
        right_label="Intel",
        right_values=speedup_values(intel),
        left_color=COLORS["rvv"],
        left_fill=COLORS["rvv"],
        right_color=COLORS["intel"],
        right_fill=COLORS["intel"],
        y_min=-0.05,
        y_max=1.08,
    )

    render_boxplot_png(
        out_dir / f"{args.prefix}-spearman.png",
        title="Kernel Spearman: RVV vs Intel",
        y_label="Spearman rank correlation",
        left_label="RVV",
        left_values=spearman_values(rvv),
        right_label="Intel",
        right_values=spearman_values(intel),
        left_color=COLORS["rvv"],
        left_fill=COLORS["rvv"],
        right_color=COLORS["intel"],
        right_fill=COLORS["intel"],
        y_min=-1.05,
        y_max=1.05,
    )

    rvv_ns, rvv_dist, rvv_eligible = topn_distributions(rvv, args.max_topn)
    intel_ns, intel_dist, intel_eligible = topn_distributions(intel, args.max_topn)
    render_topn_png(
        out_dir / f"{args.prefix}-topn.png",
        title="Kernel Top-N Overlap: RVV vs Intel",
        rvv_ns=rvv_ns,
        rvv_distributions=rvv_dist,
        rvv_eligible=rvv_eligible,
        intel_ns=intel_ns,
        intel_distributions=intel_dist,
        intel_eligible=intel_eligible,
    )

    print(f"wrote {out_dir / f'{args.prefix}-speedup.png'}")
    print(f"wrote {out_dir / f'{args.prefix}-spearman.png'}")
    print(f"wrote {out_dir / f'{args.prefix}-topn.png'}")


if __name__ == "__main__":
    main()
