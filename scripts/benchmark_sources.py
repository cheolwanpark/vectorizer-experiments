from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any


RUN_SRC_ROOT = Path("emulator") / "run" / "src"
GENERATED_RUN_SRC_ROOT = RUN_SRC_ROOT / "generated"
TSVC_RUN_SRC_ROOT = RUN_SRC_ROOT / "tsvc"
TSVC_LOOP_ROOT = Path("emulator") / "benchmarks" / "TSVC_2" / "src" / "loops"
GENERATED_MINIMAL_MARKER = "TSVC_EMULATE_GENERATED"
KERNEL_FUNCTION_NAME = "kernel"
SUPPORTED_SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".s", ".S"}

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
STRUCT_INIT_RE = re.compile(
    r"^\s*static\s+struct\s*\{(?P<fields_decl>[^}]*)\}\s*(?P<var>[A-Za-z_]\w*)\s*=\s*\{(?P<values>[^}]*)\}\s*;\s*$"
)
RETURN_EXPR_RE = re.compile(r"^\s*return\s+(?P<expr>.+);\s*$")


@dataclass(frozen=True)
class BenchmarkSource:
    bench: str
    source_path: Path
    source_kind: str
    function_name: str = KERNEL_FUNCTION_NAME


@dataclass(frozen=True)
class CatalogWorkload:
    workload_id: str
    kind: str
    manifest_path: Path | None = None
    primary_source_path: Path | None = None
    analysis_source_path: Path | None = None
    source_kind: str = ""
    function_name: str = KERNEL_FUNCTION_NAME
    include_dirs: tuple[Path, ...] = ()
    compile_flags: tuple[str, ...] = ()
    llvm_flags: tuple[str, ...] = ()
    opt_flags: tuple[str, ...] = ()
    prevec_passes: str | None = None
    analysis_failure: str = ""
    analysis_failure_message: str = ""


@dataclass(frozen=True)
class ArgInfoSpec:
    kind: str
    expr: str | None = None
    fields: dict[str, str] | None = None


class ConversionError(RuntimeError):
    pass


def manual_source_path(root: Path, bench: str) -> Path:
    return root / RUN_SRC_ROOT / f"{bench}.c"


def categorized_manual_source_path(root: Path, bench: str) -> Path:
    return root / TSVC_RUN_SRC_ROOT / bench / f"{bench}.c"


def generated_source_path(root: Path, bench: str) -> Path:
    return root / GENERATED_RUN_SRC_ROOT / f"{bench}.c"


def loop_source_path(root: Path, bench: str) -> Path:
    return root / TSVC_LOOP_ROOT / f"{bench}.c"


def resolve_relative(base_dir: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def ensure_list(value: Any, field_name: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RuntimeError(f"{field_name} must be a list")
    return value


def load_mapping_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        data = json.loads(text)
    else:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                f"Failed to parse {path}. Install PyYAML or keep the file in strict JSON syntax."
            ) from exc
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise RuntimeError(f"manifest root must be a mapping: {path}")
    return data


def _analysis_source_result(
    *,
    manifest_path: Path,
    resolved_sources: list[Path],
    build: dict[str, Any],
) -> tuple[Path | None, str, str]:
    analysis_source_raw = build.get("analysis_source")
    if analysis_source_raw is not None:
        analysis_source = resolve_relative(manifest_path.parent.resolve(), str(analysis_source_raw))
        if analysis_source is None or analysis_source.suffix != ".c":
            raise RuntimeError(
                f"build.analysis_source must point to a .c file in sources: {manifest_path}"
            )
        if analysis_source not in resolved_sources:
            raise RuntimeError(
                f"build.analysis_source must point to a declared source entry: {manifest_path}"
            )
        return analysis_source, "", ""

    c_sources = [source for source in resolved_sources if source.suffix == ".c"]
    if len(c_sources) == 1:
        return c_sources[0], "", ""
    if not c_sources:
        return (
            None,
            "unsupported_analysis_source",
            "manifest does not declare an analyzable C source",
        )
    return (
        None,
        "unsupported_analysis_source",
        "manifest declares multiple C sources without build.analysis_source",
    )


def _load_manifest_workload(manifest_path: Path) -> CatalogWorkload:
    data = load_mapping_file(manifest_path)
    base_dir = manifest_path.parent.resolve()
    build = data.get("build") or {}
    entry = data.get("entry") or {}
    if not isinstance(build, dict):
        raise RuntimeError(f"build must be a mapping: {manifest_path}")
    if not isinstance(entry, dict):
        raise RuntimeError(f"entry must be a mapping: {manifest_path}")

    sources = ensure_list(data.get("sources"), "sources")
    if not sources:
        raise RuntimeError(f"manifest must declare at least one source: {manifest_path}")

    resolved_sources = [resolve_relative(base_dir, str(source)) for source in sources]
    for source in resolved_sources:
        if source is None or not source.exists():
            raise FileNotFoundError(f"source not found for manifest {manifest_path}: {source}")

    primary_sources = [
        source for source in resolved_sources if source.suffix in SUPPORTED_SOURCE_SUFFIXES
    ]
    analysis_source_path, analysis_failure, analysis_failure_message = _analysis_source_result(
        manifest_path=manifest_path.resolve(),
        resolved_sources=resolved_sources,
        build=build,
    )
    workload_id = str(data.get("name") or base_dir.name)
    entry_mode = str(entry.get("mode", "kernel"))
    function_name = str(
        entry.get("symbol", KERNEL_FUNCTION_NAME if entry_mode == "kernel" else "main")
    )

    return CatalogWorkload(
        workload_id=workload_id,
        kind="manifest",
        manifest_path=manifest_path.resolve(),
        primary_source_path=primary_sources[0] if len(primary_sources) == 1 else None,
        analysis_source_path=analysis_source_path,
        source_kind="manifest",
        function_name=function_name,
        include_dirs=tuple(
            resolve_relative(base_dir, str(value))
            for value in ensure_list(build.get("include_dirs"), "build.include_dirs")
        ),
        compile_flags=tuple(
            str(value) for value in ensure_list(build.get("compile_flags"), "build.compile_flags")
        ),
        llvm_flags=tuple(
            str(value) for value in ensure_list(build.get("llvm_flags"), "build.llvm_flags")
        ),
        opt_flags=tuple(
            str(value) for value in ensure_list(build.get("opt_flags"), "build.opt_flags")
        ),
        prevec_passes=str(build.get("prevec_passes")) if build.get("prevec_passes") else None,
        analysis_failure=analysis_failure,
        analysis_failure_message=analysis_failure_message,
    )


def resolve_catalog_dir(root: Path, catalog_dir: str = "") -> Path:
    run_src_root = (root / RUN_SRC_ROOT).resolve()
    if not catalog_dir:
        return run_src_root

    candidate = (run_src_root / catalog_dir).resolve()
    try:
        candidate.relative_to(run_src_root)
    except ValueError as exc:
        raise RuntimeError(f"catalog dir must be inside {RUN_SRC_ROOT}: {catalog_dir}") from exc
    if not candidate.exists():
        raise FileNotFoundError(f"catalog dir not found: {candidate}")
    if not candidate.is_dir():
        raise RuntimeError(f"catalog dir must be a directory: {candidate}")
    return candidate


def _should_include_legacy_tsvc(catalog_dir: str) -> bool:
    if not catalog_dir:
        return True
    return Path(catalog_dir).parts[:1] == ("tsvc",)


def _find_manual_source_path(root: Path, bench: str) -> Path | None:
    for candidate in (manual_source_path(root, bench), categorized_manual_source_path(root, bench)):
        if candidate.exists():
            return candidate
    return None


def discover_catalog_workloads(root: Path, catalog_dir: str = "") -> list[CatalogWorkload]:
    workloads_by_id: dict[str, CatalogWorkload] = {}
    search_root = resolve_catalog_dir(root, catalog_dir)

    for manifest_path in sorted(path for path in search_root.rglob("manifest.yaml") if path.is_file()):
        workload = _load_manifest_workload(manifest_path)
        existing = workloads_by_id.get(workload.workload_id)
        if existing is not None:
            raise RuntimeError(
                f"duplicate manifest workload id {workload.workload_id}: "
                f"{existing.manifest_path} and {workload.manifest_path}"
            )
        workloads_by_id[workload.workload_id] = workload

    if _should_include_legacy_tsvc(catalog_dir):
        manual = {path.stem for path in (root / RUN_SRC_ROOT).glob("s*.c")}
        manual.update(
            path.parent.name
            for path in (root / TSVC_RUN_SRC_ROOT).glob("*/s*.c")
            if path.stem == path.parent.name
        )
        loops = {path.stem for path in (root / TSVC_LOOP_ROOT).glob("s*.c")}
        for bench in sorted(manual | loops):
            if bench in workloads_by_id:
                continue
            manual_source = _find_manual_source_path(root, bench)
            if manual_source is not None:
                workloads_by_id[bench] = CatalogWorkload(
                    workload_id=bench,
                    kind="legacy_source",
                    primary_source_path=manual_source,
                    analysis_source_path=manual_source,
                    source_kind="manual",
                )
                continue
            generated = ensure_generated_source(root, bench)
            workloads_by_id[bench] = CatalogWorkload(
                workload_id=bench,
                kind="legacy_source",
                primary_source_path=generated,
                analysis_source_path=generated,
                source_kind="generated",
            )

    return sorted(workloads_by_id.values(), key=lambda workload: workload.workload_id)


def discover_catalog_benches(root: Path, catalog_dir: str = "") -> list[str]:
    return [workload.workload_id for workload in discover_catalog_workloads(root, catalog_dir)]


def discover_tsvc_benches(root: Path, catalog_dir: str = "") -> list[str]:
    return [
        workload.workload_id
        for workload in discover_catalog_workloads(root, catalog_dir)
        if re.fullmatch(r"s\d{3,5}", workload.workload_id)
    ]


def resolve_catalog_workload(root: Path, workload_id: str) -> CatalogWorkload:
    for workload in discover_catalog_workloads(root):
        if workload.workload_id == workload_id:
            return workload
    raise FileNotFoundError(f"workload not found for {workload_id}")


def resolve_workload_input(root: Path, workload_id: str) -> Path:
    workload = resolve_catalog_workload(root, workload_id)
    if workload.manifest_path is not None:
        return workload.manifest_path
    if workload.primary_source_path is not None:
        return workload.primary_source_path
    raise FileNotFoundError(f"workload input not found for {workload_id}")


def resolve_benchmark_source(root: Path, bench: str) -> BenchmarkSource:
    workload = resolve_catalog_workload(root, bench)
    if workload.primary_source_path is None:
        raise FileNotFoundError(f"simplified benchmark source not found for {bench}")
    return BenchmarkSource(
        bench=bench,
        source_path=workload.primary_source_path,
        source_kind=workload.source_kind,
        function_name=workload.function_name,
    )


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
    signature_re = re.compile(rf"\breal_t\s+{re.escape(bench)}\s*\(\s*struct\s+args_t\s*\*\s*func_args\s*\)")
    loop_body = _extract_function_body(
        source_text,
        signature_re,
    )
    helper_text = _extract_helper_text(source_text, signature_re)
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
        "#include <math.h>",
        "#include <stdlib.h>",
        '#include "common.h"',
        "",
        "#ifndef ABS",
        "#define ABS fabsf",
        "#endif",
        "",
        "extern int *tsvc_ip;",
        "extern int tsvc_n1;",
        "extern int tsvc_n3;",
        "extern real_t tsvc_s1;",
        "extern real_t tsvc_s2;",
        "extern real_t flat_2d_array[LEN_2D * LEN_2D];",
        "extern real_t x[LEN_1D];",
        "extern real_t tt[LEN_2D][LEN_2D];",
        "extern real_t * __restrict__ xx;",
        "extern real_t *yy;",
        "extern real_t test(real_t *A);",
        "extern real_t f(real_t a, real_t b);",
        "",
    ]
    if helper_text:
        lines.extend(helper_text.splitlines())
        lines.append("")
    lines.append("void kernel(void) {")
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
    struct_initializers: dict[str, dict[str, str]] = {}
    return_expr: str | None = None

    for line in body_text.splitlines():
        struct_init_match = STRUCT_INIT_RE.match(line)
        if struct_init_match:
            field_names = _parse_struct_field_names(struct_init_match.group("fields_decl"))
            values = [
                value.strip()
                for value in struct_init_match.group("values").split(",")
                if value.strip()
            ]
            if field_names and len(field_names) == len(values):
                struct_initializers[struct_init_match.group("var")] = dict(zip(field_names, values))
            continue

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
        if variable in struct_initializers:
            return ArgInfoSpec(kind="struct", fields=struct_initializers[variable])

    return ArgInfoSpec(kind="direct", expr=return_expr)


def _parse_struct_field_names(fields_decl: str) -> list[str]:
    return re.findall(r"([A-Za-z_]\w*)\s*(?:\[[^\]]+\])?\s*;", fields_decl)


def _extract_helper_text(source_text: str, signature_re: re.Pattern[str]) -> str:
    match = signature_re.search(source_text)
    if match is None:
        raise ConversionError(f"function matching {signature_re.pattern!r} not found")

    helper_lines: list[str] = []
    for line in source_text[:match.start()].splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#include"):
            continue
        helper_lines.append(line.rstrip())
    return "\n".join(helper_lines).strip()


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
    if arg_info.kind == "struct" and arg_info.fields:
        if len(arg_info.fields) == 1:
            return next(iter(arg_info.fields.values()))
        raise ConversionError("cannot rewrite scalar arg_info access from multi-field structured args")
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
