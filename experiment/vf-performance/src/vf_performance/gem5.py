"""gem5 execution helpers and parsers."""

from __future__ import annotations

import re
import shlex
import subprocess
import time
from pathlib import Path


def parse_tsvc_kernel_cycles(text: str) -> int | None:
    """Parse the first TSVC cycle measurement line."""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("Loop"):
            continue
        match = re.match(r"^(\d+)\s+[-+0-9.eE]+$", line)
        if match:
            return int(match.group(1))
    return None


def parse_gem5_total_cycles(output_text: str, stats_text: str | None = None) -> int | None:
    patterns = [
        r"system\.cpu\.numCycles\s+(\d+)",
        r"simTicks\s+(\d+)",
        r"final_tick=(\d+)",
        r"Exiting @ tick (\d+)",
    ]
    search_space = "\n".join(part for part in (stats_text, output_text) if part)
    for pattern in patterns:
        match = re.search(pattern, search_space)
        if match:
            return int(match.group(1))
    return None


def run_gem5(
    gem5_path: Path,
    elf_path: Path,
    out_dir: Path,
    *,
    cpu_type: str = "MinorCPU",
    timeout: int = 600,
) -> tuple[str, str, float, int | None]:
    """Run gem5 in SE mode and return output, command, wall time, total cycles."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(gem5_path),
        f"--outdir={out_dir}",
        str(gem5_path.parent.parent.parent / "configs" / "example" / "se.py"),
        f"--cpu-type={cpu_type}",
        f"--cmd={elf_path}",
    ]
    command_str = shlex.join(cmd)

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + (exc.stderr or "")) + "\nTIMEOUT"
        result = None
    wall_time = time.time() - start

    stats_path = out_dir / "stats.txt"
    stats_text = stats_path.read_text() if stats_path.exists() else None
    total_cycles = parse_gem5_total_cycles(output, stats_text)
    status = "OK"
    if result is None:
        status = "TIMEOUT"
    elif result.returncode != 0:
        status = f"EXIT:{result.returncode}"
    if "TIMEOUT" in output:
        status = "TIMEOUT"

    return status, output, wall_time, total_cycles
