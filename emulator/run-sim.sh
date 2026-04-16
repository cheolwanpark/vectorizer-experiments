#!/usr/bin/env python3
"""
Unified simulator runner.

Examples:
  ./run-sim.sh saturn my-test.elf
  ./run-sim.sh saturn src/kernel.c --lmul=2
  ./run-sim.sh xiangshan.MinimalConfig workloads/hello.bin
  ./run-sim.sh t1 tests/rvv-test.elf

Config:
  - Uses `./sim-configs.yaml` for simulator paths and defaults.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SimResult:
    """Result of a simulation run."""
    exit_code: int
    wall_time_s: float
    cycles: int | None = None           # Total simulation cycles
    kernel_cycles: int | None = None    # Kernel-only cycles (from mcycle CSR)
    status: str = "UNKNOWN"
    log_file: Path | None = None
    trace_file: Path | None = None
    sim_out_dir: Path | None = None


@dataclass(frozen=True)
class TargetSpec:
    group: str
    config: str | None


# Mapping from sim-configs group names to build-kernel target names
GROUP_TO_BUILD_TARGET = {
    "saturn": "saturn",
    "ara": "ara",
    "xiangshan": "xiangshan",
    "t1": "t1",
    "gem5": "gem5",
    "vicuna": "vicuna",
}


def _parse_target(token: str) -> TargetSpec:
    token = token.strip()
    if not token:
        raise ValueError("empty target")
    if "." in token:
        group, rest = token.split(".", 1)
        rest = rest.strip()
        return TargetSpec(group=group.strip(), config=rest if rest else None)
    return TargetSpec(group=token, config=None)


def _load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()

    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("config root must be an object")
            return data
        except json.JSONDecodeError:
            pass

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            f"Failed to parse {path}. Install PyYAML: pip install pyyaml"
        ) from exc

    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("config root must be a mapping/object")
    return data


def _require_mapping(obj: Any, where: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError(f"{where} must be an object/mapping")
    return obj


def _resolve_group(group_name: str, config: dict[str, Any]) -> dict[str, Any]:
    groups = _require_mapping(config.get("groups"), "groups")
    group = groups.get(group_name)
    if group is None:
        known = ", ".join(sorted(groups.keys()))
        raise ValueError(f"unknown group '{group_name}' (known: {known})")
    return _require_mapping(group, f"groups.{group_name}")


def _find_simulator(kind: str, spec: TargetSpec, config: dict[str, Any], root_dir: Path) -> Path:
    """Find the simulator binary for the given kind and spec."""
    defaults = _require_mapping(config.get("defaults", {}), "defaults")

    if kind == "chipyard-verilator":
        chipyard_dir = Path(defaults.get("chipyard_dir", str(root_dir / "chipyard"))).expanduser()
        if not chipyard_dir.is_absolute():
            chipyard_dir = (root_dir / chipyard_dir).resolve()

        group = _resolve_group(spec.group, config)
        configs = group.get("configs", {})
        config_name = spec.config or str(group.get("default_config", "")).strip()
        resolved = configs.get(config_name, config_name)
        if isinstance(resolved, str):
            config_name = resolved

        sim_path = chipyard_dir / "sims" / "verilator" / f"simulator-chipyard.harness-{config_name}"
        return sim_path

    elif kind == "xiangshan":
        xiangshan_dir = Path(defaults.get("xiangshan_dir", str(root_dir / "XiangShan"))).expanduser()
        if not xiangshan_dir.is_absolute():
            xiangshan_dir = (root_dir / xiangshan_dir).resolve()
        return xiangshan_dir / "build" / "emu"

    elif kind == "t1":
        t1_dir = Path(defaults.get("t1_dir", str(root_dir / "t1-micro58ae"))).expanduser()
        if not t1_dir.is_absolute():
            t1_dir = (root_dir / t1_dir).resolve()
        # Try common locations
        for candidate in [
            t1_dir / "result" / "bin" / "t1rocketemu-verilated-simulator",
            t1_dir / "result" / "emu",
        ]:
            if candidate.exists():
                return candidate
        return t1_dir / "result" / "bin" / "t1rocketemu-verilated-simulator"

    elif kind == "gem5":
        gem5_dir = Path(defaults.get("gem5_dir", str(root_dir / "gem5"))).expanduser()
        if not gem5_dir.is_absolute():
            gem5_dir = (root_dir / gem5_dir).resolve()
        return gem5_dir / "build" / "RISCV" / "gem5.opt"

    elif kind == "vicuna":
        # Vicuna simulator built via artifacts/build_vicuna.sh
        vreg_w = spec.config or "512"
        for candidate in [
            root_dir / "artifacts" / f"vicuna-sim-{vreg_w}",
            root_dir / f"artifacts/vicuna-verilator-{vreg_w}" / "obj_dir" / "Vvproc_top",
        ]:
            if candidate.exists():
                return candidate
        return root_dir / "artifacts" / f"vicuna-sim-{vreg_w}"

    else:
        raise ValueError(f"unsupported kind: {kind}")


def _parse_cycles_from_log(log_content: str, kind: str) -> int | None:
    """Parse cycle count from simulator output."""
    patterns = [
        # XiangShan style (cycleCnt may have commas: 93,558)
        r"total guest instructions\s*=\s*([\d,]+)",
        r"host time\s*=.*?cycleCnt\s*=\s*([\d,]+)",
        r"cycleCnt\s*=\s*([\d,]+)",
        # Chipyard/Rocket style
        r"mcycle\s*=\s*([\d,]+)",
        r"Completed after\s+([\d,]+)\s+(?:simulation\s+)?cycles",
        r"cycles:\s*([\d,]+)",
        r"Total cycles\s*[:=]\s*([\d,]+)",
        # T1 style
        r"total_cycles\s*[:=]\s*([\d,]+)",
        r"\[CYCLE\]\s*([\d,]+)",
        # Vicuna style (UART output)
        r"cycles=([\d,]+)",
        # Generic
        r"([\d,]+)\s+cycles",
    ]

    for pattern in patterns:
        match = re.search(pattern, log_content, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def _parse_gem5_total_cycles(output_text: str, stats_text: str | None = None) -> int | None:
    """Parse total gem5 cycles from stdout/stderr or stats.txt."""
    search_space = "\n".join(part for part in (stats_text, output_text) if part)
    patterns = [
        r"system\.cpu\.numCycles\s+(\d+)",
        r"simTicks\s+(\d+)",
        r"final_tick=(\d+)",
        r"Exiting @ tick (\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, search_space)
        if match:
            return int(match.group(1))
    return None


def _parse_kernel_cycles_from_trace(trace_content: str) -> int | None:
    """Parse kernel cycles from verbose trace by finding csrr mcycle instructions.

    The harness does:
      start = rdcycle();  // csrr s0, mcycle
      kernel();
      end = rdcycle();    // csrr s1, mcycle

    We look for consecutive csrr mcycle instructions and compute end - start.
    """
    # Pattern: C0:  CYCLE [1] pc=[...] W[r REG=VALUE]... inst=[...] csrr REG, mcycle
    pattern = r"C0:\s+(\d+)\s+\[1\].*?W\[r\s+\d+=([0-9a-fA-F]+)\].*?csrr\s+\w+,\s*mcycle"
    matches = list(re.finditer(pattern, trace_content))

    if len(matches) >= 2:
        # Get the last two mcycle reads (start and end of timed run)
        # Note: there may be warmup mcycle reads too, so we take the last two
        start_match = matches[-2]
        end_match = matches[-1]

        start_val = int(start_match.group(2), 16)
        end_val = int(end_match.group(2), 16)

        kernel_cycles = end_val - start_val
        return kernel_cycles if kernel_cycles > 0 else None

    return None


def _parse_kernel_cycles_from_xiangshan_trace(trace_path: Path) -> int | None:
    """Parse kernel cycles from XiangShan commit trace.

    XiangShan trace format:
    [N] commit pc XXX inst XXX wen 1 dst N data XXX idx XXX

    mcycle CSR read instructions have inst starting with 'b00' (mcycle=0xB00).
    The data field contains the mcycle value.
    """
    if not trace_path.exists():
        return None

    # Pattern for mcycle CSR read: inst starts with b00
    pattern = r'\[\d+\] commit pc [0-9a-f]+ inst (b00[0-9a-f]+) wen 1 dst \d+ data ([0-9a-f]+)'

    mcycle_reads = []
    try:
        with open(trace_path, 'r') as f:
            for line in f:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    data = int(match.group(2), 16)
                    mcycle_reads.append(data)
    except Exception:
        return None

    if len(mcycle_reads) >= 2:
        # Last two are start and end of timed kernel run
        start = mcycle_reads[-2]
        end = mcycle_reads[-1]
        kernel_cycles = end - start
        return kernel_cycles if kernel_cycles > 0 else None

    return None


def _parse_kernel_cycles_from_t1_rtl_event(rtl_event_path: Path) -> int | None:
    """Parse kernel cycles from T1 rtl-event.jsonl.

    T1 harness stores:
    - s0 (idx=8): start mcycle (value ≈ sim_cycle)
    - s1 (idx=9): end mcycle, then (end - start) = kernel cycles

    Pattern:
    1. s0 gets start mcycle (value ≈ sim_cycle)
    2. kernel runs
    3. s1 gets end mcycle (value ≈ sim_cycle)
    4. s1 gets (end - start) = kernel cycles (small value)
    """
    if not rtl_event_path.exists():
        return None

    s0_writes: list[tuple[int, int]] = []  # (data, cycle)
    s1_writes: list[tuple[int, int]] = []

    try:
        with open(rtl_event_path, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line)
                    if event.get("event") == "RegWrite":
                        idx = event.get("idx")
                        data = int(event.get("data", "0"), 16)
                        cycle = event.get("cycle", 0)
                        if idx == 8:  # s0
                            s0_writes.append((data, cycle))
                        elif idx == 9:  # s1
                            s1_writes.append((data, cycle))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return None

    # Find s0 write where value ≈ sim_cycle (start mcycle)
    start_mcycle = None
    start_sim_cycle = None
    for data, cycle in s0_writes:
        if abs(data - cycle) < 10 and data > 10000:
            start_mcycle = data
            start_sim_cycle = cycle

    if start_mcycle is None:
        return None

    # Find s1 writes after start_sim_cycle
    # Pattern: first s1 where value ≈ cycle (end mcycle), then s1 with small value (kernel cycles)
    end_mcycle = None
    for data, cycle in s1_writes:
        if cycle > start_sim_cycle:
            if end_mcycle is None and abs(data - cycle) < 10:
                # This is end mcycle
                end_mcycle = data
            elif end_mcycle is not None and data < end_mcycle - start_mcycle + 1000:
                # This could be kernel cycles
                if 100 < data < 500000:  # reasonable kernel cycles range
                    return data

    # Fallback: calculate from end - start
    if end_mcycle is not None:
        return end_mcycle - start_mcycle

    return None


def _parse_status_from_log(log_content: str, exit_code: int) -> str:
    """Determine status from log content."""
    if "*** PASSED ***" in log_content or "PASSED" in log_content or "HIT GOOD TRAP" in log_content:
        return "PASS"
    if "*** FAILED ***" in log_content or "FAILED" in log_content:
        return "FAIL"
    if "Assertion" in log_content and "failed" in log_content.lower():
        return "ASSERT"
    if "TIMEOUT" in log_content:
        return "TIMEOUT"
    if exit_code == 0:
        return "OK"
    if exit_code == 124:
        return "TIMEOUT"
    return f"EXIT:{exit_code}"


def build_kernel(
    root_dir: Path,
    source: Path,
    target: str,
    *,
    lmul: int = 1,
    len_1d: int = 1000,
    use_vf: str | None = None,
    cflags: str | None = None,
    optflags: str | None = None,
    build_out_dir: Path | None = None,
) -> Path:
    """Build a .c kernel using run/build-kernel and return the ELF path."""
    build_script = root_dir / "run" / "build-kernel"
    if not build_script.exists():
        raise FileNotFoundError(f"build-kernel not found: {build_script}")

    # Determine output path
    kernel_name = source.stem
    out_dir = build_out_dir if build_out_dir is not None else root_dir / "run" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    vf_suffix = f"_vf{use_vf}" if use_vf is not None else ""
    output_elf = out_dir / f"{kernel_name}_{target}_lmul{lmul}{vf_suffix}.elf"

    cmd = [
        "bash",
        str(build_script),
        target,
        str(source),
        f"--lmul={lmul}",
        f"--len={len_1d}",
        f"--output={output_elf}",
    ]
    if use_vf is not None:
        cmd.append(f"--use-vf={use_vf}")
    if cflags:
        cmd.append(f"--cflags={cflags}")
    if optflags:
        cmd.append(f"--optflags={optflags}")

    vf_text = f", use_vf={use_vf}" if use_vf is not None else ""
    print(f"Building kernel: {source.name} (target={target}, lmul={lmul}{vf_text})")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Build failed:\n{result.stderr}", file=sys.stderr)
        raise RuntimeError(f"build-kernel failed with exit code {result.returncode}")

    if not output_elf.exists():
        raise FileNotFoundError(f"Build succeeded but ELF not found: {output_elf}")

    print(f"Built: {output_elf}")
    return output_elf


def _find_spike_dasm(root_dir: Path) -> Path | None:
    """Find spike-dasm binary."""
    # Check common locations
    candidates = [
        root_dir / "chipyard" / ".conda-env" / "riscv-tools" / "bin" / "spike-dasm",
        root_dir / "chipyard" / "toolchains" / "riscv-tools" / "riscv-isa-sim" / "build" / "spike-dasm",
        Path(os.environ.get("RISCV", "/opt/riscv")) / "bin" / "spike-dasm",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    # Try PATH
    import shutil
    path_dasm = shutil.which("spike-dasm")
    if path_dasm:
        return Path(path_dasm)
    return None


def _print_cmd(cmd: str | list[str], dry_run: bool = False) -> None:
    """Print the command in an emphasized format."""
    if isinstance(cmd, list):
        cmd_str = shlex.join(cmd)
    else:
        cmd_str = cmd
    separator = "═" * 70

    if dry_run:
        print(f"\n{separator}")
        print(f"[DRY-RUN] Would execute:")
        print(f"{separator}")
        print(cmd_str)
        print(f"{separator}\n")
    else:
        print(f"\n{separator}")
        print(f"CMD: {cmd_str}")
        print(f"{separator}\n")


def run_chipyard_sim(
    sim_path: Path,
    workload: Path,
    *,
    max_cycles: int = 100_000_000,
    timeout: int = 600,
    extra_args: list[str] | None = None,
    dry_run: bool = False,
    log_dir: Path | None = None,
    root_dir: Path | None = None,
    verbose: bool = True,
) -> SimResult:
    """Run a Chipyard Verilator simulation.

    When verbose=True (default), uses spike-dasm to decode instruction trace.
    Logs are saved to log_dir (default: sim-logs/).
    """
    if not sim_path.exists():
        raise FileNotFoundError(f"Simulator not found: {sim_path}")
    if not workload.exists():
        raise FileNotFoundError(f"Workload not found: {workload}")

    # Setup log directory and files
    if log_dir is None:
        log_dir = (root_dir or Path.cwd()) / "sim-logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_base = log_dir / workload.stem
    log_file = Path(f"{log_base}.log")
    out_file = Path(f"{log_base}.out")

    # Ara uses rdtime for timeout, which doesn't match actual simulation cycles
    # Setting max_core_cycles=0 disables the timeout for Ara
    is_ara = "Ara" in str(sim_path)
    effective_max_cycles = 0 if is_ara else max_cycles

    # Build permissive args (options that go between +permissive and +permissive-off)
    permissive_args = [
        f"+max_core_cycles={effective_max_cycles}",
        f"+loadmem={workload}",
    ]
    if verbose:
        permissive_args.append("+verbose")

    # Find spike-dasm for verbose mode
    spike_dasm = None
    if verbose and root_dir:
        spike_dasm = _find_spike_dasm(root_dir)

    if extra_args:
        permissive_args.extend(extra_args)

    # Build command
    if verbose and spike_dasm:
        # Use shell command with spike-dasm pipe
        # Format: (set -o pipefail && sim +permissive ARGS +permissive-off binary 2> >(spike-dasm > out) | tee log)
        sim_cmd_parts = [
            shlex.quote(str(sim_path)),
            "+permissive",
            *[shlex.quote(a) if " " in a else a for a in permissive_args],
            "+permissive-off",
            shlex.quote(str(workload)),
        ]
        # ulimit -s 65536 required for mmap in ELF loading
        shell_cmd = (
            f"(ulimit -s 65536 && set -o pipefail && {' '.join(sim_cmd_parts)} "
            f"2> >({shlex.quote(str(spike_dasm))} > {shlex.quote(str(out_file))}) "
            f"| tee {shlex.quote(str(log_file))})"
        )
        _print_cmd(shell_cmd, dry_run)

        if dry_run:
            return SimResult(exit_code=0, wall_time_s=0.0, status="DRY-RUN", log_file=log_file)

        start = time.time()
        try:
            result = subprocess.run(
                shell_cmd,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            exit_code = result.returncode
            # Read log file for parsing
            output = ""
            if log_file.exists():
                output = log_file.read_text()
            output += result.stdout + result.stderr
        except subprocess.TimeoutExpired as e:
            exit_code = 124
            output = (e.stdout or "") + (e.stderr or "") + "\nTIMEOUT"
        wall_time = time.time() - start
    else:
        # Simple mode without spike-dasm
        # Build shell command with ulimit -s 65536 for mmap in ELF loading
        cmd_parts = [
            shlex.quote(str(sim_path)),
            "+permissive",
            *[shlex.quote(a) if " " in a else a for a in permissive_args],
            "+permissive-off",
            shlex.quote(str(workload)),
        ]
        shell_cmd = f"ulimit -s 65536 && {' '.join(cmd_parts)}"
        _print_cmd(shell_cmd, dry_run)

        if dry_run:
            return SimResult(exit_code=0, wall_time_s=0.0, status="DRY-RUN", log_file=log_file)

        start = time.time()
        try:
            result = subprocess.run(
                shell_cmd,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            exit_code = result.returncode
            output = result.stdout + result.stderr
            # Save log even in simple mode
            log_file.write_text(output)
        except subprocess.TimeoutExpired as e:
            exit_code = 124
            output = (e.stdout or "") + (e.stderr or "") + "\nTIMEOUT"
        wall_time = time.time() - start

    cycles = _parse_cycles_from_log(output, "chipyard")
    kernel_cycles = None

    # In verbose mode, PASSED/cycles message is in the .out file (via spike-dasm stderr redirect)
    # Also parse kernel cycles from mcycle CSR reads in the trace
    if out_file.exists():
        out_content = out_file.read_text()
        if cycles is None:
            cycles = _parse_cycles_from_log(out_content, "chipyard")
        # Parse kernel cycles from trace (csrr mcycle instructions)
        kernel_cycles = _parse_kernel_cycles_from_trace(out_content)
        output += out_content  # Include for status parsing too

    status = _parse_status_from_log(output, exit_code)

    return SimResult(
        exit_code=exit_code,
        wall_time_s=wall_time,
        cycles=cycles,
        kernel_cycles=kernel_cycles,
        status=status,
        log_file=log_file,
    )


def run_xiangshan_sim(
    sim_path: Path,
    workload: Path,
    *,
    max_cycles: int = 100_000_000,
    timeout: int = 600,
    extra_args: list[str] | None = None,
    dry_run: bool = False,
    log_dir: Path | None = None,
    root_dir: Path | None = None,
    verbose: bool = False,
) -> SimResult:
    """Run a XiangShan emu simulation.

    Kernel cycles are extracted from UART output (KC=<number>).
    When verbose=True, also enables commit trace logging for debug/waveform.
    Options:
      --dump-commit-trace  - dump commit trace when log is enabled
      -b/--log-begin=NUM   - display log from NUM th cycle
      -e/--log-end=NUM     - stop display log at NUM th cycle
    """
    if not sim_path.exists():
        raise FileNotFoundError(f"Simulator not found: {sim_path}")
    if not workload.exists():
        raise FileNotFoundError(f"Workload not found: {workload}")

    # Setup log directory
    if log_dir is None:
        log_dir = (root_dir or Path.cwd()) / "sim-logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_base = log_dir / workload.stem
    log_file = Path(f"{log_base}.log")
    trace_file = Path(f"{log_base}.trace") if verbose else None

    base_cmd = [
        str(sim_path),
        "-i", str(workload),
        f"--max-cycles={max_cycles}",
    ]

    if extra_args:
        base_cmd.extend(extra_args)

    if dry_run:
        cmd = base_cmd + (["--dump-commit-trace", "-b", "0"] if verbose else [])
        _print_cmd(cmd, dry_run)
        return SimResult(exit_code=0, wall_time_s=0.0, status="DRY-RUN", log_file=log_file, trace_file=trace_file)

    kernel_cycles = None

    # Verbose mode: run with commit trace (for waveform/debug analysis)
    if verbose and trace_file:
        cmd = base_cmd + ["--dump-commit-trace"]
    else:
        cmd = base_cmd.copy()

    _print_cmd(cmd, dry_run)

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = result.returncode
        output = result.stdout + result.stderr
        log_file.write_text(output)
    except subprocess.TimeoutExpired as e:
        exit_code = 124
        output = (e.stdout or "") + (e.stderr or "") + "\nTIMEOUT"

    wall_time = time.time() - start
    cycles = _parse_cycles_from_log(output, "xiangshan")
    status = _parse_status_from_log(output, exit_code)

    # Parse kernel cycles from UART output: "KC=<number>"
    kc_match = re.search(r'KC=(\d+)', output)
    if kc_match:
        kernel_cycles = int(kc_match.group(1))

    return SimResult(
        exit_code=exit_code,
        wall_time_s=wall_time,
        cycles=cycles,
        kernel_cycles=kernel_cycles,
        status=status,
        log_file=log_file,
        trace_file=trace_file if (trace_file and trace_file.exists()) else None,
    )


def run_t1_sim(
    sim_path: Path,
    workload: Path,
    *,
    max_cycles: int = 100_000_000,
    timeout: int = 600,
    extra_args: list[str] | None = None,
    dry_run: bool = False,
    log_dir: Path | None = None,
    root_dir: Path | None = None,
    verbose: bool = True,
) -> SimResult:
    """Run a T1 simulation.

    T1 uses plusarg format for arguments:
      +t1_elf_file=<path>      - ELF file to run
      +t1_dramsim3_cfg=<path>  - DRAMsim3 config file (use 'no' to disable)
      +t1_rtl_event_path=<path> - RTL event output path
      +t1_timeout=<cycles>     - Timeout in cycles (optional)
      +t1_global_timeout=<cycles> - Global timeout (optional)

    When verbose=True (default), sets RUST_LOG=TRACE for detailed instruction trace.
    """
    if not sim_path.exists():
        raise FileNotFoundError(f"Simulator not found: {sim_path}")
    if not workload.exists():
        raise FileNotFoundError(f"Workload not found: {workload}")

    # Setup log directory
    if log_dir is None:
        log_dir = (root_dir or Path.cwd()) / "sim-logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_base = log_dir / workload.stem
    log_file = Path(f"{log_base}.log")
    trace_file = Path(f"{log_base}.trace") if verbose else None
    rtl_event_file = log_dir / f"{workload.stem}-rtl-event.jsonl"
    sim_result_file = log_dir / f"{workload.stem}-sim_result.json"

    # T1 uses plusarg format, not standard CLI args
    cmd = [
        str(sim_path),
        f"+t1_elf_file={workload}",
        "+t1_dramsim3_cfg=no",  # Disable DRAMsim3 by default
        f"+t1_rtl_event_path={rtl_event_file}",
    ]

    # Add timeout if specified
    if max_cycles > 0:
        cmd.append(f"+t1_timeout={max_cycles}")

    if extra_args:
        cmd.extend(extra_args)

    # Set environment for verbose mode (RUST_LOG=TRACE enables instruction trace)
    env = os.environ.copy()
    if verbose:
        env["RUST_LOG"] = "TRACE"
        print(f"[T1 Verbose] RUST_LOG=TRACE (instruction trace enabled)")

    _print_cmd(cmd, dry_run)

    if dry_run:
        return SimResult(exit_code=0, wall_time_s=0.0, status="DRY-RUN", log_file=log_file, trace_file=trace_file)

    # T1 outputs sim_result.json in current directory
    # We'll run from log_dir to capture it
    original_cwd = Path.cwd()

    start = time.time()
    try:
        if verbose and trace_file:
            # In verbose mode, capture stdout (trace output) to trace file
            # and stderr to log file
            with open(trace_file, 'w') as trace_fd, open(log_file, 'w') as log_fd:
                result = subprocess.run(
                    cmd,
                    stdout=trace_fd,
                    stderr=log_fd,
                    timeout=timeout,
                    cwd=str(log_dir),
                    env=env,
                )
            exit_code = result.returncode
            # Read back log content for parsing
            output = log_file.read_text() if log_file.exists() else ""
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(log_dir),
                env=env,
            )
            exit_code = result.returncode
            output = result.stdout + result.stderr
            # Save log
            log_file.write_text(output)

        # Try to read cycle count from sim_result.json
        cycles = None
        t1_result_file = log_dir / "sim_result.json"
        if t1_result_file.exists():
            try:
                import json as json_mod
                t1_result = json_mod.loads(t1_result_file.read_text())
                cycles = t1_result.get("total_cycles")
                # Rename to include workload name
                if sim_result_file != t1_result_file:
                    t1_result_file.rename(sim_result_file)
            except Exception:
                pass

        if cycles is None:
            cycles = _parse_cycles_from_log(output, "t1")

    except subprocess.TimeoutExpired as e:
        exit_code = 124
        output = (e.stdout or "") + (e.stderr or "") + "\nTIMEOUT"
        cycles = None
    wall_time = time.time() - start

    status = _parse_status_from_log(output, exit_code)

    # T1 $finish is normal termination
    if exit_code == 0 or "$finish" in output:
        if status not in ("FAIL", "ASSERT", "TIMEOUT"):
            status = "OK"

    # Parse kernel cycles from rtl-event.jsonl
    kernel_cycles = None
    if rtl_event_file.exists():
        kernel_cycles = _parse_kernel_cycles_from_t1_rtl_event(rtl_event_file)

    return SimResult(
        exit_code=exit_code,
        wall_time_s=wall_time,
        cycles=cycles,
        kernel_cycles=kernel_cycles,
        status=status,
        log_file=log_file,
        trace_file=trace_file if (trace_file and trace_file.exists()) else None,
    )


def run_vicuna_sim(
    sim_path: Path,
    workload: Path,
    *,
    max_cycles: int = 100_000_000,
    timeout: int = 600,
    extra_args: list[str] | None = None,
    dry_run: bool = False,
    log_dir: Path | None = None,
    root_dir: Path | None = None,
    verbose: bool = True,
) -> SimResult:
    """Run a Vicuna simulation.

    Vicuna uses a custom CLI format:
      Vvproc_top PROG_PATHS MEM_W MEM_SZ MEM_LATENCY EXTRA_CYCLES TRACE_FILE [WAVEFORM_FILE]

    The simulator reads VMEM format programs from PROG_PATHS file.
    UART output at 0xFF000000 goes to stdout.
    Simulation ends when program fetches address 0 (jr x0).
    """
    if not sim_path.exists():
        raise FileNotFoundError(f"Simulator not found: {sim_path}")
    if not workload.exists():
        raise FileNotFoundError(f"Workload not found: {workload}")

    # Setup log directory
    if log_dir is None:
        log_dir = (root_dir or Path.cwd()) / "sim-logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_base = log_dir / workload.stem
    log_file = Path(f"{log_base}.log")
    trace_file = log_dir / f"{workload.stem}_trace.csv"

    # Vicuna needs VMEM format - check if we need to convert
    vmem_path = workload
    if workload.suffix == ".elf":
        vmem_path = workload.with_suffix(".vmem")
        if not vmem_path.exists():
            # Convert ELF to VMEM using objcopy + srec_cat
            print(f"Converting ELF to VMEM: {vmem_path}")
            bin_path = workload.with_suffix(".bin")
            try:
                # ELF -> BIN
                subprocess.run([
                    "llvm-objcopy", "-O", "binary", str(workload), str(bin_path)
                ], check=True, capture_output=True)
                # BIN -> VMEM
                subprocess.run([
                    "srec_cat", str(bin_path), "-binary", "-offset", "0x0000",
                    "-byte-swap", "4", "-o", str(vmem_path), "-vmem"
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to convert ELF to VMEM: {e}")
            except FileNotFoundError:
                raise RuntimeError("srec_cat not found. Install srecord: apt install srecord")

    # Create PROG_PATHS file
    progs_file = log_dir / f"{workload.stem}_progs.txt"
    progs_file.write_text(str(vmem_path.resolve()) + "\n")

    # Vicuna CLI: Vvproc_top PROG_PATHS MEM_W MEM_SZ MEM_LATENCY EXTRA_CYCLES TRACE_FILE [WAVEFORM]
    # MEM_W=32, MEM_SZ=262144 (256KB), MEM_LATENCY=1, EXTRA_CYCLES=1024
    cmd = [
        str(sim_path),
        str(progs_file),
        "32",      # MEM_W
        "262144",  # MEM_SZ (256KB)
        "1",       # MEM_LATENCY
        "1024",    # EXTRA_CYCLES (cycles after program ends)
        str(trace_file),
    ]

    if extra_args:
        cmd.extend(extra_args)

    _print_cmd(cmd, dry_run)

    if dry_run:
        return SimResult(exit_code=0, wall_time_s=0.0, status="DRY-RUN", log_file=log_file)

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = result.returncode
        output = result.stdout + result.stderr
        log_file.write_text(output)
    except subprocess.TimeoutExpired as e:
        exit_code = 124
        output = (e.stdout or "") + (e.stderr or "") + "\nTIMEOUT"
    wall_time = time.time() - start

    # Parse cycles from UART output (cycles=N)
    cycles = _parse_cycles_from_log(output, "vicuna")
    status = _parse_status_from_log(output, exit_code)

    return SimResult(
        exit_code=exit_code,
        wall_time_s=wall_time,
        cycles=cycles,
        status=status,
        log_file=log_file,
        trace_file=trace_file if trace_file.exists() else None,
    )


def run_gem5_sim(
    sim_path: Path,
    workload: Path,
    *,
    mode: str = "se",  # se or fs
    cpu_type: str = "MinorCPU",
    timeout: int = 600,
    extra_args: list[str] | None = None,
    dry_run: bool = False,
    log_dir: Path | None = None,
    sim_out_dir: Path | None = None,
) -> SimResult:
    """Run a gem5 simulation."""
    if not sim_path.exists():
        raise FileNotFoundError(f"Simulator not found: {sim_path}")
    if not workload.exists():
        raise FileNotFoundError(f"Workload not found: {workload}")

    gem5_dir = sim_path.parent.parent.parent
    se_script = gem5_dir / "configs" / "deprecated" / "example" / "se.py"
    if not se_script.exists():
        se_script = gem5_dir / "configs" / "example" / "se.py"

    if log_dir is None:
        log_dir = Path.cwd() / "sim-logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{workload.stem}.log"
    if sim_out_dir is None:
        sim_out_dir = log_dir / f"{workload.stem}-gem5"
    sim_out_dir.mkdir(parents=True, exist_ok=True)

    if mode == "se":
        cmd = [
            str(sim_path),
            f"--outdir={sim_out_dir}",
            str(se_script),
            f"--cpu-type={cpu_type}",
            "--caches",
            f"--cmd={workload}",
        ]
    else:
        raise ValueError(f"gem5 mode '{mode}' not yet supported")

    if extra_args:
        cmd.extend(extra_args)

    _print_cmd(cmd, dry_run)

    if dry_run:
        return SimResult(
            exit_code=0,
            wall_time_s=0.0,
            status="DRY-RUN",
            log_file=log_file,
            sim_out_dir=sim_out_dir,
        )

    start = time.time()
    output = ""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = result.returncode
        output = result.stdout + result.stderr
        log_file.write_text(output)
    except subprocess.TimeoutExpired as e:
        exit_code = 124
        output = (e.stdout or "") + (e.stderr or "") + "\nTIMEOUT"
        log_file.write_text(output)
    wall_time = time.time() - start

    stats_path = sim_out_dir / "stats.txt"
    stats_text = stats_path.read_text() if stats_path.exists() else None
    kernel_cycles = _parse_cycles_from_log(output, "gem5")
    cycles = _parse_gem5_total_cycles(output, stats_text)
    status = _parse_status_from_log(output, exit_code)

    return SimResult(
        exit_code=exit_code,
        wall_time_s=wall_time,
        cycles=cycles,
        kernel_cycles=kernel_cycles,
        status=status,
        log_file=log_file,
        sim_out_dir=sim_out_dir,
    )


def format_result(result: SimResult, verbose: bool = False) -> str:
    """Format simulation result for display."""
    lines = []
    lines.append(f"Status:    {result.status}")
    lines.append(f"Exit code: {result.exit_code}")
    lines.append(f"Wall time: {result.wall_time_s:.2f}s")

    # Primary metric: kernel cycles (measured via mcycle CSR in harness)
    if result.kernel_cycles is not None:
        lines.append(f"Kernel:    {result.kernel_cycles:,} cycles")
    if result.cycles is not None:
        lines.append(f"Total sim: {result.cycles:,} cycles")

    # Sim speed based on total simulation cycles
    if result.cycles is not None and result.wall_time_s > 0:
        khz = result.cycles / result.wall_time_s / 1000
        lines.append(f"Sim speed: {khz:.1f} kHz")

    if result.log_file is not None:
        lines.append(f"Log file:  {result.log_file}")
    if result.trace_file is not None:
        lines.append(f"Trace:     {result.trace_file}")
    if result.sim_out_dir is not None:
        lines.append(f"Sim out:   {result.sim_out_dir}")
    # Check for .out file from spike-dasm (Saturn/Chipyard)
    if result.log_file is not None:
        out_file = result.log_file.with_suffix(".out")
        if out_file.exists() and out_file != result.trace_file:
            lines.append(f"Dasm:      {out_file}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Unified simulator runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s saturn test.elf                 Run ELF on Saturn (verbose ON by default)
  %(prog)s saturn src/kernel.c --lmul=2    Build and run .c file
  %(prog)s xiangshan test.bin              Run on XiangShan with commit trace
  %(prog)s t1 test.elf                     Run on T1 with instruction trace (RUST_LOG=TRACE)
  %(prog)s t1 test.elf --no-sim-verbose    Run on T1 without trace (faster)
  %(prog)s --list                          List available simulators

Verbose Mode (default: ON):
  - Saturn/Ara:   +verbose with spike-dasm for instruction decode
  - XiangShan:    --dump-commit-trace for commit log
  - T1:           RUST_LOG=TRACE for detailed instruction trace

  Use --no-sim-verbose to disable trace output for faster simulation.
""",
    )
    parser.add_argument("target", nargs="?", help="Simulator target (e.g., 'saturn', 'xiangshan.MinimalConfig')")
    parser.add_argument("workload", nargs="?", help="Path to ELF/binary or .c source file")
    parser.add_argument("--config-file", default="sim-configs.yaml", help="Config file path")
    parser.add_argument("--max-cycles", type=int, default=100_000_000, help="Maximum simulation cycles")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds")
    parser.add_argument("--lmul", type=int, default=1, help="LMUL value for kernel build (1,2,4,8)")
    parser.add_argument("--len", type=int, default=1000, help="LEN_1D array size for kernel build")
    parser.add_argument(
        "--use-vf",
        type=str,
        default="",
        help="Force loop vectorization with LLVM -vplan-use-vf syntax, for example fixed:4 or scalable:2",
    )
    parser.add_argument("--list", action="store_true", help="List available simulators")
    parser.add_argument("--dry-run", action="store_true", help="Print command without executing")
    parser.add_argument("--log-dir", type=str, default="sim-logs", help="Directory for simulation logs (default: sim-logs)")
    parser.add_argument("--no-sim-verbose", action="store_true",
                        help="Disable simulator verbose/trace mode (default: verbose ON)")
    parser.add_argument("--sim-verbose", action="store_true",
                        help="Enable commit trace (XiangShan: off by default since UART provides kernel cycles)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose CLI output")
    parser.add_argument("--cflags", type=str, default=None, help="Additional C flags for kernel build (e.g., -ffast-math)")
    parser.add_argument("--optflags", type=str, default=None, help="Additional opt flags for kernel build (e.g., -precise-mem-cost)")
    parser.add_argument("--sim-out-dir", type=str, default=None, help="Simulation output directory for backends that produce extra artifacts")
    parser.add_argument("--build-out-dir", type=str, default=None, help="Kernel build output directory")
    parser.add_argument("extra_args", nargs="*", help="Additional simulator arguments")

    args, unknown = parser.parse_known_args(argv)
    args.extra_args = (args.extra_args or []) + unknown
    root_dir = Path(__file__).resolve().parent
    config_path = Path(args.config_file)
    if not config_path.is_absolute():
        config_path = root_dir / config_path

    config = _load_config(config_path)

    if args.list:
        groups = _require_mapping(config.get("groups"), "groups")
        print("Available simulators:")
        for group_name in sorted(groups.keys()):
            group = _require_mapping(groups[group_name], f"groups.{group_name}")
            kind = group.get("kind", "unknown")
            desc = group.get("description", "")
            print(f"  {group_name:12} ({kind}) - {desc}")

            if kind in ("chipyard-verilator", "xiangshan"):
                configs = group.get("configs", {})
                if isinstance(configs, dict) and configs:
                    for cfg_name in sorted(configs.keys()):
                        sim_path = _find_simulator(kind, TargetSpec(group_name, cfg_name), config, root_dir)
                        status = "[OK]" if sim_path.exists() else "[NOT BUILT]"
                        print(f"    {group_name}.{cfg_name:20} {status}")
            elif kind == "t1":
                sim_path = _find_simulator(kind, TargetSpec(group_name, None), config, root_dir)
                status = "[OK]" if sim_path.exists() else "[NOT BUILT]"
                targets = group.get("targets", {})
                if isinstance(targets, dict) and targets:
                    for target_name in sorted(targets.keys()):
                        print(f"    t1.{target_name:23} {status}")
                else:
                    print(f"    t1 (default)              {status}")
        return 0

    if not args.target or not args.workload:
        parser.print_help(sys.stderr)
        return 2

    spec = _parse_target(args.target)
    group = _resolve_group(spec.group, config)
    kind = str(group.get("kind", "")).strip()

    workload = Path(args.workload)
    if not workload.is_absolute():
        workload = Path.cwd() / workload

    # If workload is a .c file, build it first
    if workload.suffix == ".c":
        build_target = GROUP_TO_BUILD_TARGET.get(spec.group, spec.group)
        workload = build_kernel(
            root_dir,
            workload,
            build_target,
            lmul=args.lmul,
            len_1d=args.len,
            use_vf=args.use_vf,
            cflags=args.cflags,
            optflags=args.optflags,
            build_out_dir=Path(args.build_out_dir) if args.build_out_dir else None,
        )
        print("-" * 40)

    sim_path = _find_simulator(kind, spec, config, root_dir)

    print(f"Simulator: {sim_path}")
    print(f"Workload:  {workload}")
    print(f"Max cycles: {args.max_cycles:,}")
    print(f"Timeout:   {args.timeout}s")
    print("-" * 40)

    log_dir = Path(args.log_dir)
    if not log_dir.is_absolute():
        log_dir = root_dir / log_dir

    sim_out_dir = Path(args.sim_out_dir) if args.sim_out_dir else None
    if sim_out_dir is not None and not sim_out_dir.is_absolute():
        sim_out_dir = root_dir / sim_out_dir

    if kind == "chipyard-verilator":
        result = run_chipyard_sim(
            sim_path, workload,
            max_cycles=args.max_cycles,
            timeout=args.timeout,
            extra_args=args.extra_args or None,
            dry_run=args.dry_run,
            log_dir=log_dir,
            root_dir=root_dir,
            verbose=not args.no_sim_verbose,
        )
    elif kind == "xiangshan":
        # XiangShan: kernel cycles come from UART output, not commit trace.
        # Commit trace (verbose) is only needed for waveform/debug analysis.
        # Use --sim-verbose to explicitly enable commit trace.
        xs_verbose = hasattr(args, 'sim_verbose') and args.sim_verbose
        result = run_xiangshan_sim(
            sim_path, workload,
            max_cycles=args.max_cycles,
            timeout=args.timeout,
            extra_args=args.extra_args or None,
            dry_run=args.dry_run,
            log_dir=log_dir,
            root_dir=root_dir,
            verbose=xs_verbose,
        )
    elif kind == "t1":
        result = run_t1_sim(
            sim_path, workload,
            max_cycles=args.max_cycles,
            timeout=args.timeout,
            extra_args=args.extra_args or None,
            dry_run=args.dry_run,
            log_dir=log_dir,
            root_dir=root_dir,
            verbose=not args.no_sim_verbose,
        )
    elif kind == "gem5":
        result = run_gem5_sim(
            sim_path, workload,
            timeout=args.timeout,
            extra_args=args.extra_args or None,
            dry_run=args.dry_run,
            log_dir=log_dir,
            sim_out_dir=sim_out_dir,
        )
    elif kind == "vicuna":
        result = run_vicuna_sim(
            sim_path, workload,
            max_cycles=args.max_cycles,
            timeout=args.timeout,
            extra_args=args.extra_args or None,
            dry_run=args.dry_run,
            log_dir=log_dir,
            root_dir=root_dir,
            verbose=not args.no_sim_verbose,
        )
    else:
        print(f"error: unsupported kind '{kind}' for group '{spec.group}'", file=sys.stderr)
        return 1

    if args.dry_run:
        return 0

    print(format_result(result, verbose=args.verbose))

    return 0 if result.status in ("OK", "PASS") else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
