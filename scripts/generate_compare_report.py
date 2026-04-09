#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import sqlite3
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "compare_report.md"

DEFAULT_DB_PATTERNS = {
    "rvv": "emulate-result-*.sqlite",
    "intel": "profile-result-*.sqlite",
}

CATEGORY_RULES = {
    "both": lambda intel, rvv: intel >= 0.20 and rvv >= 0.20,
    "intel_only": lambda intel, rvv: intel >= 0.20 and rvv < 0.10,
    "rvv_only": lambda intel, rvv: rvv >= 0.20 and intel < 0.10,
}

CATEGORY_CONFIGS = [
    {
        "key": "both",
        "title": "둘다 이득",
        "limit": 2,
        "preferred": ["s111", "s2710", "s4117", "s276", "s442"],
    },
    {
        "key": "intel_only",
        "title": "Intel만 이득",
        "limit": 2,
        "preferred": ["s2275", "s257", "s315", "s278", "s1232"],
    },
    {
        "key": "rvv_only",
        "title": "RVV만 이득",
        "limit": 2,
        "preferred": ["s351", "s452", "s279", "s122", "s274"],
    },
]

SNIPPET_HINTS = {
    ("s111", "intel", "ir", "default"): ["llvm.masked.scatter", "shufflevector"],
    ("s111", "intel", "ir", "best"): ["extractelement", "fadd <4 x float>"],
    ("s111", "intel", "asm", "default"): ["vscatterqps", "vaddps"],
    ("s111", "intel", "asm", "best"): ["vmovss", "vextractps"],
    ("s111", "rvv", "ir", "default"): ["shufflevector <vscale", "llvm.masked.scatter"],
    ("s111", "rvv", "ir", "best"): ["br label %for.body", "load float"],
    ("s111", "rvv", "asm", "default"): ["vlse32.v", "vfadd.vv"],
    ("s111", "rvv", "asm", "best"): ["flw", "fadd.s"],
    ("s2710", "intel", "ir", "default"): ["llvm.fmuladd.v8f32", "llvm.masked.store"],
    ("s2710", "intel", "ir", "best"): ["fcmp ogt float", "br i1"],
    ("s2710", "intel", "asm", "default"): ["vcmpltps", "vfmadd213ps"],
    ("s2710", "intel", "asm", "best"): ["vmovss", "vfmadd213ss"],
    ("s2710", "rvv", "ir", "default"): ["llvm.masked.store.nxv4f32", "wide.load5"],
    ("s2710", "rvv", "ir", "best"): ["br label %for.body", "%cmp3 = fcmp"],
    ("s2710", "rvv", "asm", "default"): ["vl2re32.v", "vsetvli"],
    ("s2710", "rvv", "asm", "best"): ["fmadd.s", "fsw"],
    ("s2275", "intel", "ir", "default"): ["llvm.masked.scatter", "wide.masked.gather"],
    ("s2275", "intel", "ir", "best"): ["br i1 %exitcond.not.3", "for.body3"],
    ("s2275", "intel", "asm", "default"): ["vgatherdps", "vscatterdps"],
    ("s2275", "intel", "asm", "best"): ["vmovss", "vfmadd213ss"],
    ("s2275", "rvv", "ir", "default"): ["br label %vector.body", "%evl.based.iv"],
    ("s2275", "rvv", "ir", "best"): ["br label %vector.body", "%evl.based.iv"],
    ("s2275", "rvv", "asm", "default"): ["vsetvli", ".LBB0_1"],
    ("s2275", "rvv", "asm", "best"): ["vsetvli", ".LBB0_1"],
    ("s257", "intel", "ir", "default"): ["llvm.masked.scatter", "wide.masked.gather3"],
    ("s257", "intel", "ir", "best"): ["for.cond1.preheader", "br i1 %exitcond5.not"],
    ("s257", "intel", "asm", "default"): ["vgatherdps", "vscatterdps"],
    ("s257", "intel", "asm", "best"): ["vaddss", "vmovss"],
    ("s257", "rvv", "ir", "default"): ["%load_initial = load float", "for.cond1.preheader"],
    ("s257", "rvv", "ir", "best"): ["%load_initial = load float", "for.cond1.preheader"],
    ("s257", "rvv", "asm", "default"): ["flw", ".LBB0_1"],
    ("s257", "rvv", "asm", "best"): ["flw", ".LBB0_1"],
    ("s351", "intel", "ir", "default"): ["shufflevector <8 x float>", "vector.body"],
    ("s351", "intel", "ir", "best"): ["shufflevector <4 x float>", "vector.body"],
    ("s351", "intel", "asm", "default"): ["vfmadd213ps", "vmovaps"],
    ("s351", "intel", "asm", "best"): ["vfmadd231ps", "vmovlps"],
    ("s351", "rvv", "ir", "default"): ["shufflevector <vscale x 2 x float>", "vector.body"],
    ("s351", "rvv", "ir", "best"): ["shufflevector <4 x float>", "for.body"],
    ("s351", "rvv", "asm", "default"): ["vlseg5e32.v", "vfmacc.vf"],
    ("s351", "rvv", "asm", "best"): ["vle32.v", "fmadd.s"],
    ("s452", "intel", "ir", "default"): ["%vec.ind.next = add <8 x i64>", "vector.body"],
    ("s452", "intel", "ir", "best"): ["%vec.ind.next = add <8 x i64>", "vector.body"],
    ("s452", "intel", "asm", "default"): ["vcvtdq2ps", "vfmadd213ps"],
    ("s452", "intel", "asm", "best"): ["vcvtdq2ps", "vfmadd213ps"],
    ("s452", "rvv", "ir", "default"): ["llvm.stepvector", "broadcast.splat"],
    ("s452", "rvv", "ir", "best"): ["br label %for.body", "fcvt"],
    ("s452", "rvv", "asm", "default"): ["vid.v", "vsetvli"],
    ("s452", "rvv", "asm", "best"): ["fcvt.s.wu", "fmadd.s"],
}

GENERIC_HINTS = {
    ("intel", "ir", "default"): ["llvm.masked.scatter", "llvm.masked.store", "shufflevector", "fcmp "],
    ("intel", "ir", "best"): ["extractelement", "br i1", "shufflevector", "fcmp "],
    ("intel", "asm", "default"): ["vgather", "vscatter", "vfmadd", "vmovaps"],
    ("intel", "asm", "best"): ["vmovss", "vextractps", "vfmadd213ss", "jmp"],
    ("rvv", "ir", "default"): ["llvm.masked.store", "shufflevector <vscale", "llvm.stepvector", "vscale"],
    ("rvv", "ir", "best"): ["br i1", "br label %for.body", "load float", "shufflevector <4 x float>"],
    ("rvv", "asm", "default"): ["vsetvli", "vlseg", "vlse32.v", "vid.v"],
    ("rvv", "asm", "best"): ["flw", "fmadd.s", "fadd.s", "fsw"],
}


@dataclass(frozen=True)
class VariantResult:
    use_vf: str
    kernel_cycles: int
    opt_ll_text: str
    asm_text: str


@dataclass(frozen=True)
class BenchSummary:
    bench: str
    default: VariantResult
    best: VariantResult
    speedup: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate compare_report.md from emulate/profile SQLite outputs."
    )
    parser.add_argument("--emulate-db", default="", help="Path to emulate-result-*.sqlite")
    parser.add_argument("--profile-db", default="", help="Path to profile-result-*.sqlite")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output markdown path")
    return parser.parse_args()


def resolve_input(root: Path, value: str, pattern: str) -> Path:
    if value:
        path = Path(value)
        if not path.is_absolute():
            path = (root / value).resolve()
        if not path.exists():
            raise SystemExit(f"input file not found: {path}")
        return path
    matches = sorted((root / "artifacts").glob(pattern))
    if not matches:
        raise SystemExit(f"no files matched artifacts/{pattern}")
    return matches[-1].resolve()


def load_bench_summaries(db_path: Path) -> dict[str, BenchSummary]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT bench, use_vf, kernel_cycles, opt_ll_text, asm_text
        FROM emulate_results
        WHERE stage IN ('emulate', 'profile')
          AND failure = ''
          AND kernel_cycles IS NOT NULL
        ORDER BY bench, use_vf
        """
    ).fetchall()
    conn.close()

    variants_by_bench: dict[str, list[VariantResult]] = {}
    for row in rows:
        bench = str(row["bench"])
        variants_by_bench.setdefault(bench, []).append(
            VariantResult(
                use_vf=str(row["use_vf"] or ""),
                kernel_cycles=int(row["kernel_cycles"]),
                opt_ll_text=str(row["opt_ll_text"] or ""),
                asm_text=str(row["asm_text"] or ""),
            )
        )

    summaries: dict[str, BenchSummary] = {}
    for bench, variants in variants_by_bench.items():
        default = next((variant for variant in variants if variant.use_vf == ""), None)
        if default is None:
            continue
        best = min(variants, key=lambda variant: (variant.kernel_cycles, vf_sort_key(variant.use_vf)))
        speedup = 1.0 - (best.kernel_cycles / default.kernel_cycles)
        summaries[bench] = BenchSummary(bench=bench, default=default, best=best, speedup=speedup)
    return summaries


def vf_sort_key(use_vf: str) -> tuple[int, int]:
    if not use_vf:
        return (2, 0)
    family, _, factor = use_vf.partition(":")
    family_rank = {"fixed": 0, "scalable": 1}.get(family, 3)
    return (family_rank, int(factor or "0"))


def display_vf(use_vf: str) -> str:
    return "default" if not use_vf else use_vf


def classify_benches(
    intel_summaries: dict[str, BenchSummary],
    rvv_summaries: dict[str, BenchSummary],
) -> dict[str, list[str]]:
    categories = {config["key"]: [] for config in CATEGORY_CONFIGS}
    for bench in sorted(set(intel_summaries) & set(rvv_summaries)):
        intel_speedup = intel_summaries[bench].speedup
        rvv_speedup = rvv_summaries[bench].speedup
        for key, predicate in CATEGORY_RULES.items():
            if predicate(intel_speedup, rvv_speedup):
                categories[key].append(bench)
                break
    return categories


def rank_key(
    category_key: str,
    bench: str,
    intel_summaries: dict[str, BenchSummary],
    rvv_summaries: dict[str, BenchSummary],
) -> tuple[float, float]:
    intel_speedup = intel_summaries[bench].speedup
    rvv_speedup = rvv_summaries[bench].speedup
    if category_key == "both":
        return (min(intel_speedup, rvv_speedup), intel_speedup + rvv_speedup)
    if category_key == "intel_only":
        return (intel_speedup, intel_speedup - rvv_speedup)
    return (rvv_speedup, rvv_speedup - intel_speedup)


def select_case_benches(
    intel_summaries: dict[str, BenchSummary],
    rvv_summaries: dict[str, BenchSummary],
) -> list[tuple[str, str]]:
    categories = classify_benches(intel_summaries, rvv_summaries)
    selected: list[tuple[str, str]] = []
    for config in CATEGORY_CONFIGS:
        category_key = str(config["key"])
        available = set(categories[category_key])
        chosen: list[str] = []
        for bench in config["preferred"]:
            if bench in available and bench not in chosen:
                chosen.append(bench)
            if len(chosen) == config["limit"]:
                break
        if len(chosen) < config["limit"]:
            ranked = sorted(
                available - set(chosen),
                key=lambda bench: rank_key(category_key, bench, intel_summaries, rvv_summaries),
                reverse=True,
            )
            chosen.extend(ranked[: config["limit"] - len(chosen)])
        for bench in chosen:
            selected.append((category_key, bench))
    return selected


def source_path_for_bench(bench: str) -> Path:
    return ROOT / "emulator" / "benchmarks" / "TSVC_2" / "src" / "loops" / f"{bench}.c"


def extract_source_snippet(bench: str) -> str:
    source_path = source_path_for_bench(bench)
    lines = source_path.read_text().splitlines()
    start_index = next(
        (index for index, line in enumerate(lines) if line.strip().startswith("for (int nl")),
        None,
    )
    if start_index is None:
        start_index = next(
            (index for index, line in enumerate(lines) if line.strip().startswith("for (int i")),
            0,
        )
    depth = 0
    end_index = start_index
    saw_open = False
    for index in range(start_index, len(lines)):
        line = lines[index]
        open_count = line.count("{")
        close_count = line.count("}")
        if open_count:
            saw_open = True
        depth += open_count
        depth -= close_count
        end_index = index + 1
        if saw_open and depth == 0:
            break
    return "\n".join(lines[start_index:end_index]).strip()


def extract_snippet(text: str, hints: list[str], *, before: int = 1, after: int = 6) -> str:
    lines = text.splitlines()
    for hint in hints:
        for index, line in enumerate(lines):
            if hint in line:
                lo = max(0, index - before)
                hi = min(len(lines), index + after + 1)
                return "\n".join(lines[lo:hi]).strip()
    for index, line in enumerate(lines):
        if line.strip():
            hi = min(len(lines), index + after + 1)
            return "\n".join(lines[index:hi]).strip()
    return ""


def snippet_for(bench: str, target: str, kind: str, which: str, text: str) -> str:
    hints = SNIPPET_HINTS.get((bench, target, kind, which))
    if hints is None:
        hints = GENERIC_HINTS[(target, kind, which)]
    return html.escape(extract_snippet(text, hints))


def fmt_speedup(value: float) -> str:
    return f"{value:.4f}"


def fmt_variant(variant: VariantResult) -> str:
    return f"`{display_vf(variant.use_vf)}` / {variant.kernel_cycles}"


def load_case_notes(bench: str, intel: BenchSummary, rvv: BenchSummary) -> list[str]:
    intel_best = display_vf(intel.best.use_vf)
    rvv_best = display_vf(rvv.best.use_vf)
    notes = {
        "s111": [
            f"두 타겟 모두 stride-2 odd-lane update에서 default가 너무 넓고, 더 좁은 plan이 이긴다. Intel은 {intel_best}, RVV는 {rvv_best}가 최적이다.",
            "Intel default는 scatter 중심의 wide SIMD 경로라 불필요한 lane 처리 비용이 크고, best에서는 필요한 odd lane만 저장하는 쪽으로 단순화된다.",
            "RVV default는 `vsetvli + vlse32.v/vsse32.v` 형태의 strided 접근 비용이 커서, 결국 scalar-like fixed plan이 더 싸다.",
        ],
        "s2710": [
            "중첩 분기와 상이한 update path가 섞여 있어 wide predicated loop가 비싸다.",
            f"Intel도 {intel_best}에서 이득을 보지만 개선 폭은 제한적이고, wide masked FMA 경로를 줄이는 정도에 그친다.",
            f"RVV는 default vector predication 대비 {rvv_best}가 훨씬 단순한 분기 루프로 내려가며 개선 폭이 더 크다.",
        ],
        "s2275": [
            "2D update와 1D update가 같은 루프에 묶여 있어 Intel default는 gather/scatter 중심 경로로 내려가고 비용이 커진다.",
            f"Intel {intel_best}는 inner update를 사실상 scalar에 가깝게 처리해 큰 폭의 감소를 만든다.",
            "RVV는 default가 이미 최선이고 추가 VF가 이득을 못 만든다. 이 사례는 RVV 우위라기보다 Intel 쪽에만 튜닝 여지가 큰 경우다.",
        ],
        "s257": [
            "loop-carried dependence와 array expansion이 핵심이라 RVV에서는 어떤 VF도 눈에 띄는 개선을 못 만든다.",
            f"Intel은 {intel_best}에서 gather/scatter default를 scalar recurrence update에 가까운 형태로 줄이면서 이득을 얻는다.",
            "핵심 차이는 벡터 폭 자체보다 dependence를 안고 있는 업데이트를 얼마나 싸게 풀어내느냐에 있다.",
        ],
        "s351": [
            "5-way unrolled saxpy 패턴에서 RVV default는 segmented load/store 중심 경로로 내려가며 과한 setup 비용을 낸다.",
            f"RVV {rvv_best}는 `vlseg5e32` 기반 default보다 훨씬 단순한 mixed vector/scalar 루프로 바뀌면서 압도적으로 빨라진다.",
            f"Intel은 default와 {intel_best} 차이가 거의 없어 이미 적절한 폭을 고르고 있다. 따라서 큰 차이는 RVV default 선택 실패에 더 가깝다.",
        ],
        "s452": [
            "인덱스 기반 multiply-add는 RVV default가 `vid.v`와 wide setup 비용을 먼저 크게 지불한다.",
            f"RVV {rvv_best}는 scalar FMA loop로 내려가며 setup 비용을 제거해 큰 개선을 만든다.",
            "Intel은 default가 이미 best라 추가 VF 이득이 없다. 이 사례 역시 RVV의 넓은 default path가 과했다는 해석이 맞다.",
        ],
    }
    return notes.get(
        bench,
        [
            f"Intel best는 {intel_best}, RVV best는 {rvv_best}로 선택됐다.",
            "이 사례는 default path와 best path 사이의 lowering 단순화가 성능 차이를 만들었다.",
            "세부 해석은 IR/ASM 스니펫이 보여주는 메모리 접근 방식과 분기 형태를 기준으로 읽는다.",
        ],
    )


def make_overview(
    emulate_db: Path,
    profile_db: Path,
    selected_cases: list[tuple[str, str]],
    intel_summaries: dict[str, BenchSummary],
    rvv_summaries: dict[str, BenchSummary],
) -> str:
    grouped: dict[str, list[str]] = {}
    for category_key, bench in selected_cases:
        grouped.setdefault(category_key, []).append(bench)
    bullet_lines = []
    for config in CATEGORY_CONFIGS:
        benches = ", ".join(f"`{bench}`" for bench in grouped.get(config["key"], []))
        bullet_lines.append(f"- **{config['title']}**: {benches}")
    return "\n".join(
        [
            "# RVV Emulate vs Intel Profile 상세 비교 정리",
            "",
            "이 문서는 현재 산출물 두 개를 처음부터 다시 읽어 비교한 결과를 바탕으로,",
            "대표 사례 6개를 골라 **Intel default/best** 와 **RVV default/best** 를 다시 정리한 문서이다.",
            "형식은 기존 `compare_report.md`와 동일하게 각 벤치마다",
            "`실행 정보 / IR 비교 / ASM 비교 / 분석` 순서로 정리했다.",
            "",
            "## 0. Overview",
            "",
            "비교 대상:",
            "",
            f"- **Intel profile**: `artifacts/{profile_db.name}`",
            f"- **RVV emulate**: `artifacts/{emulate_db.name}`",
            "",
            "현재 결과물의 관찰 포인트:",
            "",
            "- profile DB는 default + `fixed:*`만 존재하고, emulate DB는 default + `fixed:*` + `scalable:*`를 함께 포함한다.",
            "- 따라서 이전 보고서의 사례와 해석을 유지하지 않고, 현재 DB에서 다시 계산한 SpeedUp과 코드 형태를 기준으로 사례를 재선정했다.",
            "",
            "대표 벤치 선정:",
            "",
            *bullet_lines,
            "",
            "핵심 요약:",
            "",
            "- 양쪽 모두 이득을 보는 경우에도 공통적으로 더 좁은 fixed plan이 default보다 잘 맞는 사례가 많다.",
            "- Intel만 이득인 사례는 gather/scatter 또는 recurrence를 scalar 쪽으로 더 단순하게 푸는 경우가 많다.",
            "- RVV만 이득인 사례 상당수는 RVV가 본질적으로 강하다기보다, default wide path의 setup 비용이 과했던 경우에 가깝다.",
        ]
    )


def make_methodology() -> str:
    return "\n".join(
        [
            "## 1. 분석방법",
            "",
            "### 1.1 SpeedUp 정의",
            "",
            "각 벤치에 대해:",
            "",
            "- **DefaultLatency**: `use_vf=''` 행의 `kernel_cycles`",
            "- **BestLatency**: 같은 DB 안에서 `kernel_cycles`가 최소인 행의 값",
            "",
            "```text",
            "SpeedUp = 1.0 - BestLatency / DefaultLatency",
            "```",
            "",
            "### 1.2 사례 선정 기준",
            "",
            "- **둘다 이득**: Intel/RVV 모두 `SpeedUp >= 0.20`",
            "- **Intel만 이득**: Intel `>= 0.20`, RVV `< 0.10`",
            "- **RVV만 이득**: RVV `>= 0.20`, Intel `< 0.10`",
            "- 각 범주에서 1~2개만 남기기 위해 현재 DB 기준으로 설명력이 큰 벤치를 우선 선택했다.",
            "",
            "### 1.3 해석 원칙",
            "",
            "- IR/ASM은 각 벤치의 default와 best에서 차이가 드러나는 부분만 발췌했다.",
            "- SpeedUp 차이를 곧바로 아키텍처 우열로 해석하지 않고, default lowering 실패와 패턴 적합성 차이를 구분해서 본다.",
        ]
    )


def make_case_section(
    index: int,
    category_title: str,
    bench: str,
    intel: BenchSummary,
    rvv: BenchSummary,
) -> str:
    source_rel = source_path_for_bench(bench).relative_to(ROOT)
    source_snippet = extract_source_snippet(bench)
    notes = load_case_notes(bench, intel, rvv)
    intel_ir_default = snippet_for(bench, "intel", "ir", "default", intel.default.opt_ll_text)
    intel_ir_best = snippet_for(bench, "intel", "ir", "best", intel.best.opt_ll_text)
    rvv_ir_default = snippet_for(bench, "rvv", "ir", "default", rvv.default.opt_ll_text)
    rvv_ir_best = snippet_for(bench, "rvv", "ir", "best", rvv.best.opt_ll_text)
    intel_asm_default = snippet_for(bench, "intel", "asm", "default", intel.default.asm_text)
    intel_asm_best = snippet_for(bench, "intel", "asm", "best", intel.best.asm_text)
    rvv_asm_default = snippet_for(bench, "rvv", "asm", "default", rvv.default.asm_text)
    rvv_asm_best = snippet_for(bench, "rvv", "asm", "best", rvv.best.asm_text)
    return "\n".join(
        [
            f"### 2.{index} {category_title}: `{bench}`",
            "",
            f"소스: [`{source_rel}`]({source_rel})",
            "",
            "```c",
            source_snippet,
            "```",
            "",
            "실행 정보:",
            "",
            "| target | default | best | SpeedUp |",
            "| --- | --- | --- | ---: |",
            f"| Intel | {fmt_variant(intel.default)} | {fmt_variant(intel.best)} | {fmt_speedup(intel.speedup)} |",
            f"| RVV | {fmt_variant(rvv.default)} | {fmt_variant(rvv.best)} | {fmt_speedup(rvv.speedup)} |",
            "",
            "IR 비교:",
            "",
            "<table>",
            "<tr>",
            "<th>Intel default</th>",
            "<th>Intel best</th>",
            "</tr>",
            "<tr>",
            f"<td><pre><code class=\"language-llvm\">{intel_ir_default}</code></pre></td>",
            f"<td><pre><code class=\"language-llvm\">{intel_ir_best}</code></pre></td>",
            "</tr>",
            "</table>",
            "",
            "<table>",
            "<tr>",
            "<th>RVV default</th>",
            "<th>RVV best</th>",
            "</tr>",
            "<tr>",
            f"<td><pre><code class=\"language-llvm\">{rvv_ir_default}</code></pre></td>",
            f"<td><pre><code class=\"language-llvm\">{rvv_ir_best}</code></pre></td>",
            "</tr>",
            "</table>",
            "",
            "ASM 비교:",
            "",
            "<table>",
            "<tr>",
            "<th>Intel default</th>",
            "<th>Intel best</th>",
            "</tr>",
            "<tr>",
            f"<td><pre><code class=\"language-asm\">{intel_asm_default}</code></pre></td>",
            f"<td><pre><code class=\"language-asm\">{intel_asm_best}</code></pre></td>",
            "</tr>",
            "</table>",
            "",
            "<table>",
            "<tr>",
            "<th>RVV default</th>",
            "<th>RVV best</th>",
            "</tr>",
            "<tr>",
            f"<td><pre><code class=\"language-asm\">{rvv_asm_default}</code></pre></td>",
            f"<td><pre><code class=\"language-asm\">{rvv_asm_best}</code></pre></td>",
            "</tr>",
            "</table>",
            "",
            "분석:",
            "",
            *[f"- {note}" for note in notes],
        ]
    )


def render_report(
    emulate_db: Path,
    profile_db: Path,
    intel_summaries: dict[str, BenchSummary],
    rvv_summaries: dict[str, BenchSummary],
) -> str:
    selected_cases = select_case_benches(intel_summaries, rvv_summaries)
    pieces = [
        make_overview(emulate_db, profile_db, selected_cases, intel_summaries, rvv_summaries),
        "",
        make_methodology(),
        "",
        "## 2. 사례 정리",
        "",
    ]
    title_by_key = {config["key"]: config["title"] for config in CATEGORY_CONFIGS}
    for index, (category_key, bench) in enumerate(selected_cases, start=1):
        pieces.append(
            make_case_section(
                index=index,
                category_title=title_by_key[category_key],
                bench=bench,
                intel=intel_summaries[bench],
                rvv=rvv_summaries[bench],
            )
        )
        pieces.append("")
    return "\n".join(pieces).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    emulate_db = resolve_input(ROOT, args.emulate_db, DEFAULT_DB_PATTERNS["rvv"])
    profile_db = resolve_input(ROOT, args.profile_db, DEFAULT_DB_PATTERNS["intel"])
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (ROOT / args.output).resolve()

    rvv_summaries = load_bench_summaries(emulate_db)
    intel_summaries = load_bench_summaries(profile_db)
    report = render_report(emulate_db, profile_db, intel_summaries, rvv_summaries)
    output_path.write_text(report)


if __name__ == "__main__":
    main()
