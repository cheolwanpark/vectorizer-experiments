#!/usr/bin/env python3
"""Merge vectorization results from all targets into one CSV."""
import csv
from pathlib import Path

base = Path("/root/rvv-poc/results/vectorization")
targets = ["saturn", "xiangshan", "t1"]
rows = []

fields = ["kernel","target","lmul","vectorized","asm_lmul","vector_insts","notes"]
for target in targets:
    f = base / target / "results.csv"
    with open(f) as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            clean = {k: row.get(k, "") for k in fields}
            rows.append(clean)

# Write merged
out = base / "all_vectorization.csv"
with open(out, "w", newline="") as fp:
    writer = csv.DictWriter(fp, fieldnames=["kernel","target","lmul","vectorized","asm_lmul","vector_insts","notes"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Written {len(rows)} rows to {out}")

# Summary statistics
from collections import defaultdict, Counter

# Per-kernel summary
kernel_data = defaultdict(list)
for r in rows:
    kernel_data[r["kernel"]].append(r)

print("\n=== SUMMARY ===")
print(f"Total combinations: {len(rows)}")
print(f"  Vectorized: {sum(1 for r in rows if r['vectorized']=='yes')}")
print(f"  Scalar (no): {sum(1 for r in rows if r['vectorized']=='no')}")
print(f"  Build fail: {sum(1 for r in rows if r['vectorized']=='BUILD_FAIL')}")
print(f"  LMUL mismatch: {sum(1 for r in rows if 'lmul_mismatch' in r.get('notes',''))}")

print("\n=== PER TARGET ===")
for t in targets:
    t_rows = [r for r in rows if r["target"]==t]
    vec = sum(1 for r in t_rows if r["vectorized"]=="yes")
    nv = sum(1 for r in t_rows if r["vectorized"]=="no")
    bf = sum(1 for r in t_rows if r["vectorized"]=="BUILD_FAIL")
    mm = sum(1 for r in t_rows if "lmul_mismatch" in r.get("notes",""))
    print(f"  {t:12}: {vec} vec, {nv} scalar, {bf} build_fail, {mm} lmul_mismatch")

print("\n=== LMUL MISMATCH DETAILS ===")
for r in rows:
    if "lmul_mismatch" in r.get("notes",""):
        print(f"  {r['kernel']:8} {r['target']:12} lmul={r['lmul']} -> asm={r['asm_lmul']}  {r['notes']}")

print("\n=== BUILD FAILURES (T1) ===")
for r in rows:
    if r["vectorized"] == "BUILD_FAIL":
        print(f"  {r['kernel']:8} {r['target']:12} lmul={r['lmul']}")

# Per-kernel vectorization status table
print("\n=== PER-KERNEL VECTORIZATION STATUS ===")
print(f"{'kernel':8} {'saturn':30} {'xiangshan':30} {'t1':30}")
print("-"*100)
for k in sorted(kernel_data.keys()):
    parts = []
    for t in targets:
        t_rows = [r for r in kernel_data[k] if r["target"]==t]
        statuses = []
        for r in sorted(t_rows, key=lambda x: int(x["lmul"])):
            if r["vectorized"] == "yes":
                lm = r["asm_lmul"]
                exp = f"m{r['lmul']}"
                if lm != exp:
                    statuses.append(f"{lm}!")
                else:
                    statuses.append(lm)
            elif r["vectorized"] == "BUILD_FAIL":
                statuses.append("BFAIL")
            else:
                statuses.append("SCALAR")
        parts.append(" ".join(statuses))
    print(f"{k:8} {parts[0]:30} {parts[1]:30} {parts[2]:30}")
