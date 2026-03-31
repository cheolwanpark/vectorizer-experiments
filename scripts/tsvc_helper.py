#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


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


def fail(message: str) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(1)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_tsvc_dir() -> Path:
    return repo_root() / "benchmarks" / "MultiSource" / "Benchmarks" / "TSVC"


def parse_func_calls(tsvc_dir: Path) -> dict[str, dict[str, str]]:
    tsc_inc = tsvc_dir / "tsc.inc"
    text = tsc_inc.read_text(encoding="utf-8")
    main_pos = text.find("int main(")
    if main_pos == -1:
        fail(f"could not find main() in {tsc_inc}")

    calls: dict[str, dict[str, str]] = {}
    main_text = text[main_pos:]
    block_re = re.compile(r"#if TESTS & ([A-Z_]+)\n(.*?)#endif", re.S)
    call_re = re.compile(r"^\s*(s\d{3,4}\s*\(.*\);)\s*$")
    func_re = re.compile(r"^(s\d{3,4})\s*\(")

    for category, block in block_re.findall(main_text):
        for line in block.splitlines():
            match = call_re.match(line)
            if not match:
                continue
            call_expr = match.group(1).strip()
            func_match = func_re.match(call_expr)
            if not func_match:
                continue
            func = func_match.group(1)
            if func in calls and calls[func]["category"] != category:
                fail(f"function {func} appears in multiple categories")
            calls[func] = {"category": category, "call_expr": call_expr}

    if not calls:
        fail(f"could not parse TSVC calls from {tsc_inc}")
    return calls


def resolve_metadata(tsvc_dir: Path, func: str, variant: str) -> dict[str, str]:
    if not re.fullmatch(r"s\d{3,4}", func):
        fail(f"invalid function name: {func}")
    if variant not in {"dbl", "flt"}:
        fail(f"invalid TYPE: {variant}")

    calls = parse_func_calls(tsvc_dir)
    if func not in calls:
        fail(f"unknown TSVC function: {func}")

    category = calls[func]["category"]
    call_expr = calls[func]["call_expr"]
    benchmark_dir = tsvc_dir / f"{CATEGORY_TO_DIR[category]}-{variant}"

    return {
        "category": category,
        "call_expr": call_expr,
        "benchmark_dir": str(benchmark_dir),
        "source_path": str(benchmark_dir / "tsc.c"),
        "dummy_path": str(benchmark_dir / "dummy.c"),
    }


def sanitize_ir_text(text: str, triple: str | None, datalayout: str | None) -> str:
    if triple:
        text, count = re.subn(
            r'^target triple = "[^"]*"$',
            f'target triple = "{triple}"',
            text,
            count=1,
            flags=re.M,
        )
        if count == 0:
            fail("could not find target triple in IR")

    if datalayout:
        text, count = re.subn(
            r'^target datalayout = "[^"]*"$',
            f'target datalayout = "{datalayout}"',
            text,
            count=1,
            flags=re.M,
        )
        if count == 0:
            fail("could not find target datalayout in IR")

    text = re.sub(r'\s+"target-cpu"="[^"]*"', "", text)
    text = re.sub(r'\s+"target-features"="[^"]*"', "", text)
    return text


def handle_metadata(args: argparse.Namespace) -> None:
    data = resolve_metadata(Path(args.tsvc_dir), args.function, args.type)
    print(data[args.field])


def handle_sanitize_ir(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_path = Path(args.output)
    text = input_path.read_text(encoding="utf-8")
    text = sanitize_ir_text(text, args.triple, args.datalayout)
    output_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    metadata = subparsers.add_parser("metadata")
    metadata.add_argument("--tsvc-dir", default=str(default_tsvc_dir()))
    metadata.add_argument("--func", dest="function", required=True)
    metadata.add_argument("--type", required=True)
    metadata.add_argument(
        "--field",
        choices=["benchmark_dir", "call_expr", "category", "dummy_path", "source_path"],
        required=True,
    )
    metadata.set_defaults(handler=handle_metadata)

    sanitize_ir = subparsers.add_parser("sanitize-ir")
    sanitize_ir.add_argument("--input", required=True)
    sanitize_ir.add_argument("--output", required=True)
    sanitize_ir.add_argument("--triple")
    sanitize_ir.add_argument("--datalayout")
    sanitize_ir.set_defaults(handler=handle_sanitize_ir)

    args = parser.parse_args()
    handler = args.handler
    del args.handler
    handler(args)


if __name__ == "__main__":
    main()
