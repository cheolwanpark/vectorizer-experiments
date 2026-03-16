"""Textual TUI application and widgets."""

from __future__ import annotations

from .analytics import (
    _classify_vf,
    compute_category_stats,
    compute_dashboard_stats,
    compute_vf_distribution,
)
from .models import BenchResult


def _build_app_class():
    """Build and return the TUI App class (deferred import of textual)."""
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, VerticalScroll
    from textual.widgets import (
        DataTable, Footer, Header, Input, Label, ProgressBar,
        Static, TabbedContent, TabPane,
    )

    class StatCard(Static):
        def __init__(self, title: str, value: str, **kwargs):
            super().__init__(**kwargs)
            self._title = title
            self._value = value

        def compose(self) -> ComposeResult:
            yield Label(f"[bold]{self._title}[/bold]")
            yield Label(f"[cyan]{self._value}[/cyan]")

    class BarChart(Static):
        """Simple horizontal bar chart using block characters."""
        def __init__(self, data: dict[str, int], max_width: int = 40, **kwargs):
            super().__init__(**kwargs)
            self._data = data
            self._max_width = max_width

        def compose(self) -> ComposeResult:
            if not self._data:
                yield Label("No data")
                return
            max_val = max(self._data.values()) if self._data else 1
            for label, count in sorted(self._data.items(), key=lambda x: x[0]):
                bar_len = int((count / max_val) * self._max_width) if max_val > 0 else 0
                bar = "\u2588" * bar_len
                yield Label(f"{str(label):>8} \u2502 {bar} {count}")

    class ProgressScreen(Static):
        def __init__(self, total: int, **kwargs):
            super().__init__(**kwargs)
            self._total = total
            self._completed = 0
            self._log_lines: list[str] = []

        def compose(self) -> ComposeResult:
            yield Label("[bold]Running vplan-explain pipeline\u2026[/bold]", id="prog-title")
            yield ProgressBar(total=self._total, id="prog-bar")
            yield Label("0 / 0", id="prog-count")
            yield Static("", id="prog-log")

        def advance(self, func_name: str, error: str | None):
            self._completed += 1
            status = "\u2713" if not error else f"\u2717 {error[:60]}"
            self._log_lines.append(f"  {func_name}: {status}")
            display_lines = self._log_lines[-20:]
            try:
                bar = self.query_one("#prog-bar", ProgressBar)
                bar.advance(1)
                count_label = self.query_one("#prog-count", Label)
                count_label.update(f"{self._completed} / {self._total}")
                log_widget = self.query_one("#prog-log", Static)
                log_widget.update("\n".join(display_lines))
            except Exception:
                pass

    class DetailPanel(Static):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def show_result(self, result: BenchResult):
            lines = [f"[bold]{result.func_name}[/bold] ({result.category})"]
            if result.error:
                lines.append(f"[red]Error: {result.error}[/red]")
            else:
                lines.append(f"Loops: {len(result.loops)}")
                for loop in result.loops:
                    lines.append(f"  Loop[{loop.index}] path={loop.path} plans={loop.plan_count}")
                    for plan in loop.plans:
                        vfs_str = ", ".join(plan.vfs)
                        lines.append(f"    VPlan[{plan.index}] VFs={{{vfs_str}}}")
                        for vc in plan.costs:
                            cost_str = str(vc.cost) if vc.cost is not None else "n/a"
                            lines.append(f"      VF={vc.vf} cost={cost_str}")
                    if loop.selected_vf is not None:
                        lines.append(f"    \u2192 selected VF={loop.selected_vf} plan={loop.selected_plan}")
            lines.append("")
            lines.append("[dim]\u2500\u2500\u2500 Raw Output \u2500\u2500\u2500[/dim]")
            raw = result.raw_output[:3000] if result.raw_output else "(empty)"
            lines.append(raw)
            self.update("\n".join(lines))

    class VPlanDiversityApp(App):
        CSS = """
        Screen {
            layout: vertical;
        }
        #progress-container {
            height: 100%;
            padding: 1 2;
        }
        StatCard {
            width: 1fr;
            height: 3;
            padding: 0 1;
            border: solid $primary;
        }
        #stat-cards {
            height: auto;
            max-height: 5;
        }
        BarChart {
            height: auto;
            max-height: 15;
            padding: 0 1;
        }
        #bench-filter {
            dock: top;
            height: 3;
            margin: 0 0 1 0;
        }
        DataTable {
            height: 1fr;
        }
        DetailPanel {
            height: 1fr;
            max-height: 20;
            overflow-y: auto;
            border: solid $accent;
            padding: 0 1;
        }
        #dashboard-scroll {
            height: 1fr;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("d", "switch_tab('dashboard')", "Dashboard", show=False),
            Binding("b", "switch_tab('benchmarks')", "Benchmarks", show=False),
            Binding("c", "switch_tab('categories')", "Categories", show=False),
            Binding("v", "switch_tab('vf-dist')", "VF Dist", show=False),
            Binding("r", "rerun", "Re-run"),
        ]

        def __init__(self, results: list[BenchResult] | None = None,
                     runner_args: dict | None = None, **kwargs):
            super().__init__(**kwargs)
            self._results: list[BenchResult] = results or []
            self._runner_args = runner_args or {}
            self._all_bench_rows: list[tuple] = []
            self._progress_screen: ProgressScreen | None = None

        def compose(self) -> ComposeResult:
            yield Header()
            if not self._results:
                total = self._runner_args.get("total", 0)
                self._progress_screen = ProgressScreen(total, id="progress-container")
                yield self._progress_screen
            else:
                yield from self._build_tabs()
            yield Footer()

        def _build_tabs(self) -> ComposeResult:
            stats = compute_dashboard_stats(self._results)
            cat_stats = compute_category_stats(self._results)
            vf_dist = compute_vf_distribution(self._results)

            with TabbedContent():
                with TabPane("Dashboard", id="dashboard"):
                    with VerticalScroll(id="dashboard-scroll"):
                        with Horizontal(id="stat-cards"):
                            yield StatCard("Benchmarks", str(stats.total_benchmarks))
                            yield StatCard("Successful", str(stats.successful))
                            yield StatCard("Failed", str(stats.failed))
                            yield StatCard("Loops", str(stats.total_loops))
                            yield StatCard("Plans", str(stats.total_plans))

                        yield Label("\n[bold]Plan Count Distribution[/bold]")
                        yield BarChart(
                            {str(k): v for k, v in sorted(stats.plan_count_dist.items())},
                            max_width=50,
                        )

                        yield Label("\n[bold]VF Type Distribution[/bold]")
                        yield BarChart(stats.vf_type_dist, max_width=50)

                        yield Label("\n[bold]Selected VF Breakdown[/bold]")
                        top_sel = dict(sorted(
                            stats.selected_vf_dist.items(),
                            key=lambda x: x[1], reverse=True,
                        )[:15])
                        yield BarChart(top_sel, max_width=50)

                with TabPane("Benchmarks", id="benchmarks"):
                    from textual.containers import Vertical
                    with Vertical():
                        yield Input(placeholder="Filter benchmarks\u2026", id="bench-filter")
                        yield DataTable(id="bench-table")
                        yield DetailPanel(id="detail-panel")

                with TabPane("Categories", id="categories"):
                    yield DataTable(id="cat-table")

                with TabPane("VF Distribution", id="vf-dist"):
                    with VerticalScroll():
                        yield Label("[bold]Fixed VFs[/bold]")
                        yield DataTable(id="fixed-vf-table")
                        yield Label("\n[bold]Scalable VFs[/bold]")
                        yield DataTable(id="scalable-vf-table")

        def on_mount(self) -> None:
            self.title = "VPlan Diversity"
            self.sub_title = self._runner_args.get("subtitle", "")
            if self._results:
                self._populate_tables()

        def _populate_tables(self) -> None:
            try:
                bt = self.query_one("#bench-table", DataTable)
            except Exception:
                return
            bt.add_columns(
                "Benchmark", "Category", "#Loops", "#Plans",
                "VFs", "Min Cost", "Selected VF", "Status",
            )
            self._all_bench_rows = []
            for r in sorted(self._results, key=lambda x: x.func_name):
                n_loops = len(r.loops)
                n_plans = sum(len(l.plans) for l in r.loops)
                all_vfs = set()
                min_cost: int | None = None
                sel_vfs = set()
                for loop in r.loops:
                    for plan in loop.plans:
                        for vf in plan.vfs:
                            all_vfs.add(vf)
                        for vc in plan.costs:
                            if vc.cost is not None:
                                if min_cost is None or vc.cost < min_cost:
                                    min_cost = vc.cost
                    if loop.selected_vf:
                        sel_vfs.add(loop.selected_vf)
                vfs_str = ", ".join(sorted(all_vfs)[:4])
                if len(all_vfs) > 4:
                    vfs_str += "\u2026"
                min_cost_str = str(min_cost) if min_cost is not None else "-"
                sel_str = ", ".join(sorted(sel_vfs)) if sel_vfs else "-"
                status = "OK" if not r.error else "ERR"
                row = (r.func_name, r.category, str(n_loops), str(n_plans),
                       vfs_str, min_cost_str, sel_str, status)
                self._all_bench_rows.append(row)
                bt.add_row(*row, key=r.func_name)

            ct = self.query_one("#cat-table", DataTable)
            ct.add_columns(
                "Category", "#Funcs", "#Loops", "Avg Plans/Loop",
                "Fixed VFs", "Scalable VFs", "Failed",
            )
            for cs in compute_category_stats(self._results):
                ct.add_row(
                    cs.category, str(cs.func_count), str(cs.loop_count),
                    f"{cs.avg_plans_per_loop:.1f}", str(cs.fixed_vfs),
                    str(cs.scalable_vfs), str(cs.failed),
                )

            vf_dist = compute_vf_distribution(self._results)
            fixed_t = self.query_one("#fixed-vf-table", DataTable)
            scalable_t = self.query_one("#scalable-vf-table", DataTable)
            for t in (fixed_t, scalable_t):
                t.add_columns("VF", "Occurrences", "Selections", "Min Cost", "Max Cost")

            for e in vf_dist:
                min_c = str(e.min_cost) if e.min_cost is not None else "-"
                max_c = str(e.max_cost) if e.max_cost is not None else "-"
                row = (e.vf, str(e.occurrences), str(e.selections), min_c, max_c)
                if _classify_vf(e.vf) == "scalable":
                    scalable_t.add_row(*row)
                else:
                    fixed_t.add_row(*row)

        def on_input_changed(self, event: Input.Changed) -> None:
            if event.input.id != "bench-filter":
                return
            try:
                bt = self.query_one("#bench-table", DataTable)
            except Exception:
                return
            filt = event.value.lower()
            bt.clear()
            for row in self._all_bench_rows:
                if filt and not any(filt in cell.lower() for cell in row):
                    continue
                bt.add_row(*row, key=row[0])

        def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
            table = event.data_table
            if table.id != "bench-table":
                return
            row_key = event.row_key
            func_name = str(row_key.value)
            result = next((r for r in self._results if r.func_name == func_name), None)
            if result:
                try:
                    dp = self.query_one("#detail-panel", DetailPanel)
                    dp.show_result(result)
                except Exception:
                    pass

        def action_switch_tab(self, tab_id: str) -> None:
            try:
                tc = self.query_one(TabbedContent)
                tc.active = tab_id
            except Exception:
                pass

        async def action_rerun(self) -> None:
            self.notify("Re-run not yet implemented in TUI mode. Restart the tool.")

        def set_results(self, results: list[BenchResult]) -> None:
            """Called after pipeline completes to switch from progress to dashboard."""
            self._results = results
            self.refresh()

    return VPlanDiversityApp, ProgressScreen
