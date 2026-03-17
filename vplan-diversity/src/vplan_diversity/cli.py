"""CLI entry point and orchestration."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from .analytics import load_cache, save_cache
from .models import AppRuntimeConfig, BenchResult, bench_to_dict
from .pipeline import (
    PipelineRunner,
    _find_tsvc_dir,
    discover_benchmarks,
    resolve_llvm_tools,
)
from .tui import _build_app_class


def _make_runtime_config(args, tsvc_dir, tools) -> AppRuntimeConfig:
    return AppRuntimeConfig(
        variant=args.type,
        vlen=args.vlen,
        llvm_custom=args.llvm_custom,
        tsvc_dir=str(tsvc_dir),
        tools=tools,
    )


async def run_pipeline(args) -> list[BenchResult]:
    """Run the full pipeline and return results."""
    tsvc_dir = _find_tsvc_dir()
    calls, helper_mod = discover_benchmarks(tsvc_dir)
    tools = resolve_llvm_tools(args.llvm_custom)
    func_names = sorted(calls.keys())

    print(f"Found {len(func_names)} benchmarks in {tsvc_dir}", file=sys.stderr)
    print(f"Tools: clang={tools['clang']}, opt={tools['opt']}", file=sys.stderr)
    print(f"Config: type={args.type}, vlen={args.vlen}", file=sys.stderr)

    parallelism = min(os.cpu_count() or 4, 8)
    if args.jobs:
        parallelism = args.jobs

    completed = 0

    def on_progress(result: BenchResult):
        nonlocal completed
        completed += 1
        status = "OK" if not result.error else f"ERR: {result.error[:60]}"
        print(f"  [{completed}/{len(func_names)}] {result.func_name}: {status}",
              file=sys.stderr)

    runner = PipelineRunner(
        tools=tools, tsvc_dir=tsvc_dir, calls=calls, helper_mod=helper_mod,
        variant=args.type, vlen=args.vlen, parallelism=parallelism,
        on_progress=on_progress,
    )

    try:
        results = await runner.run_all(func_names)
    finally:
        runner.cleanup()

    return results


async def run_pipeline_with_tui(args):
    """Run the pipeline with a live TUI progress screen, then show dashboard."""
    tsvc_dir = _find_tsvc_dir()
    calls, helper_mod = discover_benchmarks(tsvc_dir)
    tools = resolve_llvm_tools(args.llvm_custom)
    func_names = sorted(calls.keys())

    parallelism = min(os.cpu_count() or 4, 8)
    if args.jobs:
        parallelism = args.jobs

    AppClass, ProgressScreenClass = _build_app_class()

    results: list[BenchResult] = []
    completed_count = 0

    app = AppClass(
        results=None,
        runner_args={
            "total": len(func_names),
            "subtitle": f"type={args.type} vlen={args.vlen}",
        },
        runtime_config=_make_runtime_config(args, tsvc_dir, tools),
    )

    async def do_pipeline():
        nonlocal results
        runner = PipelineRunner(
            tools=tools, tsvc_dir=tsvc_dir, calls=calls, helper_mod=helper_mod,
            variant=args.type, vlen=args.vlen, parallelism=parallelism,
            on_progress=lambda r: _tui_progress(app, r),
        )
        try:
            results = await runner.run_all(func_names)
        finally:
            runner.cleanup()

        save_cache(results, args.type, args.vlen, tools)
        app.exit()

    def _tui_progress(the_app, result: BenchResult):
        nonlocal completed_count
        completed_count += 1
        if the_app._progress_screen:
            the_app.call_from_thread(
                the_app._progress_screen.advance,
                result.func_name, result.error,
            )

    import threading

    def _run_pipeline_thread():
        loop = asyncio.new_event_loop()
        loop.run_until_complete(do_pipeline())

    t = threading.Thread(target=_run_pipeline_thread, daemon=True)
    t.start()
    await app.run_async()
    t.join(timeout=5)

    if results:
        dashboard_app = AppClass(
            results=results,
            runner_args={
                "subtitle": f"type={args.type} vlen={args.vlen} | {len(results)} benchmarks",
            },
            runtime_config=_make_runtime_config(args, tsvc_dir, tools),
        )
        await dashboard_app.run_async()


def main():
    parser = argparse.ArgumentParser(
        description="VPlan Diversity Diagnostic Tool \u2014 analyze vectorizer plan diversity across TSVC benchmarks",
    )
    parser.add_argument("--type", choices=["dbl", "flt"], default="dbl",
                        help="TSVC type variant (default: dbl)")
    parser.add_argument("--vlen", type=int, default=128,
                        help="RVV VLEN in bits (default: 128)")
    parser.add_argument("--llvm-custom", default=None,
                        help="Path to LLVM build dir (falls back to $LLVM_CUSTOM)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Skip loading cached results")
    parser.add_argument("--json-output", action="store_true",
                        help="Dump JSON results to stdout instead of TUI")
    parser.add_argument("-j", "--jobs", type=int, default=None,
                        help="Max parallel pipelines (default: min(cpus, 8))")

    args = parser.parse_args()

    results: list[BenchResult] | None = None
    if not args.no_cache:
        results = load_cache(args.type, args.vlen)
        if results:
            print(f"Loaded {len(results)} cached results", file=sys.stderr)

    if args.json_output:
        if not results:
            results = asyncio.run(run_pipeline(args))
            tools = resolve_llvm_tools(args.llvm_custom)
            save_cache(results, args.type, args.vlen, tools)
        json.dump([bench_to_dict(r) for r in results], sys.stdout, indent=2)
        print()
        return

    if results:
        tsvc_dir = _find_tsvc_dir()
        tools = resolve_llvm_tools(args.llvm_custom)
        AppClass, _ = _build_app_class()
        app = AppClass(
            results=results,
            runner_args={
                "subtitle": f"type={args.type} vlen={args.vlen} | {len(results)} benchmarks",
            },
            runtime_config=_make_runtime_config(args, tsvc_dir, tools),
        )
        app.run()
    else:
        asyncio.run(run_pipeline_with_tui(args))


if __name__ == "__main__":
    main()
