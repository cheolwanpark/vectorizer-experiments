"""Cache and export helpers."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import (
    AppRuntimeConfig,
    BenchmarkAnalysis,
    RunResult,
    SessionData,
    analysis_from_dict,
    run_from_dict,
    to_dict,
)

CACHE_SCHEMA_VERSION = "v3"


def ensure_cache_dirs(cache_root: Path) -> None:
    for name in ("analysis", "runs", "artifacts", "logs", "gem5-out"):
        (cache_root / name).mkdir(parents=True, exist_ok=True)


def cache_root_from_runtime(runtime: AppRuntimeConfig) -> Path:
    root = Path(runtime.cache_dir)
    ensure_cache_dirs(root)
    return root


def tool_version(tool_path: str, version_arg: str = "--version") -> str:
    try:
        result = subprocess.run(
            [tool_path, version_arg],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return "unknown"

    output = result.stdout or result.stderr
    for line in output.splitlines():
        line = line.strip()
        if line:
            return line
    return "unknown"


def analysis_cache_key(runtime: AppRuntimeConfig, benchmark: str, source_path: str) -> str:
    opt_version = runtime.tool_versions.get("opt") or tool_version(runtime.tools.get("opt", "opt"))
    payload = "|".join(
        [
            CACHE_SCHEMA_VERSION,
            runtime.executor,
            benchmark,
            source_path,
            str(runtime.len_1d),
            runtime.guest_workspace or "",
            runtime.tools.get("clang", "clang"),
            runtime.tools.get("opt", "opt"),
            runtime.tools.get("sysroot", ""),
            runtime.tools.get("gem5", ""),
            opt_version,
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


def run_cache_key(
    runtime: AppRuntimeConfig,
    benchmark: str,
    source_path: str,
    loop_index: int | None,
    requested_vf: str | None,
    mode: str,
) -> str:
    clang_version = runtime.tool_versions.get("clang") or tool_version(runtime.tools.get("clang", "clang"))
    payload = "|".join(
        [
            CACHE_SCHEMA_VERSION,
            runtime.executor,
            benchmark,
            source_path,
            str(loop_index),
            str(requested_vf),
            mode,
            str(runtime.len_1d),
            runtime.guest_workspace or "",
            runtime.gem5_cpu_type,
            runtime.tools.get("clang", "clang"),
            runtime.tools.get("opt", "opt"),
            runtime.tools.get("sysroot", ""),
            runtime.tools.get("gem5", "gem5"),
            clang_version,
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def load_cached_analysis(cache_root: Path, key: str) -> BenchmarkAnalysis | None:
    path = cache_root / "analysis" / f"{key}.json"
    if not path.exists():
        return None
    try:
        return analysis_from_dict(json.loads(path.read_text()))
    except Exception:
        return None


def save_cached_analysis(cache_root: Path, key: str, analysis: BenchmarkAnalysis) -> Path:
    path = cache_root / "analysis" / f"{key}.json"
    path.write_text(json.dumps(to_dict(analysis), indent=2))
    return path


def load_cached_run(cache_root: Path, key: str) -> RunResult | None:
    path = cache_root / "runs" / f"{key}.json"
    if not path.exists():
        return None
    try:
        return run_from_dict(json.loads(path.read_text()))
    except Exception:
        return None


def save_cached_run(cache_root: Path, key: str, run_result: RunResult) -> Path:
    path = cache_root / "runs" / f"{key}.json"
    path.write_text(json.dumps(to_dict(run_result), indent=2))
    return path


def export_session_json(path: Path, runtime: AppRuntimeConfig, session: SessionData) -> None:
    payload = {
        "timestamp": datetime.now().isoformat(),
        "runtime": to_dict(runtime),
        "analyses": [to_dict(item) for item in session.analyses],
        "runs": [to_dict(item) for item in session.runs],
    }
    path.write_text(json.dumps(payload, indent=2))


def export_runs_csv(path: Path, runs: Iterable[RunResult]) -> None:
    rows = list(runs)
    fieldnames = [
        "benchmark",
        "category",
        "mode",
        "loop_index",
        "requested_vf",
        "selected_vf",
        "selected_plan",
        "selected_cost",
        "kernel_cycles",
        "total_cycles",
        "wall_time_s",
        "status",
        "delta_vs_default",
        "speedup_vs_default",
        "artifact_path",
        "log_path",
        "message",
        "error",
        "cache_hit",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: getattr(row, name) for name in fieldnames})
