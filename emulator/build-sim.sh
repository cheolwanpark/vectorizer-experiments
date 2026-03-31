#!/usr/bin/env python3
"""
Unified simulator build wrapper.

Examples:
  ./build-sim.sh xiangshan.MinimalConfig
  ./build-sim.sh saturn.REFV512D128RocketConfig
  ./build-sim.sh gem5
  ./build-sim.sh t1            # uses default target from sim-configs.yaml

Config:
  - Defaults to `./sim-configs.yaml`.
  - Accepts YAML or JSON; JSON is also valid YAML 1.2 (so you can keep the file as .yaml).
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TargetSpec:
    group: str
    config: str | None


def _nproc() -> int:
    for key in ("NPROC",):
        value = os.environ.get(key)
        if value:
            try:
                n = int(value)
                if n > 0:
                    return n
            except ValueError:
                pass
    try:
        import multiprocessing

        return max(1, multiprocessing.cpu_count())
    except Exception:
        return 1


def _default_jobs(nproc: int) -> int:
    value = os.environ.get("JOBS")
    if value:
        try:
            return max(1, int(value))
        except ValueError:
            pass
    return max(1, nproc // 2)


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

    # Prefer JSON first. JSON is valid YAML 1.2, so using JSON here lets us avoid PyYAML dependency.
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("config root must be an object")
            return data
        except json.JSONDecodeError:
            # If the user wrote YAML flow-style with comments/trailing commas, it can start with '{'
            # while being invalid JSON. Fall back to YAML if available.
            pass

    # Fall back to YAML if user wrote it as YAML.
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            f"Failed to parse {path}.\n"
            f"- If you want YAML (comments, flow style, etc.), install PyYAML: python3 -m pip install pyyaml\n"
            f"- Otherwise keep it strict JSON (JSON is also valid YAML 1.2)\n"
        ) from exc

    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("config root must be a mapping/object")
    return data


def _require_mapping(obj: Any, where: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError(f"{where} must be an object/mapping")
    return obj


def _render_bash_script(lines: list[str], root_dir: Path | None = None) -> str:
    # Use bash -lc to support `source` and robust shell behavior in one place.
    preamble = "set -euo pipefail\n"
    # Source env.sh if it exists to set up PATH
    if root_dir:
        env_sh = root_dir / "env.sh"
        if env_sh.exists():
            preamble += f"source {shlex.quote(str(env_sh))} 2>/dev/null || true\n"
    return preamble + "\n".join(lines) + "\n"


def _run_bash(script: str, cwd: Path, dry_run: bool) -> None:
    if dry_run:
        sys.stdout.write(f"# cwd: {cwd}\n")
        sys.stdout.write(script)
        return
    subprocess.run(["bash", "-lc", script], cwd=str(cwd), check=True)


def _resolve_group(group_name: str, config: dict[str, Any]) -> dict[str, Any]:
    groups = _require_mapping(config.get("groups"), "groups")
    group = groups.get(group_name)
    if group is None:
        known = ", ".join(sorted(groups.keys()))
        raise ValueError(f"unknown group '{group_name}' (known: {known})")
    return _require_mapping(group, f"groups.{group_name}")


def _resolve_default_config(group_name: str, group: dict[str, Any], configs: dict[str, Any]) -> str | None:
    explicit = str(group.get("default_config", "")).strip()
    if explicit:
        return explicit
    if "default" in configs:
        return "default"
    if group_name in configs:
        return group_name
    if len(configs) == 1:
        return next(iter(configs.keys()))
    return None


def _chipyard_make_script(
    *,
    root_dir: Path,
    chipyard_dir: Path,
    config_name: str,
    jobs: int,
    verilator_threads: int,
    group_name: str = "",
) -> list[str]:
    # Ara requires USE_ARA=1 to include proper include paths
    extra_vars = ""
    if group_name == "ara":
        extra_vars = "USE_ARA=1 "
    return [
        f"pushd {shlex.quote(str(chipyard_dir / 'sims' / 'verilator'))}",
        f"{extra_vars}make -j{jobs} CONFIG={shlex.quote(config_name)} "
        f"VERILATOR_THREADS={verilator_threads} LOADMEM=1 NUMACTL=1",
        "popd"
    ]


def _xiangshan_make_script(*, root_dir: Path, xiangshan_dir: Path, config_name: str, jobs: int, emu_threads: int) -> list[str]:
    # XiangShan Makefile doesn't track CONFIG changes - it only checks if SimTop.sv exists.
    # We track the last built config and clean if it changed.
    marker_file = xiangshan_dir / "build" / ".last-sim-config"
    return [
        f"cd {shlex.quote(str(xiangshan_dir))}",
        # Ensure NEMU/AM env vars are set for difftest
        f"export NEMU_HOME={shlex.quote(str(root_dir / 'third-party' / 'NEMU'))}",
        f"export AM_HOME={shlex.quote(str(root_dir / 'third-party' / 'nexus-am'))}",
        f"export NOOP_HOME={shlex.quote(str(xiangshan_dir))}",
        # Initialize submodules if needed
        "make init 2>/dev/null || true",
        # Check if config changed and clean RTL if needed
        f"MARKER={shlex.quote(str(marker_file))}",
        f"EXPECTED_CONFIG={shlex.quote(config_name)}",
        'if [ -f "$MARKER" ]; then',
        '  LAST_CONFIG=$(cat "$MARKER")',
        '  if [ "$LAST_CONFIG" != "$EXPECTED_CONFIG" ]; then',
        '    echo "[xiangshan] Config changed from $LAST_CONFIG to $EXPECTED_CONFIG, cleaning RTL..."',
        '    rm -rf ./build/rtl ./build/verilator-compile ./build/emu',
        "  fi",
        "elif [ -d ./build/rtl ]; then",
        '  echo "[xiangshan] Existing RTL found without config marker, cleaning for fresh build..."',
        "  rm -rf ./build/rtl ./build/verilator-compile ./build/emu",
        "fi",
        # Build the emulator
        f"make emu -j{jobs} CONFIG={shlex.quote(config_name)} EMU_THREADS={emu_threads}",
        # Record the config used
        'mkdir -p "$(dirname "$MARKER")"',
        'echo "$EXPECTED_CONFIG" > "$MARKER"',
    ]


def _t1_build_script(*, t1_dir: Path, flake_target: str, jobs: int) -> list[str]:
    return [
        "rm -rf /homeless-shelter 2>/dev/null || true",
        f"cd {shlex.quote(str(t1_dir))}",
        "nix build "
        + shlex.quote(flake_target)
        + " --extra-experimental-features "
        + shlex.quote("nix-command flakes")
        + " --option sandbox false "
        + f"-j{jobs}",
    ]


def _gem5_build_script(*, root_dir: Path, jobs: int) -> list[str]:
    return [
        f"bash {shlex.quote(str(root_dir / 'build_gem5.sh'))} -j {jobs}"
    ]


def _list_config(config: dict[str, Any]) -> int:
    groups = _require_mapping(config.get("groups"), "groups")
    for group_name in sorted(groups.keys()):
        group = _require_mapping(groups[group_name], f"groups.{group_name}")
        kind = group.get("kind", "unknown")
        print(f"{group_name} ({kind})")
        if kind in ("chipyard-verilator", "xiangshan"):
            configs = group.get("configs", {})
            if isinstance(configs, dict) and configs:
                for name in sorted(configs.keys()):
                    print(f"  - {group_name}.{name}")
        if kind == "t1":
            targets = group.get("targets", {})
            if isinstance(targets, dict) and targets:
                for name in sorted(targets.keys()):
                    print(f"  - t1.{name}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("targets", nargs="*", help="Targets like 'xiangshan.MinimalConfig' or 'gem5'")
    parser.add_argument("--config-file", default="sim-configs.yaml", help="Config file path (default: sim-configs.yaml)")
    parser.add_argument("-j", "--jobs", type=int, default=None, help="Parallel jobs (default: nproc/2)")
    parser.add_argument("--dry-run", action="store_true", help="Print resolved shell scripts without executing")
    parser.add_argument("--list", action="store_true", help="List available groups/configs from config file")
    args = parser.parse_args(argv)

    root_dir = Path(__file__).resolve().parent
    config_path = (Path(args.config_file).resolve() if os.path.isabs(args.config_file) else (root_dir / args.config_file))
    config = _load_config(config_path)

    if args.list:
        return _list_config(config)

    nproc = _nproc()
    jobs = args.jobs if args.jobs and args.jobs > 0 else _default_jobs(nproc)

    defaults = _require_mapping(config.get("defaults", {}), "defaults")
    default_targets = defaults.get("default_targets", [])
    if not args.targets:
        if isinstance(default_targets, list) and default_targets:
            args.targets = [str(x) for x in default_targets]
        else:
            parser.print_help(sys.stderr)
            return 2

    specs = [_parse_target(t) for t in args.targets]

    chipyard_dir = Path(defaults.get("chipyard_dir", str(root_dir / "chipyard"))).expanduser()
    if not chipyard_dir.is_absolute():
        chipyard_dir = (root_dir / chipyard_dir).resolve()
    xiangshan_dir = Path(defaults.get("xiangshan_dir", str(root_dir / "XiangShan"))).expanduser()
    if not xiangshan_dir.is_absolute():
        xiangshan_dir = (root_dir / xiangshan_dir).resolve()
    t1_dir = Path(defaults.get("t1_dir", str(root_dir / "t1-micro58ae"))).expanduser()
    if not t1_dir.is_absolute():
        t1_dir = (root_dir / t1_dir).resolve()

    emu_threads = int(os.environ.get("EMU_THREADS", str(defaults.get("emu_threads", 8))))
    verilator_threads_cfg = int(defaults.get("verilator_threads", 0))
    verilator_threads_default = max(1, nproc // 2) if verilator_threads_cfg <= 0 else verilator_threads_cfg
    verilator_threads = int(os.environ.get("VERILATOR_THREADS", str(verilator_threads_default)))
    for spec in specs:
        group = _resolve_group(spec.group, config)
        kind = str(group.get("kind", "")).strip()

        if kind == "gem5":
            print("gem5")
            if spec.config:
                raise ValueError("gem5 does not take a config suffix (use: gem5)")
            script_lines = _gem5_build_script(root_dir=root_dir, jobs=jobs)
            _run_bash(_render_bash_script(script_lines, root_dir=root_dir), cwd=root_dir, dry_run=args.dry_run)
            continue

        if kind == "chipyard-verilator":
            configs = group.get("configs", {})
            if not isinstance(configs, dict):
                raise ValueError(f"groups.{spec.group}.configs must be a mapping")

            config_name = spec.config or _resolve_default_config(spec.group, group, configs)
            if not config_name:
                raise ValueError(f"{spec.group} requires a config (e.g. {spec.group}.<ConfigName>)")

            resolved = configs.get(config_name, None)
            if resolved is None:
                known = ", ".join(sorted(configs.keys()))
                raise ValueError(f"unknown config '{spec.group}.{config_name}' (known: {known})")
            resolved_name = resolved if isinstance(resolved, str) else config_name

            script_lines = _chipyard_make_script(
                root_dir=root_dir,
                chipyard_dir=chipyard_dir,
                config_name=resolved_name,
                jobs=jobs,
                verilator_threads=verilator_threads,
                group_name=spec.group,
            )
            _run_bash(_render_bash_script(script_lines, root_dir=root_dir), cwd=root_dir, dry_run=args.dry_run)
            continue

        if kind == "xiangshan":
            configs = group.get("configs", {})
            if not isinstance(configs, dict):
                raise ValueError(f"groups.{spec.group}.configs must be a mapping")
            config_name = spec.config or str(group.get("default_config", "")).strip()
            if not config_name:
                raise ValueError("xiangshan requires a config (e.g. xiangshan.MinimalConfig)")
            if config_name not in configs:
                known = ", ".join(sorted(configs.keys()))
                raise ValueError(f"unknown config 'xiangshan.{config_name}' (known: {known})")

            script_lines = _xiangshan_make_script(
                root_dir=root_dir,
                xiangshan_dir=xiangshan_dir,
                config_name=config_name,
                jobs=jobs,
                emu_threads=emu_threads,
            )
            _run_bash(_render_bash_script(script_lines, root_dir=root_dir), cwd=root_dir, dry_run=args.dry_run)
            continue

        if kind == "t1":
            targets = group.get("targets", {})
            if not isinstance(targets, dict):
                raise ValueError("groups.t1.targets must be a mapping")
            if spec.config:
                flake_target = targets.get(spec.config)
                if not isinstance(flake_target, str) or not flake_target.strip():
                    known = ", ".join(sorted(targets.keys()))
                    raise ValueError(f"unknown target 't1.{spec.config}' (known: {known})")
            else:
                flake_target = str(group.get("default_target", "")).strip()
                if not flake_target:
                    raise ValueError("t1 requires default_target or an explicit t1.<name> mapping")

            script_lines = _t1_build_script(t1_dir=t1_dir, flake_target=flake_target, jobs=jobs)
            _run_bash(_render_bash_script(script_lines, root_dir=root_dir), cwd=root_dir, dry_run=args.dry_run)
            continue

        raise ValueError(f"unsupported kind '{kind}' for group '{spec.group}'")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
