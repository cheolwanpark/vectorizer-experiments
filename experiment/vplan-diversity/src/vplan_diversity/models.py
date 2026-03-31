"""Data models and serialization for VPlan diversity results."""

from __future__ import annotations

from dataclasses import asdict, dataclass


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


@dataclass
class AppRuntimeConfig:
    variant: str
    vlen: int
    llvm_custom: str | None
    tsvc_dir: str
    tools: dict[str, str]


@dataclass
class AnalysisEntry:
    loop_index: int
    plan_index: int
    all_vfs: list[str]
    forced_vf: str
    cost_summary: str
    command: str
    log_path: str
    status: str
    dump_text: str
    message: str | None
    selected_vf: str | None
    selected_plan: int | None


@dataclass
class FunctionAnalysisReport:
    func_name: str
    category: str
    entries: list[AnalysisEntry]
    source_code: str
    source_path: str | None
    markdown_report: str


def bench_to_dict(b: BenchResult) -> dict:
    return asdict(b)


def bench_from_dict(d: dict) -> BenchResult:
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
