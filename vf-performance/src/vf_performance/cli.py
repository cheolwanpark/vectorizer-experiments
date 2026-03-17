"""CLI entrypoint and TUI orchestration."""

from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path

from .models import SessionData, to_dict
from .pipeline import PipelineRunner, default_runtime_config, resolve_llvm_tools, resolve_rvv_root
from .storage import export_runs_csv, export_session_json
from .tui import build_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run TSVC_2 benchmarks across forced VFs and compare LLVM cost against gem5 latency",
    )
    parser.add_argument("--rvv-root", default=None, help="Path to rvv-poc-main")
    parser.add_argument(
        "--llvm-custom",
        default=None,
        help="Path to LLVM build/bin directory (falls back to $LLVM_CUSTOM)",
    )
    parser.add_argument("--len", type=int, default=32000, help="TSVC LEN_1D value")
    parser.add_argument("-j", "--jobs", type=int, default=None, help="Analysis parallelism")
    parser.add_argument("--sim-jobs", type=int, default=1, help="Simulation parallelism (reserved)")
    parser.add_argument("--bench", action="append", default=[], help="Benchmark name filter")
    parser.add_argument("--resume", action="store_true", help="Alias for cached execution")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cached analyses and runs")
    parser.add_argument("--csv-output", default=None, help="Export run rows to CSV")
    parser.add_argument("--json-output", default=None, help="Export full session JSON")
    parser.add_argument("--no-tui", action="store_true", help="Run in CLI mode only")
    return parser.parse_args()


def run_pipeline(runtime, on_progress=None) -> SessionData:
    runner = PipelineRunner(runtime, on_progress=on_progress)
    try:
        return runner.run()
    finally:
        runner.cleanup()


def main() -> None:
    args = parse_args()
    rvv_root = resolve_rvv_root(args.rvv_root)
    tools = resolve_llvm_tools(args.llvm_custom, rvv_root)
    runtime = default_runtime_config(args, rvv_root, tools)

    if args.no_tui:
        session = run_pipeline(runtime)
        _handle_exports(args, runtime, session)
        return

    AppClass, ProgressScreen = build_app()
    app = AppClass(
        session=None,
        subtitle=f"root={rvv_root.name} len={runtime.len_1d}",
    )
    session: SessionData | None = None

    def handle_progress(kind: str, payload: dict) -> None:
        if app.progress_screen is None:
            return
        if kind == "analysis_completed":
            analysis = payload["analysis"]
            app.call_from_thread(
                app.progress_screen.advance,
                f"analysis {payload['completed']}/{payload['total']}: {analysis.benchmark}",
            )
        elif kind == "run_completed":
            run = payload["run"]
            label = run.requested_vf or "default"
            app.call_from_thread(
                app.progress_screen.advance,
                f"run {payload['completed']}/{payload['total']}: {run.benchmark} {label}",
            )

    def worker() -> None:
        nonlocal session
        try:
            session = run_pipeline(runtime, on_progress=handle_progress)
            app.call_from_thread(app.set_session, session)
            app.call_from_thread(app.exit)
        except Exception as exc:
            app.call_from_thread(app.progress_screen.advance, f"error: {exc}")
            app.call_from_thread(app.exit)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    app.run()
    thread.join(timeout=5)

    if session is not None:
        _handle_exports(args, runtime, session)
        dashboard = AppClass(
            session=session,
            subtitle=f"{len(session.analyses)} benchmarks | {len(session.runs)} runs",
        )
        dashboard.run()


def _handle_exports(args: argparse.Namespace, runtime, session: SessionData) -> None:
    if args.csv_output:
        export_runs_csv(Path(args.csv_output), session.runs)
    if args.json_output:
        export_session_json(Path(args.json_output), runtime, session)
    if not args.csv_output and not args.json_output and args.no_tui:
        print(
            json.dumps(
                {
                    "analyses": [to_dict(item) for item in session.analyses],
                    "runs": [to_dict(item) for item in session.runs],
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
