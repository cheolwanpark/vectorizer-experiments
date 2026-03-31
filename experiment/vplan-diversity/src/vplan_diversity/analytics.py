"""Statistics computation and result caching."""

from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .models import BenchResult, bench_from_dict, bench_to_dict


# ─── Caching ────────────────────────────────────────────────────────────────


def _cache_path(variant: str, vlen: int) -> Path:
    return Path.home() / ".cache" / "vplan-diversity" / f"rvv-{variant}-vlen{vlen}.json"


def _llvm_version(tools: dict[str, str]) -> str:
    try:
        r = subprocess.run([tools["opt"], "--version"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            if "version" in line.lower():
                return line.strip()
    except Exception:
        pass
    return "unknown"


def load_cache(variant: str, vlen: int) -> list[BenchResult] | None:
    cp = _cache_path(variant, vlen)
    if not cp.exists():
        return None
    try:
        data = json.loads(cp.read_text())
        return [bench_from_dict(d) for d in data["results"]]
    except Exception:
        return None


def save_cache(results: list[BenchResult], variant: str, vlen: int, tools: dict[str, str]):
    cp = _cache_path(variant, vlen)
    cp.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": datetime.now().isoformat(),
        "llvm_version": _llvm_version(tools),
        "variant": variant,
        "vlen": vlen,
        "results": [bench_to_dict(r) for r in results],
    }
    cp.write_text(json.dumps(data, indent=2))


# ─── Analytics ──────────────────────────────────────────────────────────────


@dataclass
class DashboardStats:
    total_benchmarks: int = 0
    successful: int = 0
    failed: int = 0
    total_loops: int = 0
    total_plans: int = 0
    plan_count_dist: dict[int, int] = field(default_factory=dict)
    vf_type_dist: dict[str, int] = field(default_factory=dict)
    selected_vf_dist: dict[str, int] = field(default_factory=dict)


@dataclass
class CategoryStats:
    category: str
    func_count: int = 0
    loop_count: int = 0
    plan_count: int = 0
    avg_plans_per_loop: float = 0.0
    fixed_vfs: int = 0
    scalable_vfs: int = 0
    failed: int = 0


@dataclass
class VFDistEntry:
    vf: str
    occurrences: int = 0
    selections: int = 0
    min_cost: int | None = None
    max_cost: int | None = None


def _classify_vf(vf: str) -> str:
    if "vscale" in vf.lower():
        return "scalable"
    return "fixed"


def compute_dashboard_stats(results: list[BenchResult]) -> DashboardStats:
    s = DashboardStats()
    s.total_benchmarks = len(results)
    plan_counts: list[int] = []

    for r in results:
        if r.error:
            s.failed += 1
            continue
        s.successful += 1
        s.total_loops += len(r.loops)
        for loop in r.loops:
            s.total_plans += len(loop.plans)
            plan_counts.append(len(loop.plans))

            vf_types = set()
            for plan in loop.plans:
                for vf in plan.vfs:
                    vf_types.add(_classify_vf(vf))
            if vf_types == {"fixed"}:
                s.vf_type_dist["fixed only"] = s.vf_type_dist.get("fixed only", 0) + 1
            elif vf_types == {"scalable"}:
                s.vf_type_dist["scalable only"] = s.vf_type_dist.get("scalable only", 0) + 1
            elif len(vf_types) > 1:
                s.vf_type_dist["mixed"] = s.vf_type_dist.get("mixed", 0) + 1

            if loop.selected_vf:
                s.selected_vf_dist[loop.selected_vf] = s.selected_vf_dist.get(loop.selected_vf, 0) + 1

    s.plan_count_dist = dict(Counter(plan_counts))
    return s


def compute_category_stats(results: list[BenchResult]) -> list[CategoryStats]:
    by_cat: dict[str, list[BenchResult]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)

    stats = []
    for cat in sorted(by_cat):
        cs = CategoryStats(category=cat)
        rs = by_cat[cat]
        cs.func_count = len(rs)
        for r in rs:
            if r.error:
                cs.failed += 1
                continue
            cs.loop_count += len(r.loops)
            for loop in r.loops:
                cs.plan_count += len(loop.plans)
                for plan in loop.plans:
                    for vf in plan.vfs:
                        if _classify_vf(vf) == "scalable":
                            cs.scalable_vfs += 1
                        else:
                            cs.fixed_vfs += 1
        if cs.loop_count > 0:
            cs.avg_plans_per_loop = cs.plan_count / cs.loop_count
        stats.append(cs)
    return stats


def compute_vf_distribution(results: list[BenchResult]) -> list[VFDistEntry]:
    vf_data: dict[str, VFDistEntry] = {}

    for r in results:
        for loop in r.loops:
            for plan in loop.plans:
                for vc in plan.costs:
                    if vc.vf not in vf_data:
                        vf_data[vc.vf] = VFDistEntry(vf=vc.vf)
                    e = vf_data[vc.vf]
                    e.occurrences += 1
                    if vc.cost is not None:
                        if e.min_cost is None or vc.cost < e.min_cost:
                            e.min_cost = vc.cost
                        if e.max_cost is None or vc.cost > e.max_cost:
                            e.max_cost = vc.cost

            if loop.selected_vf:
                if loop.selected_vf not in vf_data:
                    vf_data[loop.selected_vf] = VFDistEntry(vf=loop.selected_vf)
                vf_data[loop.selected_vf].selections += 1

    return sorted(vf_data.values(), key=lambda e: e.occurrences, reverse=True)
