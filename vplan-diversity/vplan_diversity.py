#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "textual>=1.0.0",
# ]
# ///
"""VPlan Diversity Diagnostic Tool.

Runs vplan-explain on all 136 TSVC benchmarks, collects VPlan diversity data,
and presents an interactive TUI dashboard.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent

# ─── Data Models ────────────────────────────────────────────────────────────


@dataclass
class VFCost:
    vf: str
    cost: int | None


@dataclass
class VPlan:
    index: int
    vfs: list[str]
    costs: list[VFCost]


@dataclass
class LoopInfo:
    index: int
    path: str
    plan_count: int
    plans: list[VPlan]
    selected_vf: str | None
    selected_plan: int | None


@dataclass
class BenchResult:
    func_name: str
    category: str
    loops: list[LoopInfo]
    error: str | None
    raw_output: str


# ─── Data model serialization ───────────────────────────────────────────────


def _bench_to_dict(b: BenchResult) -> dict:
    return asdict(b)


def _bench_from_dict(d: dict) -> BenchResult:
    loops = []
    for l in d.get("loops", []):
        plans = []
        for p in l.get("plans", []):
            costs = [VFCost(**c) for c in p.get("costs", [])]
            plans.append(VPlan(index=p["index"], vfs=p["vfs"], costs=costs))
        loops.append(LoopInfo(
            index=l["index"], path=l["path"], plan_count=l["plan_count"],
            plans=plans, selected_vf=l.get("selected_vf"),
            selected_plan=l.get("selected_plan"),
        ))
    return BenchResult(
        func_name=d["func_name"], category=d["category"],
        loops=loops, error=d.get("error"), raw_output=d.get("raw_output", ""),
    )


# ─── TSVC Source Acquisition ────────────────────────────────────────────────


def _find_tsvc_dir() -> Path:
    """Locate the TSVC benchmark directory."""
    local = SCRIPT_DIR / "TSVC"
    if local.exists() and (local / "tsc.inc").exists():
        return local.resolve()

    tmp = Path("/tmp/llvm-test-suite/MultiSource/Benchmarks/TSVC")
    if tmp.exists() and (tmp / "tsc.inc").exists():
        return tmp

    print("TSVC not found locally. Cloning llvm-test-suite (sparse)…", file=sys.stderr)
    repo = Path("/tmp/llvm-test-suite")
    subprocess.run(
        ["git", "clone", "--depth=1", "--filter=blob:none", "--sparse",
         "https://github.com/llvm/llvm-test-suite.git", str(repo)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "sparse-checkout", "set",
         "MultiSource/Benchmarks/TSVC"],
        check=True, capture_output=True,
    )
    if not (tmp / "tsc.inc").exists():
        print("Error: TSVC clone succeeded but tsc.inc not found.", file=sys.stderr)
        sys.exit(1)
    return tmp


# ─── Benchmark Discovery ───────────────────────────────────────────────────

CATEGORY_TO_DIR = {
    "CONTROL_FLOW": "ControlFlow",
    "CONTROL_LOOPS": "ControlLoops",
    "CROSSING_THRESHOLDS": "CrossingThresholds",
    "EQUIVALENCING": "Equivalencing",
    "EXPANSION": "Expansion",
    "GLOBAL_DATA_FLOW": "GlobalDataFlow",
    "INDIRECT_ADDRESSING": "IndirectAddressing",
    "INDUCTION_VARIABLE": "InductionVariable",
    "LINEAR_DEPENDENCE": "LinearDependence",
    "LOOP_RESTRUCTURING": "LoopRestructuring",
    "LOOP_REROLLING": "LoopRerolling",
    "NODE_SPLITTING": "NodeSplitting",
    "PACKING": "Packing",
    "RECURRENCES": "Recurrences",
    "REDUCTIONS": "Reductions",
    "SEARCHING": "Searching",
    "STATEMENT_REORDERING": "StatementReordering",
    "SYMBOLICS": "Symbolics",
}


def _parse_func_calls_inline(tsc_inc: Path) -> dict[str, dict[str, str]]:
    """Inline reimplementation of tsvc_make_helper.parse_func_calls()."""
    text = tsc_inc.read_text()
    main_pos = text.find("int main(")
    if main_pos == -1:
        raise RuntimeError(f"could not find main() in {tsc_inc}")

    calls: dict[str, dict[str, str]] = {}
    main_text = text[main_pos:]
    block_re = re.compile(r"#if TESTS & ([A-Z_]+)\n(.*?)#endif", re.S)
    call_re = re.compile(r"^\s*(s\d{3,4}\s*\(.*\);)\s*$")
    func_re = re.compile(r"^(s\d{3,4})\s*\(")

    for category, block in block_re.findall(main_text):
        for line in block.splitlines():
            m = call_re.match(line)
            if not m:
                continue
            call_expr = m.group(1).strip()
            fm = func_re.match(call_expr)
            if not fm:
                continue
            func = fm.group(1)
            if func in calls and calls[func]["category"] != category:
                raise RuntimeError(f"function {func} appears in multiple categories")
            calls[func] = {"category": category, "call_expr": call_expr}

    if not calls:
        raise RuntimeError(f"could not parse TSVC calls from {tsc_inc}")
    return calls


def _sanitize_ir_text_inline(text: str, triple: str | None, datalayout: str | None) -> str:
    """Inline reimplementation of tsvc_make_helper.sanitize_ir_text()."""
    if triple:
        text, count = re.subn(
            r'^target triple = "[^"]*"$',
            f'target triple = "{triple}"',
            text, count=1, flags=re.M,
        )
        if count == 0:
            raise RuntimeError("could not find target triple in IR")
    if datalayout:
        text, count = re.subn(
            r'^target datalayout = "[^"]*"$',
            f'target datalayout = "{datalayout}"',
            text, count=1, flags=re.M,
        )
        if count == 0:
            raise RuntimeError("could not find target datalayout in IR")
    text = re.sub(r'\s+"target-cpu"="[^"]*"', "", text)
    text = re.sub(r'\s+"target-features"="[^"]*"', "", text)
    return text


def discover_benchmarks(tsvc_dir: Path) -> tuple[dict[str, dict[str, str]], Any]:
    """Return (calls_dict, helper_module_or_None)."""
    helper_path = tsvc_dir / "tsvc_make_helper.py"
    if helper_path.exists():
        try:
            spec = importlib.util.spec_from_file_location("tsvc_make_helper", helper_path)
            mod = importlib.util.module_from_spec(spec)
            # Patch TSVC_DIR / TSC_INC so the module works from any location
            spec.loader.exec_module(mod)
            return mod.CALLS, mod
        except Exception:
            pass

    # Fallback: inline parse
    calls = _parse_func_calls_inline(tsvc_dir / "tsc.inc")
    return calls, None


def resolve_source_path(func: str, calls: dict, tsvc_dir: Path, variant: str) -> Path:
    category = calls[func]["category"]
    dir_name = CATEGORY_TO_DIR[category]
    return tsvc_dir / f"{dir_name}-{variant}" / "tsc.c"


# ─── LLVM Tool Resolution ──────────────────────────────────────────────────


def resolve_llvm_tools(llvm_custom: str | None) -> dict[str, str]:
    """Resolve paths to clang, opt, llvm-extract."""
    tools: dict[str, str] = {}
    if not llvm_custom:
        llvm_custom = os.environ.get("LLVM_CUSTOM")

    if llvm_custom:
        base = Path(llvm_custom).resolve()
        for tool in ("clang", "opt", "llvm-extract"):
            for candidate in (base / tool, base / "bin" / tool):
                if candidate.exists():
                    tools[tool] = str(candidate)
                    break
            if tool not in tools:
                print(f"Warning: {tool} not found in {base}", file=sys.stderr)
                tools[tool] = tool  # fall back to PATH
    else:
        for tool in ("clang", "opt", "llvm-extract"):
            found = shutil.which(tool)
            if found:
                tools[tool] = found
            else:
                tools[tool] = tool

    return tools


# ─── Output Parser ──────────────────────────────────────────────────────────

_LOOP_HEADER_RE = re.compile(r'^LV: Loop\[(\d+)\] path=(\w+) plans=(\d+)$', re.M)
_PLAN_HEADER_RE = re.compile(r'^LV:\s+VPlan\[(\d+)\] VFs=\{([^}]+)\}$', re.M)
_COST_LINE_RE = re.compile(r'^LV:\s+VF=(.+?) cost=(\d+)$', re.M)
_SELECTION_RE = re.compile(r'^LV:\s+selected VF=(.+?) plan=(\d+)$', re.M)


def parse_vplan_output(stderr_text: str) -> list[LoopInfo]:
    """Parse vplan-explain stderr output into LoopInfo list."""
    loops: list[LoopInfo] = []

    # Split into loop blocks
    loop_starts = list(_LOOP_HEADER_RE.finditer(stderr_text))
    if not loop_starts:
        return loops

    for i, lm in enumerate(loop_starts):
        start = lm.start()
        end = loop_starts[i + 1].start() if i + 1 < len(loop_starts) else len(stderr_text)
        block = stderr_text[start:end]

        loop_idx = int(lm.group(1))
        path = lm.group(2)
        plan_count = int(lm.group(3))

        # Parse plans within this loop block
        plan_matches = list(_PLAN_HEADER_RE.finditer(block))
        plans: list[VPlan] = []

        for j, pm in enumerate(plan_matches):
            pstart = pm.start()
            pend = plan_matches[j + 1].start() if j + 1 < len(plan_matches) else len(block)
            plan_block = block[pstart:pend]

            plan_idx = int(pm.group(1))
            vfs = [v.strip() for v in pm.group(2).split(",")]

            costs: list[VFCost] = []
            for cm in _COST_LINE_RE.finditer(plan_block):
                costs.append(VFCost(vf=cm.group(1), cost=int(cm.group(2))))

            # If no cost lines found, create VFCost entries with None
            if not costs:
                for vf in vfs:
                    costs.append(VFCost(vf=vf, cost=None))

            plans.append(VPlan(index=plan_idx, vfs=vfs, costs=costs))

        # Parse selection
        sel_match = _SELECTION_RE.search(block)
        selected_vf = sel_match.group(1) if sel_match else None
        selected_plan = int(sel_match.group(2)) if sel_match else None

        loops.append(LoopInfo(
            index=loop_idx, path=path, plan_count=plan_count,
            plans=plans, selected_vf=selected_vf, selected_plan=selected_plan,
        ))

    return loops


# ─── Pipeline Runner ────────────────────────────────────────────────────────

RVV_TRIPLE = "riscv64-unknown-unknown-elf"
RVV_DATALAYOUT = "e-m:e-p:64:64-i64:64-i128:128-n32:64-S128"
PREVEC_PASSES = "mem2reg,instcombine,simplifycfg,loop-simplify,lcssa,indvars,loop-rotate,instcombine,simplifycfg"


async def _run_cmd(cmd: list[str], cwd: str | None = None,
                   stdin_data: bytes | None = None) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd,
        stdin=asyncio.subprocess.PIPE if stdin_data else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=stdin_data)
    return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")


class PipelineRunner:
    def __init__(self, tools: dict[str, str], tsvc_dir: Path,
                 calls: dict, helper_mod: Any,
                 variant: str, vlen: int, parallelism: int,
                 on_progress=None):
        self.tools = tools
        self.tsvc_dir = tsvc_dir
        self.calls = calls
        self.helper_mod = helper_mod
        self.variant = variant
        self.vlen = vlen
        self.sem = asyncio.Semaphore(parallelism)
        self.on_progress = on_progress
        self.work_dir = Path(tempfile.mkdtemp(prefix="vplan-diversity-"))
        self._full_ll_cache: dict[str, Path] = {}
        self._full_ll_locks: dict[str, asyncio.Lock] = {}

    def _target_args(self) -> list[str]:
        return [
            f"-mtriple=riscv64-unknown-elf",
            f"-mcpu=generic-rv64",
            f"-mattr=+v",
            f"-riscv-v-vector-bits-min={self.vlen}",
            f"-riscv-v-vector-bits-max={self.vlen}",
        ]

    def _sanitize_ir(self, text: str) -> str:
        if self.helper_mod:
            return self.helper_mod.sanitize_ir_text(text, RVV_TRIPLE, RVV_DATALAYOUT)
        return _sanitize_ir_text_inline(text, RVV_TRIPLE, RVV_DATALAYOUT)

    async def _get_full_ll(self, source_path: Path) -> Path:
        """Compile source to full.ll, cached per source file."""
        key = str(source_path)
        if key not in self._full_ll_locks:
            self._full_ll_locks[key] = asyncio.Lock()

        async with self._full_ll_locks[key]:
            if key in self._full_ll_cache:
                return self._full_ll_cache[key]

            src_hash = hashlib.md5(str(source_path).encode()).hexdigest()[:8]
            out = self.work_dir / f"full_{src_hash}.ll"

            rc, stdout, stderr = await _run_cmd([
                self.tools["clang"],
                "-O0", "-Xclang", "-disable-O0-optnone",
                "-S", "-emit-llvm",
                str(source_path), "-o", str(out),
            ])
            if rc != 0:
                raise RuntimeError(f"clang failed for {source_path}: {stderr}")

            self._full_ll_cache[key] = out
            return out

    async def run_one(self, func_name: str) -> BenchResult:
        """Run the full pipeline for one benchmark function."""
        category = self.calls[func_name]["category"]
        async with self.sem:
            try:
                source_path = resolve_source_path(
                    func_name, self.calls, self.tsvc_dir, self.variant)

                # Step 1: clang (cached per source)
                full_ll = await self._get_full_ll(source_path)

                func_dir = self.work_dir / func_name
                func_dir.mkdir(exist_ok=True)
                func_ll = func_dir / f"{func_name}.ll"

                # Step 2: llvm-extract
                rc, stdout, stderr = await _run_cmd([
                    self.tools["llvm-extract"],
                    "-S", f"--func={func_name}",
                    str(full_ll), "-o", str(func_ll),
                ])
                if rc != 0:
                    raise RuntimeError(f"llvm-extract failed: {stderr}")

                # Step 3: Sanitize IR
                ir_text = func_ll.read_text()
                try:
                    ir_text = self._sanitize_ir(ir_text)
                except RuntimeError:
                    # Some functions may not have triple/datalayout; proceed anyway
                    pass
                func_ll.write_text(ir_text)

                # Step 4: Pre-vectorize
                prevec_ll = func_dir / f"{func_name}.prevec.ll"
                rc, stdout, stderr = await _run_cmd([
                    self.tools["opt"],
                    *self._target_args(),
                    f"-passes={PREVEC_PASSES}",
                    "-S", str(func_ll), "-o", str(prevec_ll),
                ])
                if rc != 0:
                    raise RuntimeError(f"opt prevec failed: {stderr}")

                # Step 5: VPlan explain (reads from stdin like the Makefile)
                prevec_data = prevec_ll.read_bytes()
                rc, stdout, stderr = await _run_cmd([
                    self.tools["opt"],
                    *self._target_args(),
                    "-passes=loop-vectorize",
                    "-vplan-explain",
                    "-disable-output",
                ], stdin_data=prevec_data)
                # vplan-explain may return non-zero for some benchmarks
                # but still produce useful output on stderr

                # Combine stdout+stderr (vplan-explain writes to stderr)
                raw_output = stderr if stderr else stdout
                loops = parse_vplan_output(raw_output)

                result = BenchResult(
                    func_name=func_name, category=category,
                    loops=loops, error=None, raw_output=raw_output,
                )

            except Exception as e:
                result = BenchResult(
                    func_name=func_name, category=category,
                    loops=[], error=str(e), raw_output="",
                )

        if self.on_progress:
            self.on_progress(result)
        return result

    async def run_all(self, func_names: list[str]) -> list[BenchResult]:
        tasks = [self.run_one(fn) for fn in func_names]
        return await asyncio.gather(*tasks)

    def cleanup(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)


# ─── Caching ────────────────────────────────────────────────────────────────


def _cache_path(variant: str, vlen: int) -> Path:
    return Path.home() / ".cache" / "vplan-diversity" / f"rvv-{variant}-vlen{vlen}.json"


def _llvm_version(tools: dict[str, str]) -> str:
    try:
        r = subprocess.run([tools["opt"], "--version"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            if "version" in line.lower():
                return line.strip()
    except Exception:
        pass
    return "unknown"


def load_cache(variant: str, vlen: int) -> list[BenchResult] | None:
    cp = _cache_path(variant, vlen)
    if not cp.exists():
        return None
    try:
        data = json.loads(cp.read_text())
        return [_bench_from_dict(d) for d in data["results"]]
    except Exception:
        return None


def save_cache(results: list[BenchResult], variant: str, vlen: int, tools: dict[str, str]):
    cp = _cache_path(variant, vlen)
    cp.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": datetime.now().isoformat(),
        "llvm_version": _llvm_version(tools),
        "variant": variant,
        "vlen": vlen,
        "results": [_bench_to_dict(r) for r in results],
    }
    cp.write_text(json.dumps(data, indent=2))


# ─── Analytics ──────────────────────────────────────────────────────────────


@dataclass
class DashboardStats:
    total_benchmarks: int = 0
    successful: int = 0
    failed: int = 0
    total_loops: int = 0
    total_plans: int = 0
    plan_count_dist: dict[int, int] = field(default_factory=dict)
    vf_type_dist: dict[str, int] = field(default_factory=dict)  # fixed/scalable/mixed
    selected_vf_dist: dict[str, int] = field(default_factory=dict)


@dataclass
class CategoryStats:
    category: str
    func_count: int = 0
    loop_count: int = 0
    plan_count: int = 0
    avg_plans_per_loop: float = 0.0
    fixed_vfs: int = 0
    scalable_vfs: int = 0
    failed: int = 0


@dataclass
class VFDistEntry:
    vf: str
    occurrences: int = 0
    selections: int = 0
    min_cost: int | None = None
    max_cost: int | None = None


def _classify_vf(vf: str) -> str:
    if "vscale" in vf.lower():
        return "scalable"
    return "fixed"


def compute_dashboard_stats(results: list[BenchResult]) -> DashboardStats:
    s = DashboardStats()
    s.total_benchmarks = len(results)
    plan_counts: list[int] = []

    for r in results:
        if r.error:
            s.failed += 1
            continue
        s.successful += 1
        s.total_loops += len(r.loops)
        for loop in r.loops:
            s.total_plans += len(loop.plans)
            plan_counts.append(len(loop.plans))

            # VF type classification per loop
            vf_types = set()
            for plan in loop.plans:
                for vf in plan.vfs:
                    vf_types.add(_classify_vf(vf))
            if vf_types == {"fixed"}:
                s.vf_type_dist["fixed only"] = s.vf_type_dist.get("fixed only", 0) + 1
            elif vf_types == {"scalable"}:
                s.vf_type_dist["scalable only"] = s.vf_type_dist.get("scalable only", 0) + 1
            elif len(vf_types) > 1:
                s.vf_type_dist["mixed"] = s.vf_type_dist.get("mixed", 0) + 1

            if loop.selected_vf:
                s.selected_vf_dist[loop.selected_vf] = s.selected_vf_dist.get(loop.selected_vf, 0) + 1

    s.plan_count_dist = dict(Counter(plan_counts))
    return s


def compute_category_stats(results: list[BenchResult]) -> list[CategoryStats]:
    by_cat: dict[str, list[BenchResult]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)

    stats = []
    for cat in sorted(by_cat):
        cs = CategoryStats(category=cat)
        rs = by_cat[cat]
        cs.func_count = len(rs)
        for r in rs:
            if r.error:
                cs.failed += 1
                continue
            cs.loop_count += len(r.loops)
            for loop in r.loops:
                cs.plan_count += len(loop.plans)
                for plan in loop.plans:
                    for vf in plan.vfs:
                        if _classify_vf(vf) == "scalable":
                            cs.scalable_vfs += 1
                        else:
                            cs.fixed_vfs += 1
        if cs.loop_count > 0:
            cs.avg_plans_per_loop = cs.plan_count / cs.loop_count
        stats.append(cs)
    return stats


def compute_vf_distribution(results: list[BenchResult]) -> list[VFDistEntry]:
    vf_data: dict[str, VFDistEntry] = {}

    for r in results:
        for loop in r.loops:
            for plan in loop.plans:
                for vc in plan.costs:
                    if vc.vf not in vf_data:
                        vf_data[vc.vf] = VFDistEntry(vf=vc.vf)
                    e = vf_data[vc.vf]
                    e.occurrences += 1
                    if vc.cost is not None:
                        if e.min_cost is None or vc.cost < e.min_cost:
                            e.min_cost = vc.cost
                        if e.max_cost is None or vc.cost > e.max_cost:
                            e.max_cost = vc.cost

            if loop.selected_vf:
                if loop.selected_vf not in vf_data:
                    vf_data[loop.selected_vf] = VFDistEntry(vf=loop.selected_vf)
                vf_data[loop.selected_vf].selections += 1

    return sorted(vf_data.values(), key=lambda e: e.occurrences, reverse=True)


# ─── TUI ────────────────────────────────────────────────────────────────────

def _build_app_class():
    """Build and return the TUI App class (deferred import of textual)."""
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical, VerticalScroll
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
                bar = "█" * bar_len
                yield Label(f"{str(label):>8} │ {bar} {count}")

    class ProgressScreen(Static):
        def __init__(self, total: int, **kwargs):
            super().__init__(**kwargs)
            self._total = total
            self._completed = 0
            self._log_lines: list[str] = []

        def compose(self) -> ComposeResult:
            yield Label("[bold]Running vplan-explain pipeline…[/bold]", id="prog-title")
            yield ProgressBar(total=self._total, id="prog-bar")
            yield Label("0 / 0", id="prog-count")
            yield Static("", id="prog-log")

        def advance(self, func_name: str, error: str | None):
            self._completed += 1
            status = "✓" if not error else f"✗ {error[:60]}"
            self._log_lines.append(f"  {func_name}: {status}")
            # Keep last 20 lines
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
                        lines.append(f"    → selected VF={loop.selected_vf} plan={loop.selected_plan}")
            lines.append("")
            lines.append("[dim]─── Raw Output ───[/dim]")
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
                        # Show top 15 selected VFs
                        top_sel = dict(sorted(
                            stats.selected_vf_dist.items(),
                            key=lambda x: x[1], reverse=True,
                        )[:15])
                        yield BarChart(top_sel, max_width=50)

                with TabPane("Benchmarks", id="benchmarks"):
                    with Vertical():
                        yield Input(placeholder="Filter benchmarks…", id="bench-filter")
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
            # Benchmark table
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
                    vfs_str += "…"
                min_cost_str = str(min_cost) if min_cost is not None else "-"
                sel_str = ", ".join(sorted(sel_vfs)) if sel_vfs else "-"
                status = "OK" if not r.error else "ERR"
                row = (r.func_name, r.category, str(n_loops), str(n_plans),
                       vfs_str, min_cost_str, sel_str, status)
                self._all_bench_rows.append(row)
                bt.add_row(*row, key=r.func_name)

            # Category table
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

            # VF distribution tables
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
            # Placeholder — would need to re-run the pipeline
            self.notify("Re-run not yet implemented in TUI mode. Restart the tool.")

        def set_results(self, results: list[BenchResult]) -> None:
            """Called after pipeline completes to switch from progress to dashboard."""
            self._results = results
            # Full remount
            self.refresh()

    return VPlanDiversityApp, ProgressScreen


# ─── Main Orchestration ────────────────────────────────────────────────────


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

    # Phase 1: Run pipeline with progress
    results: list[BenchResult] = []
    completed_count = 0

    app = AppClass(
        results=None,
        runner_args={
            "total": len(func_names),
            "subtitle": f"type={args.type} vlen={args.vlen}",
        },
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

        # Save cache
        save_cache(results, args.type, args.vlen, tools)

        # Exit progress app, will relaunch with results
        app.exit()

    def _tui_progress(the_app: AppClass, result: BenchResult):
        nonlocal completed_count
        completed_count += 1
        if the_app._progress_screen:
            the_app.call_from_thread(
                the_app._progress_screen.advance,
                result.func_name, result.error,
            )

    # Launch pipeline in background thread, run app in main thread
    import threading

    def _run_pipeline_thread():
        loop = asyncio.new_event_loop()
        loop.run_until_complete(do_pipeline())

    t = threading.Thread(target=_run_pipeline_thread, daemon=True)
    t.start()
    await app.run_async()
    t.join(timeout=5)

    # Phase 2: Launch dashboard with results
    if results:
        dashboard_app = AppClass(
            results=results,
            runner_args={
                "subtitle": f"type={args.type} vlen={args.vlen} | {len(results)} benchmarks",
            },
        )
        await dashboard_app.run_async()


def main():
    parser = argparse.ArgumentParser(
        description="VPlan Diversity Diagnostic Tool — analyze vectorizer plan diversity across TSVC benchmarks",
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

    # Try cache first
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
        json.dump([_bench_to_dict(r) for r in results], sys.stdout, indent=2)
        print()
        return

    if results:
        # Launch TUI dashboard directly
        AppClass, _ = _build_app_class()
        app = AppClass(
            results=results,
            runner_args={
                "subtitle": f"type={args.type} vlen={args.vlen} | {len(results)} benchmarks",
            },
        )
        app.run()
    else:
        # Run pipeline with TUI progress, then dashboard
        asyncio.run(run_pipeline_with_tui(args))


if __name__ == "__main__":
    main()
