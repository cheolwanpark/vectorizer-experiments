"""TSVC discovery, LLVM tool resolution, output parsing, and pipeline runner."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .models import (
    AnalysisEntry,
    AppRuntimeConfig,
    BenchResult,
    FunctionAnalysisReport,
    LoopInfo,
    VFCost,
    VPlan,
)

# ─── TSVC Source Acquisition ────────────────────────────────────────────────

_PACKAGE_DIR = Path(__file__).resolve().parent


def _find_tsvc_dir() -> Path:
    """Locate the TSVC benchmark directory."""
    # Check relative to the package directory (two levels up to project root)
    project_root = _PACKAGE_DIR.parent.parent
    local = project_root / "TSVC"
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
_SELECTED_DUMP_HEADER_RE = re.compile(
    r'^LV: Loop\[(\d+)\] selected VPlan dump follows$'
)


def parse_vplan_output(stderr_text: str) -> list[LoopInfo]:
    """Parse vplan-explain stderr output into LoopInfo list."""
    loops: list[LoopInfo] = []

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

            if not costs:
                for vf in vfs:
                    costs.append(VFCost(vf=vf, cost=None))

            plans.append(VPlan(index=plan_idx, vfs=vfs, costs=costs))

        sel_match = _SELECTION_RE.search(block)
        selected_vf = sel_match.group(1) if sel_match else None
        selected_plan = int(sel_match.group(2)) if sel_match else None

        loops.append(LoopInfo(
            index=loop_idx, path=path, plan_count=plan_count,
            plans=plans, selected_vf=selected_vf, selected_plan=selected_plan,
        ))

    return loops


def pick_highest_vf(vfs: list[str]) -> str:
    """Select the highest VF by numeric magnitude, keeping ties deterministic."""
    if not vfs:
        raise ValueError("cannot select highest VF from an empty list")

    ranked = []
    for index, vf in enumerate(vfs):
        match = re.search(r'(\d+)(?!.*\d)', vf)
        magnitude = int(match.group(1)) if match else -1
        ranked.append((magnitude, index, vf))
    return max(ranked)[2]


def encode_use_vf(vf: str) -> str:
    """Convert a parsed VF label into the -vplan-use-vf CLI syntax."""
    text = vf.strip().lower()
    match = re.search(r'(\d+)(?!.*\d)', text)
    if match is None:
        raise ValueError(f"unable to encode VF value: {vf}")
    scale = match.group(1)
    if "vscale" in text:
        return f"scalable:{scale}"
    return f"fixed:{scale}"


def build_forced_vf_arg(result: BenchResult, target_loop_index: int, forced_vf: str) -> str:
    """Build the positional -vplan-use-vf value for one selected loop."""
    encoded_vf = encode_use_vf(forced_vf)
    if not result.loops:
        return encoded_vf

    max_loop_index = max(loop.index for loop in result.loops)
    if max_loop_index == 0:
        return encoded_vf

    entries = ["-"] * (max_loop_index + 1)
    entries[target_loop_index] = encoded_vf
    return ",".join(entries)


def extract_selected_vplan_dumps(verbose_text: str) -> dict[int, str]:
    """Extract the selected VPlan dump body keyed by loop index."""
    dumps: dict[int, str] = {}
    current_loop: int | None = None
    current_lines: list[str] = []

    for line in verbose_text.splitlines():
        header = _SELECTED_DUMP_HEADER_RE.match(line)
        if header:
            if current_loop is not None:
                dumps[current_loop] = "\n".join(current_lines).strip()
            current_loop = int(header.group(1))
            current_lines = []
            continue

        if current_loop is not None and line.startswith("LV:"):
            dumps[current_loop] = "\n".join(current_lines).strip()
            current_loop = None
            current_lines = []

        if current_loop is not None:
            current_lines.append(line)

    if current_loop is not None:
        dumps[current_loop] = "\n".join(current_lines).strip()

    return dumps


def format_cost_summary(plan: VPlan) -> str:
    if not plan.costs:
        return "-"
    return ", ".join(
        f"{cost.vf}={cost.cost if cost.cost is not None else 'n/a'}"
        for cost in plan.costs
    )


def build_analysis_markdown_report(report: FunctionAnalysisReport,
                                   runtime: AppRuntimeConfig) -> str:
    """Render a shareable Markdown report for one function analysis."""
    lines = [
        f"# VPlan Analysis: `{report.func_name}`",
        "",
        f"- Category: `{report.category}`",
        f"- TYPE: `{runtime.variant}`",
        f"- VLEN: `{runtime.vlen}`",
        "",
        "| Loop | Plan | Forced VF | All VFs | Costs | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for entry in report.entries:
        status = entry.status.upper()
        if entry.message:
            status = f"{status}: {entry.message}"
        lines.append(
            f"| {entry.loop_index} | {entry.plan_index} | `{entry.forced_vf}` | "
            f"`{', '.join(entry.all_vfs)}` | `{entry.cost_summary}` | {status} |"
        )

    for entry in report.entries:
        lines.extend([
            "",
            f"## Loop[{entry.loop_index}] Plan {entry.plan_index}",
            "",
            f"- Forced VF: `{entry.forced_vf}`",
            f"- All VFs: `{', '.join(entry.all_vfs)}`",
            f"- Costs: `{entry.cost_summary}`",
            f"- Command: `{entry.command}`",
            f"- Status: `{entry.status}`",
        ])
        if entry.message:
            lines.append(f"- Note: {entry.message}")
        lines.append("")
        if entry.dump_text:
            lines.extend([
                "```text",
                entry.dump_text,
                "```",
            ])
        else:
            lines.append("_No VPlan dump captured._")

    return "\n".join(lines)


def analyze_function_vplans(result: BenchResult, runtime: AppRuntimeConfig,
                            on_progress=None) -> FunctionAnalysisReport:
    """Run forced-VF make opt commands and capture one selected dump per plan."""
    if result.error:
        raise RuntimeError(f"{result.func_name} failed in the baseline run: {result.error}")
    if not result.loops:
        raise RuntimeError(f"{result.func_name} has no parsed loops to analyze")

    total_entries = sum(len(loop.plans) for loop in result.loops)
    if total_entries == 0:
        raise RuntimeError(f"{result.func_name} has no parsed VPlans to analyze")

    tsvc_dir = Path(runtime.tsvc_dir)
    log_path = tsvc_dir / ".build" / runtime.variant / result.func_name / "opt.verbose.log"
    entries: list[AnalysisEntry] = []
    completed = 0

    for loop in sorted(result.loops, key=lambda item: item.index):
        for plan in loop.plans:
            forced_vf = pick_highest_vf(plan.vfs)
            vf_arg = build_forced_vf_arg(result, loop.index, forced_vf)
            cmd = [
                "make", "--no-print-directory", "opt", result.func_name,
                f"TYPE={runtime.variant}",
                f"VLEN={runtime.vlen}",
                f"USE_VF={vf_arg}",
            ]
            for tool_var, tool_name in (
                ("CLANG", "clang"),
                ("OPT", "opt"),
                ("LLVM_EXTRACT", "llvm-extract"),
            ):
                tool_path = runtime.tools.get(tool_name)
                if tool_path:
                    cmd.append(f"{tool_var}={tool_path}")
            if runtime.llvm_custom:
                cmd.append(f"LLVM_CUSTOM={runtime.llvm_custom}")

            proc = subprocess.run(
                cmd,
                cwd=tsvc_dir,
                text=True,
                capture_output=True,
            )

            status = "ok"
            message: str | None = None
            dump_text = ""
            selected_vf: str | None = None
            selected_plan: int | None = None

            if proc.returncode != 0:
                output = (proc.stderr or proc.stdout or "").strip().splitlines()
                detail = output[-1] if output else "make opt failed"
                status = "error"
                message = detail
            elif not log_path.exists():
                status = "error"
                message = f"missing verbose log: {log_path}"
            else:
                verbose_text = log_path.read_text(errors="replace")
                parsed_loops = parse_vplan_output(verbose_text)
                parsed_loop = next(
                    (item for item in parsed_loops if item.index == loop.index),
                    None,
                )
                dump_text = extract_selected_vplan_dumps(verbose_text).get(loop.index, "")

                if parsed_loop is None:
                    status = "error"
                    message = f"Loop[{loop.index}] summary not found in verbose log"
                else:
                    selected_vf = parsed_loop.selected_vf
                    selected_plan = parsed_loop.selected_plan
                    if not dump_text:
                        status = "error"
                        message = f"Loop[{loop.index}] selected dump missing in verbose log"
                    elif selected_vf != forced_vf or selected_plan != plan.index:
                        status = "warning"
                        message = (
                            f"expected VF={forced_vf} plan={plan.index}, "
                            f"got VF={selected_vf} plan={selected_plan}"
                        )

            entry = AnalysisEntry(
                loop_index=loop.index,
                plan_index=plan.index,
                all_vfs=plan.vfs,
                forced_vf=forced_vf,
                cost_summary=format_cost_summary(plan),
                command=shlex.join(cmd),
                log_path=str(log_path),
                status=status,
                dump_text=dump_text,
                message=message,
                selected_vf=selected_vf,
                selected_plan=selected_plan,
            )
            entries.append(entry)
            completed += 1
            if on_progress:
                on_progress(completed, total_entries, entry)

    report = FunctionAnalysisReport(
        func_name=result.func_name,
        category=result.category,
        entries=entries,
        markdown_report="",
    )
    report.markdown_report = build_analysis_markdown_report(report, runtime)
    return report


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

                full_ll = await self._get_full_ll(source_path)

                func_dir = self.work_dir / func_name
                func_dir.mkdir(exist_ok=True)
                func_ll = func_dir / f"{func_name}.ll"

                rc, stdout, stderr = await _run_cmd([
                    self.tools["llvm-extract"],
                    "-S", f"--func={func_name}",
                    str(full_ll), "-o", str(func_ll),
                ])
                if rc != 0:
                    raise RuntimeError(f"llvm-extract failed: {stderr}")

                ir_text = func_ll.read_text()
                try:
                    ir_text = self._sanitize_ir(ir_text)
                except RuntimeError:
                    pass
                func_ll.write_text(ir_text)

                prevec_ll = func_dir / f"{func_name}.prevec.ll"
                rc, stdout, stderr = await _run_cmd([
                    self.tools["opt"],
                    *self._target_args(),
                    f"-passes={PREVEC_PASSES}",
                    "-S", str(func_ll), "-o", str(prevec_ll),
                ])
                if rc != 0:
                    raise RuntimeError(f"opt prevec failed: {stderr}")

                prevec_data = prevec_ll.read_bytes()
                rc, stdout, stderr = await _run_cmd([
                    self.tools["opt"],
                    *self._target_args(),
                    "-passes=loop-vectorize",
                    "-vplan-explain",
                    "-disable-output",
                ], stdin_data=prevec_data)

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
