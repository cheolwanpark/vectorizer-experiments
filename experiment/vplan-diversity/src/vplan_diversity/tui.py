"""Textual TUI application and widgets."""

from __future__ import annotations

from .analytics import (
    _classify_vf,
    compute_category_stats,
    compute_dashboard_stats,
    compute_vf_distribution,
)
from .models import AnalysisEntry, AppRuntimeConfig, BenchResult, FunctionAnalysisReport
from .pipeline import analyze_function_vplans


def _build_app_class():
    """Build and return the TUI App class (deferred import of textual)."""
    import threading

    from rich.text import Text
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.widgets import (
        Button, DataTable, Footer, Header, Input, Label, ProgressBar,
        Static, TabbedContent, TabPane,
    )

    _NUMERIC_COLUMNS = {
        "#Loops", "#Plans", "Min Cost", "#Funcs", "Avg Plans/Loop",
        "Fixed VFs", "Scalable VFs", "Failed", "Occurrences",
        "Selections", "Max Cost",
    }

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

    class AnalysisDetailPanel(Static):
        def show_placeholder(self, message: str):
            self.update(message)

        def show_entry(self, entry: AnalysisEntry):
            lines = [
                f"[bold]Loop[{entry.loop_index}] Plan {entry.plan_index}[/bold]",
                f"Forced VF: {entry.forced_vf}",
                f"All VFs: {', '.join(entry.all_vfs)}",
                f"Costs: {entry.cost_summary}",
                f"Status: {entry.status}",
            ]
            if entry.selected_vf is not None or entry.selected_plan is not None:
                lines.append(
                    f"Selected: VF={entry.selected_vf or '-'} plan="
                    f"{entry.selected_plan if entry.selected_plan is not None else '-'}"
                )
            if entry.message:
                lines.append(f"[yellow]Note: {entry.message}[/yellow]")
            lines.extend([
                "",
                "[dim]--- Command ---[/dim]",
                entry.command,
                f"Log: {entry.log_path}",
                "",
                "[dim]--- Selected VPlan Dump ---[/dim]",
                entry.dump_text if entry.dump_text else "(no dump captured)",
            ])
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
        #analysis-controls {
            height: auto;
            margin: 0 0 1 0;
        }
        #analysis-func {
            width: 1fr;
        }
        #analysis-status {
            margin: 0 0 1 0;
        }
        #analysis-main {
            height: 1fr;
        }
        #analysis-table {
            width: 48;
            min-width: 48;
        }
        AnalysisDetailPanel {
            height: 1fr;
            overflow-y: auto;
            border: solid $accent;
            padding: 0 1;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("d", "switch_tab('dashboard')", "Dashboard"),
            Binding("b", "switch_tab('benchmarks')", "Benchmarks"),
            Binding("a", "switch_tab('analysis')", "Analysis"),
            Binding("c", "switch_tab('categories')", "Categories"),
            Binding("v", "switch_tab('vf-dist')", "VF Dist"),
            Binding("f", "switch_tab('failed-logs')", "Failed Logs"),
            Binding("r", "rerun", "Re-run"),
            Binding("s", "cycle_sort", "Sort"),
            Binding("y", "yank_analysis_report", "Copy Analysis"),
        ]

        def __init__(self, results: list[BenchResult] | None = None,
                     runner_args: dict | None = None,
                     runtime_config: AppRuntimeConfig | None = None,
                     **kwargs):
            super().__init__(**kwargs)
            self._results: list[BenchResult] = results or []
            self._runner_args = runner_args or {}
            self._runtime_config = runtime_config
            self._all_bench_rows: list[tuple] = []
            self._all_failed_rows: list[tuple] = []
            self._progress_screen: ProgressScreen | None = None
            self._sort_state: dict = {}
            self._col_labels: dict = {}
            self._analysis_entries: dict[str, AnalysisEntry] = {}
            self._analysis_report: FunctionAnalysisReport | None = None
            self._analysis_running = False

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
                    with Vertical():
                        yield Input(placeholder="Filter benchmarks\u2026", id="bench-filter")
                        yield DataTable(id="bench-table")
                        yield DetailPanel(id="detail-panel")

                with TabPane("Analysis", id="analysis"):
                    with Vertical():
                        with Horizontal(id="analysis-controls"):
                            yield Input(
                                placeholder="Function name (e.g. s000)",
                                id="analysis-func",
                            )
                            yield Button("Analyze", id="analysis-run", variant="primary")
                            yield Button("Copy Markdown", id="analysis-copy", disabled=True)
                        yield Label(
                            "Enter a benchmark function name and run analysis.",
                            id="analysis-status",
                        )
                        with Horizontal(id="analysis-main"):
                            yield DataTable(id="analysis-table")
                            yield AnalysisDetailPanel(id="analysis-detail")

                with TabPane("Categories", id="categories"):
                    yield DataTable(id="cat-table")

                with TabPane("VF Distribution", id="vf-dist"):
                    with VerticalScroll():
                        yield Label("[bold]Fixed VFs[/bold]")
                        yield DataTable(id="fixed-vf-table")
                        yield Label("\n[bold]Scalable VFs[/bold]")
                        yield DataTable(id="scalable-vf-table")

                with TabPane("Failed Logs", id="failed-logs"):
                    from textual.containers import Vertical as V2
                    with V2():
                        yield DataTable(id="failed-table")
                        yield DetailPanel(id="failed-detail-panel")

        def on_mount(self) -> None:
            self.title = "VPlan Diversity"
            self.sub_title = self._runner_args.get("subtitle", "")
            if self._results:
                self._populate_tables()
                self._set_analysis_status("Enter a benchmark function name and run analysis.")

        def _register_columns(self, table, *labels):
            padded = [f"{l}  " for l in labels]
            keys = table.add_columns(*padded)
            self._col_labels[table.id] = dict(zip(keys, labels))

        def _make_sort_key(self, label):
            if label in _NUMERIC_COLUMNS:
                def _num(val):
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return float("inf")
                return _num
            return lambda val: str(val).lower()

        def _apply_sort(self, table, col_key, reverse):
            tid = table.id
            orig = self._col_labels[tid][col_key]
            table.sort(col_key, key=self._make_sort_key(orig), reverse=reverse)
            for ck in table.columns:
                base = self._col_labels[tid][ck]
                table.columns[ck].label = Text(f"{base}  ")
            indicator = " \u25bc" if reverse else " \u25b2"
            table.columns[col_key].label = Text(f"{orig}{indicator}")
            self._sort_state[tid] = (col_key, reverse)

        def _clear_sort(self, table):
            tid = table.id
            for ck in table.columns:
                base = self._col_labels[tid][ck]
                table.columns[ck].label = Text(f"{base}  ")
            self._sort_state.pop(tid, None)

        def _reapply_sort(self, table):
            tid = table.id
            prev = self._sort_state.get(tid)
            if prev is None:
                return
            col_key, reverse = prev
            if col_key in table.columns:
                orig = self._col_labels[tid][col_key]
                table.sort(col_key, key=self._make_sort_key(orig), reverse=reverse)

        def _populate_tables(self) -> None:
            try:
                bt = self.query_one("#bench-table", DataTable)
            except Exception:
                return
            self._register_columns(
                bt,
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
            self._register_columns(
                ct,
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
                self._register_columns(
                    t, "VF", "Occurrences", "Selections", "Min Cost", "Max Cost",
                )

            for e in vf_dist:
                min_c = str(e.min_cost) if e.min_cost is not None else "-"
                max_c = str(e.max_cost) if e.max_cost is not None else "-"
                row = (e.vf, str(e.occurrences), str(e.selections), min_c, max_c)
                if _classify_vf(e.vf) == "scalable":
                    scalable_t.add_row(*row)
                else:
                    fixed_t.add_row(*row)

            # Failed logs table
            try:
                ft = self.query_one("#failed-table", DataTable)
            except Exception:
                return
            self._register_columns(ft, "Benchmark", "Category", "Error")
            self._all_failed_rows = []
            for r in sorted(self._results, key=lambda x: x.func_name):
                if not r.error:
                    continue
                err_short = (r.error[:80] + "\u2026") if len(r.error) > 80 else r.error
                row = (r.func_name, r.category, err_short)
                self._all_failed_rows.append(row)
                ft.add_row(*row, key=r.func_name)

            at = self.query_one("#analysis-table", DataTable)
            self._register_columns(
                at,
                "Loop", "Plan", "Forced VF", "All VFs", "Costs", "Status",
            )
            detail = self.query_one("#analysis-detail", AnalysisDetailPanel)
            detail.show_placeholder("No analysis loaded.")

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
            self._reapply_sort(bt)

        def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
            table = event.data_table
            row_key = event.row_key
            if table.id in ("bench-table", "failed-table"):
                func_name = str(row_key.value)
                result = next((r for r in self._results if r.func_name == func_name), None)
                if result:
                    panel_id = (
                        "#detail-panel" if table.id == "bench-table"
                        else "#failed-detail-panel"
                    )
                    try:
                        dp = self.query_one(panel_id, DetailPanel)
                        dp.show_result(result)
                    except Exception:
                        pass
                return

            if table.id == "analysis-table":
                entry = self._analysis_entries.get(str(row_key.value))
                if entry:
                    try:
                        panel = self.query_one("#analysis-detail", AnalysisDetailPanel)
                        panel.show_entry(entry)
                    except Exception:
                        pass

        def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
            table = event.data_table
            tid = table.id
            if tid not in self._col_labels:
                return
            col_key = event.column_key
            prev = self._sort_state.get(tid)
            if prev and prev[0] is col_key:
                if not prev[1]:
                    self._apply_sort(table, col_key, reverse=True)
                else:
                    self._clear_sort(table)
            else:
                self._apply_sort(table, col_key, reverse=False)

        def _active_table(self):
            focused = self.focused
            if isinstance(focused, DataTable):
                return focused
            try:
                tc = self.query_one(TabbedContent)
                pane = self.query_one(f"#{tc.active}", TabPane)
                return pane.query_one(DataTable)
            except Exception:
                return None

        def action_cycle_sort(self) -> None:
            table = self._active_table()
            if table is None or table.id not in self._col_labels:
                return
            col_keys = [c.key for c in table.ordered_columns]
            prev = self._sort_state.get(table.id)
            if prev is None:
                self._apply_sort(table, col_keys[0], reverse=False)
            else:
                cur_idx = next(
                    (i for i, ck in enumerate(col_keys) if ck is prev[0]),
                    0,
                )
                if not prev[1]:
                    self._apply_sort(table, col_keys[cur_idx], reverse=True)
                elif cur_idx + 1 < len(col_keys):
                    self._apply_sort(table, col_keys[cur_idx + 1], reverse=False)
                else:
                    self._clear_sort(table)

        def action_switch_tab(self, tab_id: str) -> None:
            try:
                tc = self.query_one(TabbedContent)
                tc.active = tab_id
            except Exception:
                pass
            self._focus_active_table()

        def on_tabbed_content_tab_activated(self, event) -> None:
            self._focus_active_table()

        def _focus_active_table(self) -> None:
            def _do_focus():
                try:
                    tc = self.query_one(TabbedContent)
                    if tc.active == "analysis":
                        self.query_one("#analysis-func", Input).focus()
                        return
                    pane = self.query_one(f"#{tc.active}", TabPane)
                    dt = pane.query_one(DataTable)
                    dt.focus()
                except Exception:
                    pass
            self.set_timer(0.1, _do_focus)

        async def action_rerun(self) -> None:
            self.notify("Re-run not yet implemented in TUI mode. Restart the tool.")

        def action_yank_analysis_report(self) -> None:
            if not self._analysis_report:
                self.notify("No analysis report to copy.")
                return
            try:
                self.copy_to_clipboard(self._analysis_report.markdown_report)
                self.notify(f"Copied analysis report for {self._analysis_report.func_name}.")
            except Exception as exc:
                self.notify(f"Clipboard copy failed: {exc}")

        def _set_analysis_status(self, message: str) -> None:
            try:
                self.query_one("#analysis-status", Label).update(message)
            except Exception:
                pass

        def _set_analysis_controls_enabled(self, enabled: bool) -> None:
            try:
                self.query_one("#analysis-func", Input).disabled = not enabled
                self.query_one("#analysis-run", Button).disabled = not enabled
                self.query_one("#analysis-copy", Button).disabled = (
                    not enabled or self._analysis_report is None
                )
            except Exception:
                pass

        def _reset_analysis_view(self) -> None:
            self._analysis_entries = {}
            self._analysis_report = None
            try:
                table = self.query_one("#analysis-table", DataTable)
                table.clear()
            except Exception:
                pass
            try:
                panel = self.query_one("#analysis-detail", AnalysisDetailPanel)
                panel.show_placeholder("Analysis is running...")
            except Exception:
                pass
            self._set_analysis_controls_enabled(False)

        def _add_analysis_row(self, entry: AnalysisEntry) -> None:
            row_key = f"{entry.loop_index}:{entry.plan_index}"
            self._analysis_entries[row_key] = entry
            try:
                table = self.query_one("#analysis-table", DataTable)
                status = {
                    "ok": "OK",
                    "warning": "WARN",
                    "error": "ERR",
                }.get(entry.status, entry.status.upper())
                table.add_row(
                    str(entry.loop_index),
                    str(entry.plan_index),
                    entry.forced_vf,
                    ", ".join(entry.all_vfs),
                    entry.cost_summary,
                    status,
                    key=row_key,
                )
                if len(self._analysis_entries) == 1:
                    panel = self.query_one("#analysis-detail", AnalysisDetailPanel)
                    panel.show_entry(entry)
            except Exception:
                pass

        def _analysis_progress(self, func_name: str, completed: int, total: int,
                               entry: AnalysisEntry) -> None:
            self._set_analysis_status(
                f"Analyzing {func_name}: {completed}/{total} plans complete"
            )
            self._add_analysis_row(entry)

        def _finish_analysis(self, report: FunctionAnalysisReport | None,
                             error: str | None) -> None:
            self._analysis_running = False
            if error:
                self._set_analysis_status(f"Analysis failed: {error}")
                try:
                    panel = self.query_one("#analysis-detail", AnalysisDetailPanel)
                    panel.show_placeholder(f"Analysis failed.\n\n{error}")
                except Exception:
                    pass
                self._set_analysis_controls_enabled(True)
                return

            self._analysis_report = report
            self._set_analysis_status(
                f"Loaded analysis for {report.func_name}: {len(report.entries)} plan dumps"
            )
            self._set_analysis_controls_enabled(True)

        def _run_analysis_thread(self, func_name: str) -> None:
            try:
                if self._runtime_config is None:
                    raise RuntimeError("runtime config is missing")
                result = next((r for r in self._results if r.func_name == func_name), None)
                if result is None:
                    raise RuntimeError(f"unknown function: {func_name}")
                report = analyze_function_vplans(
                    result,
                    self._runtime_config,
                    on_progress=lambda completed, total, entry: self.call_from_thread(
                        self._analysis_progress,
                        func_name,
                        completed,
                        total,
                        entry,
                    ),
                )
                self.call_from_thread(self._finish_analysis, report, None)
            except Exception as exc:
                self.call_from_thread(self._finish_analysis, None, str(exc))

        def _start_analysis(self) -> None:
            if self._analysis_running:
                self.notify("Analysis is already running.")
                return

            try:
                func_name = self.query_one("#analysis-func", Input).value.strip()
            except Exception:
                func_name = ""
            if not func_name:
                self.notify("Enter a function name like s000.")
                return

            self._analysis_running = True
            self._reset_analysis_view()
            self._set_analysis_status(f"Starting analysis for {func_name}...")
            worker = threading.Thread(
                target=self._run_analysis_thread,
                args=(func_name,),
                daemon=True,
            )
            worker.start()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "analysis-run":
                self._start_analysis()
            elif event.button.id == "analysis-copy":
                self.action_yank_analysis_report()

        def on_input_submitted(self, event: Input.Submitted) -> None:
            if event.input.id == "analysis-func":
                self._start_analysis()

        def set_results(self, results: list[BenchResult]) -> None:
            """Called after pipeline completes to switch from progress to dashboard."""
            self._results = results
            self.refresh()

    return VPlanDiversityApp, ProgressScreen
