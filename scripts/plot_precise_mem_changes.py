#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


COLORS = {
    "rvv": "#7f1d1d",
    "precise": "#0f766e",
    "line": "#9ca3af",
    "grid": "#e5e7eb",
    "text": "#111827",
    "muted": "#6b7280",
    "accent": "#ea580c",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot precise-mem asm-change benchmark effects.")
    parser.add_argument("--rvv-db", default="artifacts/rvv.sqlite")
    parser.add_argument("--precise-db", default="artifacts/rvv-precise.sqlite")
    parser.add_argument("--output-dir", default="artifacts/plots")
    return parser.parse_args()


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def load_rows(rvv_db: Path, precise_db: Path) -> list[dict[str, object]]:
    query = """
        WITH valid AS (
            SELECT
                r.bench,
                COALESCE(NULLIF(r.use_vf, ''), 'default') AS use_vf,
                r.asm_text AS rvv_asm,
                q.asm_text AS precise_asm,
                r.kernel_cycles AS rvv_cycles,
                q.kernel_cycles AS precise_cycles
            FROM main.emulate_results r
            JOIN p.emulate_results q USING (bench, use_vf)
            WHERE r.status = 'PASS'
              AND q.status = 'PASS'
              AND r.kernel_cycles > 0
              AND q.kernel_cycles > 0
        )
        SELECT
            bench,
            use_vf,
            rvv_cycles,
            precise_cycles,
            1.0 * precise_cycles / rvv_cycles AS cycle_ratio,
            1.0 * rvv_cycles / precise_cycles AS speedup
        FROM valid
        WHERE rvv_asm IS NOT precise_asm
        ORDER BY speedup DESC;
    """
    with sqlite3.connect(rvv_db) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("ATTACH ? AS p", (str(precise_db),))
        rows = conn.execute(query).fetchall()
    return [dict(row) for row in rows]


def cycle_label(value: float, _pos: int) -> str:
    if value >= 1000:
        return f"{value / 1000:g}k"
    return f"{value:g}"


def save_all(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    fig.savefig(output_dir / f"{stem}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_dumbbell(rows: list[dict[str, object]], output_dir: Path) -> None:
    ordered = sorted(rows, key=lambda row: float(row["speedup"]))
    labels = [f"{row['bench']} ({row['use_vf']})" for row in ordered]
    y_values = list(range(len(ordered)))
    rvv_cycles = [float(row["rvv_cycles"]) for row in ordered]
    precise_cycles = [float(row["precise_cycles"]) for row in ordered]

    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    for y, before, after in zip(y_values, rvv_cycles, precise_cycles, strict=True):
        ax.plot([after, before], [y, y], color=COLORS["line"], linewidth=2.2, zorder=1)

    ax.scatter(rvv_cycles, y_values, s=72, color=COLORS["rvv"], label="baseline rvv", zorder=3)
    ax.scatter(precise_cycles, y_values, s=72, color=COLORS["precise"], label="precise-mem", zorder=3)

    for y, row in zip(y_values, ordered, strict=True):
        label_x = math.sqrt(float(row["rvv_cycles"]) * float(row["precise_cycles"]))
        ax.annotate(
            f"{float(row['speedup']):.2f}x",
            xy=(label_x, y),
            xytext=(0, 12),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            color=COLORS["text"],
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.2},
        )

    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(FuncFormatter(cycle_label))
    ax.set_yticks(y_values, labels)
    ax.set_ylim(-0.35, len(ordered) - 0.25)
    ax.set_xlabel("kernel cycles (log scale)")
    ax.set_title("Asm-changed valid benchmarks: baseline vs precise-mem")
    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.8)
    ax.legend(frameon=False, loc="lower right")
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="y", length=0)
    save_all(fig, output_dir, "precise_mem_asm_changed_dumbbell")


def plot_cycle_ratio(rows: list[dict[str, object]], output_dir: Path) -> None:
    ordered = sorted(rows, key=lambda row: float(row["cycle_ratio"]))
    ratios = [float(row["cycle_ratio"]) for row in ordered]
    labels = [str(row["bench"]) for row in ordered]
    x_values = list(range(len(ordered)))

    fig, (ax_scatter, ax_box) = plt.subplots(
        1,
        2,
        figsize=(10.5, 4.6),
        gridspec_kw={"width_ratios": [3.2, 1.0]},
        sharey=True,
    )

    ax_scatter.axhline(1.0, color=COLORS["muted"], linestyle="--", linewidth=1.0)
    ax_scatter.scatter(x_values, ratios, s=86, color=COLORS["accent"], zorder=3)
    for x, ratio, label in zip(x_values, ratios, labels, strict=True):
        ax_scatter.annotate(
            f"{label}\n{ratio:.3f}",
            xy=(x, ratio),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8.5,
            color=COLORS["text"],
        )

    ax_scatter.set_xticks(x_values, labels)
    ax_scatter.set_ylabel("cycle ratio: precise / baseline")
    ax_scatter.set_xlabel("asm-changed benchmark")
    ax_scatter.set_title("Cycle ratio for the 6 asm changes")
    ax_scatter.grid(axis="y", color=COLORS["grid"], linewidth=0.8)

    ax_box.boxplot(
        ratios,
        vert=True,
        widths=0.42,
        patch_artist=True,
        boxprops={"facecolor": "#fed7aa", "edgecolor": COLORS["accent"], "linewidth": 1.4},
        medianprops={"color": COLORS["text"], "linewidth": 1.6},
        whiskerprops={"color": COLORS["accent"], "linewidth": 1.2},
        capprops={"color": COLORS["accent"], "linewidth": 1.2},
        flierprops={
            "marker": "o",
            "markerfacecolor": COLORS["accent"],
            "markeredgecolor": COLORS["accent"],
            "alpha": 0.55,
        },
    )
    ax_box.scatter([1] * len(ratios), ratios, s=34, color=COLORS["accent"], alpha=0.75, zorder=3)
    ax_box.axhline(1.0, color=COLORS["muted"], linestyle="--", linewidth=1.0)
    ax_box.set_xticks([1], ["box"])
    ax_box.set_title("Distribution")
    ax_box.grid(axis="y", color=COLORS["grid"], linewidth=0.8)

    y_max = max(1.05, max(ratios) * 1.18)
    ax_scatter.set_ylim(0, y_max)
    for ax in [ax_scatter, ax_box]:
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)

    save_all(fig, output_dir, "precise_mem_asm_changed_cycle_ratio")


def main() -> None:
    root = repo_root()
    args = parse_args()
    rvv_db = resolve_path(root, args.rvv_db)
    precise_db = resolve_path(root, args.precise_db)
    output_dir = resolve_path(root, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(rvv_db, precise_db)
    if not rows:
        raise SystemExit("no valid asm-changed rows found")

    plot_dumbbell(rows, output_dir)
    plot_cycle_ratio(rows, output_dir)

    print(f"wrote {len(rows)} asm-changed rows to {output_dir}")


if __name__ == "__main__":
    main()
