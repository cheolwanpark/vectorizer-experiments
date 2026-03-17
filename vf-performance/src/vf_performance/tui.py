"""Textual TUI for the VF performance dashboard."""

from __future__ import annotations

from .analytics import (
    build_analysis_detail,
    build_run_detail,
    compute_benchmark_rows,
    compute_cost_latency_rows,
    compute_overview,
)
from .models import AppRuntimeConfig, BenchmarkAnalysis, RunResult, SessionData


def _build_app_class():
    """Build and return the TUI App class with deferred Textual imports."""
    from rich.text import Text
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.widgets import DataTable, Footer, Header, Label, ProgressBar, Static, TabbedContent, TabPane

    _NUMERIC_COLUMNS = {
        "Benchmarks",
        "Analyzed OK",
        "Analyzed Failed",
        "Total Runs",
        "Completed Runs",
        "Failed Runs",
        "Cache Hits",
        "Cost/Latency Matches",
        "Loops",
        "Unique VFs",
        "Default Cycles",
        "Best Cost",
        "Best Latency",
        "Loop",
        "Selected Plan",
        "Selected Cost",
        "Kernel Cycles",
        "Total Cycles",
        "Wall Time (s)",
        "Delta",
        "Speedup",
        "Candidates",
    }

    class StatCard(Static):
        def __init__(self, title: str, value: str, **kwargs):
            super().__init__(**kwargs)
            self._title = title
            self._value = value

        def compose(self) -> ComposeResult:
            yield Label(f"[bold]{self._title}[/bold]")
            yield Label(f"[cyan]{self._value}[/cyan]")

    class DetailPanel(Static):
        def show_text(self, content: str) -> None:
            self.update(content or "No details.")

    class ProgressScreen(Static):
        def __init__(self, total: int = 0, **kwargs):
            super().__init__(**kwargs)
            self._total = total
            self._completed = 0
            self._log_lines: list[str] = []

        def compose(self) -> ComposeResult:
            yield Label("[bold]Running VF performance pipeline…[/bold]", id="prog-title")
            yield Label("Phase: waiting", id="prog-phase")
            yield ProgressBar(total=max(self._total, 1), id="prog-bar")
            yield Label("0 / 0", id="prog-count")
            yield Static("", id="prog-log")

        def set_total(self, total: int) -> None:
            self._total = max(total, 0)
            try:
                self.query_one("#prog-bar", ProgressBar).total = max(total, 1)
                self.query_one("#prog-count", Label).update(f"{self._completed} / {self._total}")
            except Exception:
                pass

        def advance(self, message: str, completed: int | None = None,
                    total: int | None = None, phase: str | None = None) -> None:
            if total is not None:
                self._total = max(total, 0)
            if completed is not None:
                delta = max(completed - self._completed, 0)
                self._completed = completed
            else:
                delta = 1
                self._completed += 1
            self._log_lines.append(message)
            display_lines = self._log_lines[-20:]
            try:
                if phase is not None:
                    self.query_one("#prog-phase", Label).update(f"Phase: {phase}")
                bar = self.query_one("#prog-bar", ProgressBar)
                if completed is not None:
                    bar.progress = self._completed
                else:
                    bar.advance(delta)
                self.query_one("#prog-count", Label).update(f"{self._completed} / {self._total}")
                self.query_one("#prog-log", Static).update("\n".join(display_lines))
            except Exception:
                pass

    class VFPerformanceApp(App):
        CSS = """
        Screen {
            layout: vertical;
        }
        #progress-container {
            height: 100%;
            padding: 1 2;
        }
        #dashboard-scroll {
            height: 1fr;
        }
        #stat-cards {
            height: auto;
            max-height: 5;
        }
        StatCard {
            width: 1fr;
            height: 3;
            padding: 0 1;
            border: solid $primary;
        }
        DataTable {
            height: 1fr;
        }
        DetailPanel {
            height: 1fr;
            border: solid $accent;
            padding: 0 1;
            overflow-y: auto;
        }
        #runs-main, #bench-main, #cost-main, #fail-main {
            height: 1fr;
        }
        #runs-table, #bench-table, #cost-table, #fail-table {
            width: 70%;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("o", "switch_tab('overview')", "Overview"),
            Binding("r", "switch_tab('runs')", "Runs"),
            Binding("b", "switch_tab('benchmarks')", "Benchmarks"),
            Binding("c", "switch_tab('cost-latency')", "Cost vs Latency"),
            Binding("f", "switch_tab('failures')", "Failures"),
            Binding("s", "cycle_sort", "Sort"),
        ]

        def __init__(
            self,
            session: SessionData | None = None,
            runner_args: dict | None = None,
            subtitle: str | None = None,
            runtime_config: AppRuntimeConfig | None = None,
            **kwargs,
        ):
            super().__init__(**kwargs)
            self._session = session or SessionData()
            self._runner_args = runner_args or {}
            if subtitle is not None:
                self._runner_args["subtitle"] = subtitle
            self._runtime_config = runtime_config
            self._progress_screen: ProgressScreen | None = None
            self._sort_state: dict[str, tuple] = {}
            self._col_labels: dict[str, dict] = {}
            self._analysis_map: dict[str, BenchmarkAnalysis] = {}
            self._run_map: dict[str, RunResult] = {}
            self._cost_map: dict[str, tuple] = {}
            self._all_run_rows: list[tuple[str, ...]] = []
            self._all_bench_rows: list[tuple[str, ...]] = []
            self._all_cost_rows: list[tuple[str, ...]] = []
            self._all_fail_rows: list[tuple[str, ...]] = []

        def compose(self) -> ComposeResult:
            yield Header()
            if not self._session.analyses and not self._session.runs:
                total = int(self._runner_args.get("total", 0))
                self._progress_screen = ProgressScreen(total=total, id="progress-container")
                yield self._progress_screen
            else:
                yield from self._build_tabs()
            yield Footer()

        def _build_tabs(self) -> ComposeResult:
            overview = compute_overview(self._session.analyses, self._session.runs)
            with TabbedContent():
                with TabPane("Overview", id="overview"):
                    with VerticalScroll(id="dashboard-scroll"):
                        with Horizontal(id="stat-cards"):
                            yield StatCard("Benchmarks", str(overview.total_benchmarks))
                            yield StatCard("Analyzed OK", str(overview.analyzed_ok))
                            yield StatCard("Analyzed Failed", str(overview.analyzed_failed))
                            yield StatCard("Total Runs", str(overview.total_runs))
                            yield StatCard("Completed Runs", str(overview.completed_runs))
                            yield StatCard("Failed Runs", str(overview.failed_runs))
                            yield StatCard("Cache Hits", str(overview.cache_hits))
                            yield StatCard("Matches", str(overview.agreement_count))

                with TabPane("Runs", id="runs"):
                    with Horizontal(id="runs-main"):
                        yield DataTable(id="runs-table")
                        yield DetailPanel(id="runs-detail")

                with TabPane("Benchmarks", id="benchmarks"):
                    with Horizontal(id="bench-main"):
                        yield DataTable(id="bench-table")
                        yield DetailPanel(id="bench-detail")

                with TabPane("Cost vs Latency", id="cost-latency"):
                    with Horizontal(id="cost-main"):
                        yield DataTable(id="cost-table")
                        yield DetailPanel(id="cost-detail")

                with TabPane("Failures", id="failures"):
                    with Horizontal(id="fail-main"):
                        yield DataTable(id="fail-table")
                        yield DetailPanel(id="fail-detail")

        def on_mount(self) -> None:
            self.title = "VF Performance"
            self.sub_title = self._runner_args.get("subtitle", "")
            if self._session.analyses or self._session.runs:
                self._populate_tables()
                self._focus_active_table()

        def _register_columns(self, table, *labels) -> None:
            padded = [f"{label}  " for label in labels]
            keys = table.add_columns(*padded)
            self._col_labels[table.id] = dict(zip(keys, labels))

        def _make_sort_key(self, label: str):
            if label in _NUMERIC_COLUMNS:
                def _numeric(value):
                    text = str(value).replace(",", "").strip()
                    if text in {"", "-", "None"}:
                        return float("inf")
                    try:
                        return float(text)
                    except ValueError:
                        return float("inf")
                return _numeric
            return lambda value: str(value).lower()

        def _apply_sort(self, table, column_key, reverse: bool) -> None:
            base = self._col_labels[table.id][column_key]
            table.sort(column_key, key=self._make_sort_key(base), reverse=reverse)
            for key in table.columns:
                label = self._col_labels[table.id][key]
                table.columns[key].label = Text(f"{label}  ")
            table.columns[column_key].label = Text(f"{base}{' ▼' if reverse else ' ▲'}")
            self._sort_state[table.id] = (column_key, reverse)

        def _clear_sort(self, table) -> None:
            for key in table.columns:
                table.columns[key].label = Text(f"{self._col_labels[table.id][key]}  ")
            self._sort_state.pop(table.id, None)

        def _reapply_sort(self, table) -> None:
            state = self._sort_state.get(table.id)
            if state is None:
                return
            column_key, reverse = state
            if column_key in table.columns:
                self._apply_sort(table, column_key, reverse)

        def _populate_tables(self) -> None:
            self._analysis_map = {item.benchmark: item for item in self._session.analyses}
            self._populate_runs_table()
            self._populate_benchmark_table()
            self._populate_cost_table()
            self._populate_failure_table()

        def _populate_runs_table(self) -> None:
            table = self.query_one("#runs-table", DataTable)
            self._register_columns(
                table,
                "Benchmark",
                "Category",
                "Mode",
                "Loop",
                "Requested VF",
                "Selected VF",
                "Selected Plan",
                "Selected Cost",
                "Kernel Cycles",
                "Total Cycles",
                "Wall Time (s)",
                "Delta",
                "Speedup",
                "Status",
            )
            self._all_run_rows = []
            self._run_map = {}
            for index, run in enumerate(self._session.runs):
                key = f"run:{index}"
                self._run_map[key] = run
                row = (
                    run.benchmark,
                    run.category,
                    run.mode,
                    str(run.loop_index) if run.loop_index is not None else "-",
                    run.requested_vf or "-",
                    run.selected_vf or "-",
                    str(run.selected_plan) if run.selected_plan is not None else "-",
                    str(run.selected_cost) if run.selected_cost is not None else "-",
                    f"{run.kernel_cycles:,}" if run.kernel_cycles is not None else "-",
                    f"{run.total_cycles:,}" if run.total_cycles is not None else "-",
                    f"{run.wall_time_s:.2f}",
                    str(run.delta_vs_default) if run.delta_vs_default is not None else "-",
                    f"{run.speedup_vs_default:.3f}" if run.speedup_vs_default is not None else "-",
                    run.status,
                )
                self._all_run_rows.append(row)
                table.add_row(*row, key=key)
            self._reapply_sort(table)
            if self._run_map:
                first_key = next(iter(self._run_map))
                self.query_one("#runs-detail", DetailPanel).show_text(build_run_detail(self._run_map[first_key]))

        def _populate_benchmark_table(self) -> None:
            table = self.query_one("#bench-table", DataTable)
            self._register_columns(
                table,
                "Benchmark",
                "Category",
                "Loops",
                "Unique VFs",
                "Default Cycles",
                "Best Cost VF",
                "Best Cost",
                "Best Latency VF",
                "Best Latency",
                "Mismatch",
            )
            self._all_bench_rows = []
            for row_data in compute_benchmark_rows(self._session.analyses, self._session.runs):
                row = (
                    row_data.benchmark,
                    row_data.category,
                    str(row_data.loop_count),
                    str(row_data.vf_count),
                    f"{row_data.default_cycles:,}" if row_data.default_cycles is not None else "-",
                    row_data.best_cost_vf or "-",
                    str(row_data.best_cost) if row_data.best_cost is not None else "-",
                    row_data.best_latency_vf or "-",
                    f"{row_data.best_latency_cycles:,}" if row_data.best_latency_cycles is not None else "-",
                    "yes" if row_data.mismatch else "no",
                )
                self._all_bench_rows.append(row)
                table.add_row(*row, key=row_data.benchmark)
            self._reapply_sort(table)
            if self._analysis_map:
                first_key = next(iter(self._analysis_map))
                self.query_one("#bench-detail", DetailPanel).show_text(build_analysis_detail(self._analysis_map[first_key]))

        def _populate_cost_table(self) -> None:
            table = self.query_one("#cost-table", DataTable)
            self._register_columns(
                table,
                "Benchmark",
                "Category",
                "Loop",
                "Best Cost VF",
                "Best Cost",
                "Best Latency VF",
                "Best Latency",
                "Candidates",
                "Match",
            )
            self._all_cost_rows = []
            self._cost_map = {}
            rows = compute_cost_latency_rows(self._session.analyses, self._session.runs)
            for row_data in rows:
                key = f"cost:{row_data.benchmark}:{row_data.loop_index}"
                self._cost_map[key] = (row_data.benchmark, row_data.loop_index)
                row = (
                    row_data.benchmark,
                    row_data.category,
                    str(row_data.loop_index),
                    row_data.best_cost_vf or "-",
                    str(row_data.best_cost) if row_data.best_cost is not None else "-",
                    row_data.best_latency_vf or "-",
                    f"{row_data.best_latency_cycles:,}" if row_data.best_latency_cycles is not None else "-",
                    str(row_data.candidate_count),
                    "yes" if row_data.matches else "no",
                )
                self._all_cost_rows.append(row)
                table.add_row(*row, key=key)
            self._reapply_sort(table)
            if self._cost_map:
                first_key = next(iter(self._cost_map))
                bench, loop = self._cost_map[first_key]
                self.query_one("#cost-detail", DetailPanel).show_text(self._build_cost_detail(bench, loop))

        def _populate_failure_table(self) -> None:
            table = self.query_one("#fail-table", DataTable)
            self._register_columns(
                table,
                "Type",
                "Benchmark",
                "Loop",
                "Requested VF",
                "Status",
                "Message",
            )
            self._all_fail_rows = []
            for analysis in self._session.analyses:
                if analysis.error:
                    row = ("analysis", analysis.benchmark, "-", "-", "ERR", analysis.error[:80])
                    key = f"fail:analysis:{analysis.benchmark}"
                    self._all_fail_rows.append(row)
                    table.add_row(*row, key=key)
            for index, run in enumerate(self._session.runs):
                if run.status in {"OK", "PASS"} and not run.error:
                    continue
                message = run.error or run.message or run.status
                row = (
                    "run",
                    run.benchmark,
                    str(run.loop_index) if run.loop_index is not None else "-",
                    run.requested_vf or "-",
                    run.status,
                    message[:80],
                )
                key = f"fail:run:{index}"
                self._all_fail_rows.append(row)
                table.add_row(*row, key=key)
            self._reapply_sort(table)
            if self._all_fail_rows:
                first_key = next(iter(table.rows))
                self._show_failure_detail(str(first_key))

        def _build_cost_detail(self, benchmark: str, loop_index: int) -> str:
            runs = [
                run for run in self._session.runs
                if run.mode == "forced" and run.benchmark == benchmark and run.loop_index == loop_index
            ]
            analysis = self._analysis_map.get(benchmark)
            lines = [f"Benchmark: {benchmark}", f"Loop: {loop_index}"]
            if analysis:
                lines.append(f"Category: {analysis.category}")
            if not runs:
                lines.append("No forced runs.")
                return "\n".join(lines)
            runs = sorted(
                runs,
                key=lambda item: (
                    item.selected_cost if item.selected_cost is not None else float("inf"),
                    item.kernel_cycles if item.kernel_cycles is not None else float("inf"),
                ),
            )
            lines.extend(["", "VF | Cost | Cycles | Status"])
            for run in runs:
                lines.append(
                    f"{run.selected_vf or run.requested_vf or '-'} | "
                    f"{run.selected_cost if run.selected_cost is not None else '-'} | "
                    f"{run.kernel_cycles if run.kernel_cycles is not None else '-'} | "
                    f"{run.status}"
                )
            return "\n".join(lines)

        def _show_failure_detail(self, key: str) -> None:
            if key.startswith("fail:analysis:"):
                benchmark = key.split(":", 2)[2]
                analysis = self._analysis_map.get(benchmark)
                if analysis:
                    self.query_one("#fail-detail", DetailPanel).show_text(build_analysis_detail(analysis))
                return
            if key.startswith("fail:run:"):
                run_index = int(key.rsplit(":", 1)[1])
                if 0 <= run_index < len(self._session.runs):
                    self.query_one("#fail-detail", DetailPanel).show_text(build_run_detail(self._session.runs[run_index]))

        def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
            table = event.data_table
            row_key = str(event.row_key.value)
            if table.id == "runs-table":
                run = self._run_map.get(row_key)
                if run is not None:
                    self.query_one("#runs-detail", DetailPanel).show_text(build_run_detail(run))
            elif table.id == "bench-table":
                analysis = self._analysis_map.get(row_key)
                if analysis is not None:
                    self.query_one("#bench-detail", DetailPanel).show_text(build_analysis_detail(analysis))
            elif table.id == "cost-table":
                info = self._cost_map.get(row_key)
                if info is not None:
                    benchmark, loop_index = info
                    self.query_one("#cost-detail", DetailPanel).show_text(
                        self._build_cost_detail(benchmark, loop_index)
                    )
            elif table.id == "fail-table":
                self._show_failure_detail(row_key)

        def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
            table = event.data_table
            if table.id not in self._col_labels:
                return
            previous = self._sort_state.get(table.id)
            column_key = event.column_key
            if previous and previous[0] == column_key:
                if not previous[1]:
                    self._apply_sort(table, column_key, reverse=True)
                else:
                    self._clear_sort(table)
            else:
                self._apply_sort(table, column_key, reverse=False)

        def _active_table(self):
            focused = self.focused
            if isinstance(focused, DataTable):
                return focused
            try:
                tabs = self.query_one(TabbedContent)
                pane = self.query_one(f"#{tabs.active}", TabPane)
                return pane.query_one(DataTable)
            except Exception:
                return None

        def action_cycle_sort(self) -> None:
            table = self._active_table()
            if table is None or table.id not in self._col_labels:
                return
            column_keys = [column.key for column in table.ordered_columns]
            previous = self._sort_state.get(table.id)
            if previous is None:
                self._apply_sort(table, column_keys[0], reverse=False)
                return
            current_index = next((idx for idx, key in enumerate(column_keys) if key is previous[0]), 0)
            if not previous[1]:
                self._apply_sort(table, column_keys[current_index], reverse=True)
            elif current_index + 1 < len(column_keys):
                self._apply_sort(table, column_keys[current_index + 1], reverse=False)
            else:
                self._clear_sort(table)

        def action_switch_tab(self, tab_id: str) -> None:
            try:
                self.query_one(TabbedContent).active = tab_id
            except Exception:
                return
            self._focus_active_table()

        def on_tabbed_content_tab_activated(self, event) -> None:
            self._focus_active_table()

        def _focus_active_table(self) -> None:
            def _do_focus() -> None:
                try:
                    tabs = self.query_one(TabbedContent)
                    pane = self.query_one(f"#{tabs.active}", TabPane)
                    pane.query_one(DataTable).focus()
                except Exception:
                    pass
            self.set_timer(0.05, _do_focus)

        def progress_advance(self, message: str, completed: int | None = None,
                             total: int | None = None, phase: str | None = None) -> None:
            if self._progress_screen is not None:
                self._progress_screen.advance(message, completed=completed, total=total, phase=phase)

        def progress_set_total(self, total: int) -> None:
            if self._progress_screen is not None:
                self._progress_screen.set_total(total)

        @property
        def progress_screen(self) -> ProgressScreen | None:
            return self._progress_screen

        def set_session(self, session: SessionData) -> None:
            self._session = session
            self.refresh(recompose=True)

    return VFPerformanceApp, ProgressScreen


def build_app():
    """Return the deferred Textual app class and progress screen type."""
    return _build_app_class()
