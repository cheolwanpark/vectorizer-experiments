from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path


RUN_SRC_ROOT = Path("emulator") / "run" / "src"
GENERATED_RUN_SRC_ROOT = RUN_SRC_ROOT / "generated"
TSVC_LOOP_ROOT = Path("emulator") / "benchmarks" / "TSVC_2" / "src" / "loops"
GENERATED_MINIMAL_MARKER = "TSVC_EMULATE_GENERATED"
KERNEL_FUNCTION_NAME = "kernel"

IGNORE_LINE_PATTERNS = (
    re.compile(r"^\s*initialise_arrays\s*\(__func__\);\s*$"),
    re.compile(r"^\s*gettimeofday\s*\(&func_args->t[12], NULL\);\s*$"),
    re.compile(r"^\s*dummy\s*\(.*\);\s*$"),
    re.compile(r"^\s*return\s+.*;\s*$"),
)
OUTER_LOOP_RE = re.compile(r"^\s*for\s*\(\s*int\s+nl\s*=.*\)\s*\{\s*$")
ARG_STRUCT_RE = re.compile(
    r"^(?P<indent>\s*)struct\s*\{.*\}\s*\*\s*(?P<name>[A-Za-z_]\w*)\s*=\s*func_args->arg_info;\s*$"
)
ARG_DEREF_RE = re.compile(
    r"^(?P<indent>\s*)(?P<lhs>.+?=\s*)\*\([^)]*\)\s*func_args->arg_info\s*;\s*$"
)
ARG_DIRECT_RE = re.compile(
    r"^(?P<indent>\s*)(?P<lhs>.+?=\s*)func_args->arg_info\s*;\s*$"
)
ARGS_ASSIGN_RE = re.compile(r"^\s*(?P<var>[A-Za-z_]\w*)\.(?P<field>\w+)\s*=\s*(?P<expr>.+);\s*$")
RETURN_EXPR_RE = re.compile(r"^\s*return\s+(?P<expr>.+);\s*$")


@dataclass(frozen=True)
class BenchmarkSource:
    bench: str
    source_path: Path
    source_kind: str
    function_name: str = KERNEL_FUNCTION_NAME


@dataclass(frozen=True)
class ArgInfoSpec:
    kind: str
    expr: str | None = None
    fields: dict[str, str] | None = None


class ConversionError(RuntimeError):
    pass


def manual_source_path(root: Path, bench: str) -> Path:
    return root / RUN_SRC_ROOT / f"{bench}.c"


def generated_source_path(root: Path, bench: str) -> Path:
    return root / GENERATED_RUN_SRC_ROOT / f"{bench}.c"


def loop_source_path(root: Path, bench: str) -> Path:
    return root / TSVC_LOOP_ROOT / f"{bench}.c"


def discover_catalog_benches(root: Path) -> list[str]:
    manual = {path.stem for path in (root / RUN_SRC_ROOT).glob("s*.c")}
    loops = {path.stem for path in (root / TSVC_LOOP_ROOT).glob("s*.c")}
    return sorted(manual | loops)


def resolve_benchmark_source(root: Path, bench: str) -> BenchmarkSource:
    manual = manual_source_path(root, bench)
    if manual.exists():
        return BenchmarkSource(bench=bench, source_path=manual, source_kind="manual")

    loop = loop_source_path(root, bench)
    if not loop.exists():
        raise FileNotFoundError(f"simplified benchmark source not found for {bench}")

    generated = ensure_generated_source(root, bench)
    return BenchmarkSource(bench=bench, source_path=generated, source_kind="generated")


def ensure_generated_source(root: Path, bench: str) -> Path:
    source = loop_source_path(root, bench)
    if not source.exists():
        raise FileNotFoundError(f"TSVC loop source not found: {source}")

    generated = generated_source_path(root, bench)
    generated.parent.mkdir(parents=True, exist_ok=True)
    generated_text = convert_loop_source_to_kernel(bench, source.read_text(encoding="utf-8"))
    if not generated.exists() or generated.read_text(encoding="utf-8") != generated_text:
        generated.write_text(generated_text, encoding="utf-8")
    return generated


def convert_loop_source_to_kernel(bench: str, source_text: str) -> str:
    loop_body = _extract_function_body(
        source_text,
        re.compile(rf"\breal_t\s+{re.escape(bench)}\s*\(\s*struct\s+args_t\s*\*\s*func_args\s*\)")
    )
    prepare_body = _extract_function_body(
        source_text,
        re.compile(r"\bvoid\s*\*\s*tsvc_prepare_args\s*\(\s*void\s*\)")
    )
    arg_info = _parse_prepare_args(prepare_body)

    outer_stripped = _strip_outer_loop(loop_body.splitlines())
    transformed = _rewrite_arg_info_lines(outer_stripped, arg_info)
    filtered = _filter_runtime_lines(transformed)
    body_text = "\n".join(filtered).strip()
    if "func_args->" in body_text:
        raise ConversionError(f"{bench}: unsupported func_args usage in generated kernel")

    lines = [
        f"/* {GENERATED_MINIMAL_MARKER}: {bench} */",
        '#include "common.h"',
        "",
        "extern int *tsvc_ip;",
        "extern int tsvc_n1;",
        "extern int tsvc_n3;",
        "extern real_t tsvc_s1;",
        "extern real_t tsvc_s2;",
        "",
        "void kernel(void) {",
    ]
    if body_text:
        lines.extend(_indent_block(body_text.splitlines(), "    "))
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def _extract_function_body(source_text: str, signature_re: re.Pattern[str]) -> str:
    match = signature_re.search(source_text)
    if match is None:
        raise ConversionError(f"function matching {signature_re.pattern!r} not found")

    brace_start = source_text.find("{", match.end())
    if brace_start == -1:
        raise ConversionError("function body start not found")

    depth = 0
    for index in range(brace_start, len(source_text)):
        char = source_text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source_text[brace_start + 1:index]

    raise ConversionError("function body end not found")


def _parse_prepare_args(body_text: str) -> ArgInfoSpec:
    assignments: dict[str, dict[str, str]] = {}
    return_expr: str | None = None

    for line in body_text.splitlines():
        assign_match = ARGS_ASSIGN_RE.match(line)
        if assign_match:
            assignments.setdefault(assign_match.group("var"), {})[assign_match.group("field")] = assign_match.group("expr").strip()
            continue

        return_match = RETURN_EXPR_RE.match(line)
        if return_match:
            return_expr = return_match.group("expr").strip().rstrip(";")

    if return_expr is None or return_expr == "NULL":
        return ArgInfoSpec(kind="none")

    if return_expr.startswith("&"):
        variable = return_expr[1:]
        if variable in assignments:
            return ArgInfoSpec(kind="struct", fields=assignments[variable])

    return ArgInfoSpec(kind="direct", expr=return_expr)


def _strip_outer_loop(lines: list[str]) -> list[str]:
    outer_start = None
    for index, line in enumerate(lines):
        if OUTER_LOOP_RE.match(line):
            outer_start = index
            break

    if outer_start is None:
        return lines

    depth = 0
    outer_end = None
    for index in range(outer_start, len(lines)):
        depth += lines[index].count("{")
        depth -= lines[index].count("}")
        if depth == 0:
            outer_end = index
            break

    if outer_end is None:
        raise ConversionError("outer nl loop block is not balanced")

    outer_body = _dedent_block(lines[outer_start + 1:outer_end])
    return lines[:outer_start] + outer_body + lines[outer_end + 1:]


def _dedent_block(lines: list[str]) -> list[str]:
    indents = [
        len(line) - len(line.lstrip(" "))
        for line in lines
        if line.strip()
    ]
    if not indents:
        return lines
    shared_indent = min(indents)
    if shared_indent <= 0:
        return lines
    return [line[shared_indent:] if len(line) >= shared_indent else line for line in lines]


def _indent_block(lines: list[str], indent: str) -> list[str]:
    return [f"{indent}{line}" if line else "" for line in lines]


def _rewrite_arg_info_lines(lines: list[str], arg_info: ArgInfoSpec) -> list[str]:
    rewritten: list[str] = []
    struct_var_fields: dict[str, dict[str, str]] = {}

    for line in lines:
        struct_match = ARG_STRUCT_RE.match(line)
        if struct_match is not None:
            if arg_info.kind != "struct" or not arg_info.fields:
                raise ConversionError("struct arg_info use does not match tsvc_prepare_args")
            struct_var_fields[struct_match.group("name")] = arg_info.fields
            continue

        updated = line
        for var_name, fields in struct_var_fields.items():
            for field_name, expr in fields.items():
                updated = re.sub(
                    rf"\b{re.escape(var_name)}->{re.escape(field_name)}\b",
                    expr,
                    updated,
                )

        if "func_args->arg_info" in updated:
            if arg_info.kind == "none":
                updated = updated.replace("func_args->arg_info", "0")
            else:
                deref_match = ARG_DEREF_RE.match(updated)
                if deref_match is not None:
                    direct_expr = _direct_value_expr(arg_info)
                    updated = f"{deref_match.group('indent')}{deref_match.group('lhs')}{direct_expr};"
                else:
                    direct_match = ARG_DIRECT_RE.match(updated)
                    if direct_match is not None:
                        direct_expr = _direct_pointer_expr(arg_info)
                        updated = f"{direct_match.group('indent')}{direct_match.group('lhs')}{direct_expr};"

        rewritten.append(updated)

    return rewritten


def _direct_value_expr(arg_info: ArgInfoSpec) -> str:
    if arg_info.kind == "none":
        return "0"
    if arg_info.kind != "direct" or arg_info.expr is None:
        raise ConversionError("cannot rewrite scalar arg_info access from structured args")
    return arg_info.expr[1:] if arg_info.expr.startswith("&") else arg_info.expr


def _direct_pointer_expr(arg_info: ArgInfoSpec) -> str:
    if arg_info.kind == "none":
        return "0"
    if arg_info.kind != "direct" or arg_info.expr is None:
        raise ConversionError("cannot rewrite pointer arg_info access from structured args")
    return arg_info.expr


def _filter_runtime_lines(lines: list[str]) -> list[str]:
    filtered: list[str] = []
    for line in lines:
        if any(pattern.match(line) for pattern in IGNORE_LINE_PATTERNS):
            continue
        filtered.append(line.rstrip())
    return filtered
