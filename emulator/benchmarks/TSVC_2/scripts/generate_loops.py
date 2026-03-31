#!/usr/bin/env python3
"""
Split the monolithic TSVC source into per-loop files that can be built
individually alongside the common data/initialisation code.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
TSVC = ROOT / "src" / "tsvc.c"
OUT_DIR = ROOT / "src" / "loops"


def parse_runs(text: str) -> List[Tuple[str, str]]:
    runs: List[Tuple[str, str]] = []
    for line in text.splitlines():
        m = re.search(r"RUN\(([^,]+),\s*(.+)\);", line)
        if m:
            runs.append((m.group(1).strip(), m.group(2).strip()))
    return runs


def extract_block(text: str, start_brace: int) -> int:
    depth = 0
    for idx in range(start_brace, len(text)):
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return idx + 1
    raise ValueError("Unbalanced braces while extracting function")


def extract_function(text: str, name: str) -> str:
    pattern = re.compile(rf"[A-Za-z_][\w\s\*]*\b{re.escape(name)}\s*\([^)]*\)\s*\{{", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Could not find function {name}")

    brace_start = text.find("{", match.start())
    if brace_start == -1:
        raise ValueError(f"Could not find opening brace for {name}")

    end = extract_block(text, brace_start)
    return text[match.start():end].strip() + "\n"


def render_prepare_fn(loop: str) -> str:
    common = {
        "s162",
        "s171",
        "s175",
        "s318",
    }
    n1_n3_struct = {"s122", "s172"}
    s1_only = {"s272", "s2710", "s332", "vpvts"}
    ip_direct = {"s353", "s491", "s4113", "s4115", "vag", "vas"}

    if loop in n1_n3_struct:
        body = """\
static struct {int a; int b;} args;
args.a = tsvc_n1;
args.b = tsvc_n3;
return &args;"""
    elif loop in common:
        body = "return &tsvc_n1;"
    elif loop == "s174":
        body = "static struct {int a;} args = {LEN_1D/2};\nreturn &args;"
    elif loop == "s242":
        body = """\
static struct {real_t a; real_t b;} args;
args.a = tsvc_s1;
args.b = tsvc_s2;
return &args;"""
    elif loop in s1_only:
        body = "return &tsvc_s1;"
    elif loop == "s4112":
        body = """\
static struct {int *a; real_t b;} args;
args.a = tsvc_ip;
args.b = tsvc_s1;
return &args;"""
    elif loop == "s4114":
        body = """\
static struct {int *a; int b;} args;
args.a = tsvc_ip;
args.b = tsvc_n1;
return &args;"""
    elif loop == "s4116":
        body = """\
static struct {int *a; int b; int c;} args;
args.a = tsvc_ip;
args.b = LEN_2D/2;
args.c = tsvc_n1;
return &args;"""
    elif loop in ip_direct:
        body = "return tsvc_ip;"
    else:
        body = "return NULL;"

    return "void *tsvc_prepare_args(void) {\n" + textwrap.indent(body, "    ") + "\n}\n"


def needs_helper(src: str, helper: str) -> bool:
    return f"{helper}(" in src


def assemble_file(
    loop: str,
    func_src: str,
    helpers: Iterable[str],
) -> str:
    header = textwrap.dedent(
        """\
        #include <math.h>
        #include "../common.h"
        #include "../array_defs.h"
        #include "../single_support.h"
        #include "../tsvc_measure.h"

        """
    )

    pieces: List[str] = [header]
    pieces.extend(h for h in helpers if h)
    if pieces[-1].strip():
        pieces.append("\n")
    pieces.append(func_src.strip() + "\n\n")
    pieces.append(f'const char *tsvc_loop_name(void) {{ return "{loop}"; }}\n\n')
    pieces.append(f"real_t tsvc_entry(struct args_t *func_args) {{ return {loop}(func_args); }}\n\n")
    pieces.append(render_prepare_fn(loop))
    return "".join(pieces)


def main() -> None:
    text = TSVC.read_text()
    runs = parse_runs(text)
    helpers_src: Dict[str, str] = {
        name: extract_function(text, name) for name in ("s151s", "s152s", "s471s")
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in OUT_DIR.glob("*.c"):
        path.unlink()

    for loop, _ in runs:
        func_src = extract_function(text, f"{loop}")

        helper_list: List[str] = []
        if needs_helper(func_src, "s151s"):
            helper_list.append(helpers_src["s151s"])
        if needs_helper(func_src, "s152s"):
            helper_list.append(helpers_src["s152s"])
        if needs_helper(func_src, "s471s"):
            helper_list.append(helpers_src["s471s"])

        content = assemble_file(loop, func_src, helper_list)
        (OUT_DIR / f"{loop}.c").write_text(content)

    print(f"Wrote {len(runs)} loop files to {OUT_DIR}")


if __name__ == "__main__":
    main()
