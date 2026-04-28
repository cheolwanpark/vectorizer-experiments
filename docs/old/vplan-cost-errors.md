# VPlan Cost Errors

This note summarizes why the current LLVM vectorizer cost path appears to mis-rank several VF choices in this repo's benchmark results, and ties each hypothesis to concrete code in `llvm-project/`.

Scope:

- Benchmarks: `s111`, `s1115`, `s128`, `s2101`, `s2710`, `s276`, `s279`, `s4112`, `s4117`
- Targets observed:
  - `profile`: x86 fixed-width vectorization
  - `emulate`: RVV-style scalable/predicated vectorization in the emulator

## Executive Summary

The main pattern is not "LLVM failed to vectorize." It is "LLVM chose a legal vector form whose modeled cost is too low relative to the actual generated code."

The strongest likely error sources are:

1. X86 gather/scatter cost is too coarse and misses split/pack overhead.
2. RISCV RVV gather/strided cost under-models `vsetvli`, mask plumbing, and index-generation overhead.
3. VPlan predication / replicate-region CFG cost is undercounted.
4. The cost model understands legality classes such as consecutive, interleaved, gather/scatter, and predicated, but it does not understand higher-level access semantics such as pairwise reuse or sparse live lanes.

## Top-Level LLVM Flow

The loop vectorizer flow relevant to these cases is:

1. Build legality:
   - `LoopVectorizationLegality LVL(...)`
   - file: `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:10028-10037`
2. Build interleaving info:
   - `InterleavedAccessInfo IAI(...)`
   - `IAI.analyzeInterleaving(...)`
   - file: `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:10066-10075`
3. Build cost model and planner:
   - `LoopVectorizationCostModel CM(...)`
   - `LoopVectorizationPlanner LVP(...)`
   - file: `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:10163-10168`
4. Pick best VF:
   - `LVP.computeBestVF()`
   - file: `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:10212`
   - implementation: `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:7375-7492`

Relevant snippet:

```cpp
LoopVectorizationCostModel CM(..., IAI, OptForSize);
LoopVectorizationPlanner LVP(..., &LVL, CM, IAI, ...);
LVP.plan(UserVF, UserIC);
VF = LVP.computeBestVF();
```

## Cause 1: X86 Gather/Scatter Cost Is Too Coarse

This explains the profile-side behavior of `s2101`, `s4112`, `s4117`, and part of `s111` / `s128` / `s276`.

### Relevant code path

- Legality of gather/scatter:
  - `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:1359-1371`
  - `LoopVectorizationCostModel::isLegalGatherOrScatter`
- Decision between interleave / gather-scatter / scalarize:
  - `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:5960-6014`
  - `LoopVectorizationCostModel::setCostBasedWideningDecision`
- Gather/scatter cost in legacy cost model:
  - `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:5573-5591`
  - `LoopVectorizationCostModel::getGatherScatterCost`
- X86 target cost:
  - `llvm/lib/Target/X86/X86TargetTransformInfo.cpp:6203-6272`
  - `llvm/lib/Target/X86/X86TargetTransformInfo.cpp:6276-6302`

### Why the model looks suspicious

The x86 gather/scatter cost is explicitly documented as rough:

```cpp
// Return an average cost of Gather / Scatter instruction, maybe improved later.
InstructionCost X86TTIImpl::getGSVectorCost(...)
```

And the actual cost formula is:

```cpp
const int GSOverhead = (Opcode == Instruction::Load) ? getGatherOverhead()
                                                     : getScatterOverhead();
return GSOverhead + VF * getMemoryOpCost(Opcode, SrcVTy->getScalarType(),
                                         Alignment, AddressSpace, CostKind);
```

That formula is too blunt for the patterns we observed:

- It treats gather/scatter mostly as a fixed overhead plus per-lane scalar memory cost.
- It does not directly model shuffle/pack sequences that appear when legal vector width splits.
- It does not directly model extra instructions needed to combine split halves after legalization.

There is some split handling:

```cpp
InstructionCost::CostType SplitFactor =
    std::max(IdxsLT.first, SrcLT.first).getValue();
if (SplitFactor > 1)
  return SplitFactor * getGSVectorCost(...);
```

But this still recursively scales the same coarse gather cost; it does not add the actual glue cost that shows up in asm, such as pack/merge instructions.

### Benchmarks explained by this path

- `s2101`
  - diagonal memory access
  - not consecutive, not interleaved in a profitable way
  - ends up in gather/scatter vs scalarization
  - profile winner is `fixed:1`, consistent with gather/scatter being overvalued
- `s4112`
  - true indirect access `b[indx[i]]`
  - profile winner is `fixed:4`, not `fixed:8`
  - consistent with wide gather cost being underestimated relative to narrower gather
- `s4117`
  - `c[i/2]` is not generic random gather; it has pairwise reuse
  - cost path sees gather legality, not semantic reuse
  - profile winner `fixed:2` suggests generic wide gather cost is too optimistic
- `s111`, `s128`
  - sparse-lane store side becomes scatter-heavy
  - x86 cost path does not seem to fully charge the shuffle + split-scatter lowering

## Cause 2: RISCV RVV Gather/Strided Cost Undercounts Real Vector Overhead

This explains why emulate-side winners are so often `fixed:1`.

### Relevant code path

- Gather/scatter cost:
  - `llvm/lib/Target/RISCV/RISCVTargetTransformInfo.cpp:1179-1202`
  - `RISCVTTIImpl::getGatherScatterOpCost`
- Strided load/store cost:
  - `llvm/lib/Target/RISCV/RISCVTargetTransformInfo.cpp:1247-1274`
  - `RISCVTTIImpl::getStridedMemoryOpCost`
- EVL/scalable lowering used by VPlan:
  - `llvm/lib/Transforms/Vectorize/VPlanRecipes.cpp:3652-3677`
  - `VPWidenLoadEVLRecipe::execute`
  - `llvm/lib/Transforms/Vectorize/VPlanRecipes.cpp:3748-3777`
  - `VPWidenStoreEVLRecipe::execute`

### Why the model looks suspicious

RISCV gather/scatter cost is basically lane-count based:

```cpp
unsigned NumLoads = getEstimatedVLFor(&VTy);
return NumLoads * TTI::TCC_Basic;
```

Likewise strided memory cost is modeled as:

```cpp
InstructionCost MemOpCost =
    getMemoryOpCost(Opcode, VTy.getElementType(), Alignment, 0, CostKind, ...);
unsigned NumLoads = getEstimatedVLFor(&VTy);
return NumLoads * MemOpCost;
```

This is likely too cheap for the generated RVV code we observed, because it does not directly account for:

- repeated `vsetvli`
- active-lane / EVL setup
- index-vector synthesis such as `vid.v`
- address scaling / widening before indexed loads
- mask creation / `vmerge` plumbing
- extra vector control instructions around predicated memory ops

Those costs are exactly what dominated the emulator output in the benchmark investigation.

### Benchmarks explained by this path

- `s2101`, `s4112`
  - indirect or diagonal indexed accesses
  - emulate winner `fixed:1`
  - consistent with RVV indexed memory being under-costed
- `s4117`
  - pairwise-reuse pattern is treated like generic indexed access
  - emulate winner `fixed:1`
- `s111`, `s128`
  - sparse/strided lane patterns
  - emulate winner `fixed:1`
  - consistent with RVV VP/strided memory path being too cheap in TTI
- `s1115`
  - transposed access can become one strided stream plus regular loads
  - even there, emulate still preferred `fixed:1`, suggesting setup/control overhead is overweight in reality but underweighted in model

## Cause 3: Predication / If-Conversion CFG Cost Is Underestimated

This is the clearest explanation for `s2710` and `s279`, and part of `s276`.

### Relevant code path

- Basic legality for predicated blocks:
  - `llvm/lib/Transforms/Vectorize/LoopVectorizationLegality.cpp:1434-1447`
  - `blockNeedsPredication`
  - `llvm/lib/Transforms/Vectorize/LoopVectorizationLegality.cpp:1500-1617`
  - `canVectorizeWithIfConvert`
- Cost-model classification:
  - `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:3038-3050`
  - `isPredicatedInst`
  - `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:5189-5241`
  - `collectInstsToScalarize`
  - `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:5244-5363`
  - `computePredInstDiscount`
  - `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp:5366-5424`
  - `expectedCost`
- VPlan predication / CFG flattening:
  - `llvm/lib/Transforms/Vectorize/VPlanPredicator.cpp:90-129`
  - `createEdgeMask`
  - `llvm/lib/Transforms/Vectorize/VPlanPredicator.cpp:131-157`
  - `createBlockInMask`
  - `llvm/lib/Transforms/Vectorize/VPlanTransforms.cpp:487-528`
  - `createReplicateRegion`

### Strongest code-level evidence

The branch-on-mask recipe is currently costed as zero:

```cpp
InstructionCost VPBranchOnMaskRecipe::computeCost(ElementCount VF,
                                                  VPCostContext &Ctx) const {
  // The legacy cost model doesn't assign costs to branches for individual
  // replicate regions. Match the current behavior in the VPlan cost model for
  // now.
  return 0;
}
```

That is a direct undercount for branchy predicated VPlan regions.

Meanwhile, actual CFG predication work is nontrivial:

- edge masks are built in `createEdgeMask`
- block masks are ORed in `createBlockInMask`
- predicated recipes are wrapped into triangular regions in `createReplicateRegion`

So the transform is not free, but an important piece of it is currently modeled as free.

### Why this matters for the observed benchmarks

`s2710` and `s279` both had default vector code that computed both sides of branches, then merged or masked the results. That is exactly the outcome of if-conversion plus predicated vector lowering. The scalar `fixed:1` winner suggests LLVM undercharged:

- branch-on-mask / replicate-region structure
- mask creation and propagation
- extra select/blend/merge work
- repair loads/stores after predicated paths

`s276` is a weaker version of the same issue: simpler control flow, so vector predication still sometimes wins, but it is in the same code family.

## Cause 4: The Model Knows Access Classes, Not Semantic Patterns

This explains why `s4117` and odd-lane cases like `s111` / `s128` are misranked even when legality is technically correct.

### Relevant code path

- Consecutive check:
  - `llvm/lib/Transforms/Vectorize/LoopVectorizationLegality.cpp:474-488`
  - `isConsecutivePtr`
- Uniform check:
  - `llvm/lib/Transforms/Vectorize/LoopVectorizationLegality.cpp:586-616`
  - `isUniform`
- Uniform memop check:
  - `llvm/lib/Transforms/Vectorize/LoopVectorizationLegality.cpp:619-628`
  - `isUniformMemOp`
- Interleave discovery:
  - `llvm/lib/Analysis/VectorUtils.cpp:1438-1740`
  - `InterleavedAccessInfo::analyzeInterleaving`

### Why this matters

These analyses classify memory as:

- consecutive
- uniform
- interleaved / strided
- gather/scatter

But they do not understand richer semantics such as:

- pairwise reuse: `c[i/2]`
- every-other-lane live update
- duplicated index structure that could be scalar-loaded and broadcast cheaply

So the cost model can easily do the following:

- reject regular widen because it is not consecutive
- accept gather/scatter because it is legal
- never realize that "scalar load + broadcast" or "narrower VF with packing" is the structurally better choice

That matches:

- `s4117`: `c[i/2]` is treated like generic gather, but real best code uses reuse-friendly narrowing
- `s111`, `s128`: odd-lane work gets modeled as vector memory ops plus shuffles/scatters, even though the useful lane density is sparse

## Where the Wrong Decision Is Made

The concrete decision point is [LoopVectorize.cpp](/Users/cheolwanpark/Documents/Lab/code-lab/vplan-cost-measure/llvm-project/llvm/lib/Transforms/Vectorize/LoopVectorize.cpp#L5883) in `setCostBasedWideningDecision()`.

For non-consecutive accesses, LLVM compares:

- `InterleaveCost`
- `GatherScatterCost`
- `ScalarizationCost`

using this logic:

```cpp
if (InterleaveCost <= GatherScatterCost &&
    InterleaveCost < ScalarizationCost)
  Decision = CM_Interleave;
else if (GatherScatterCost < ScalarizationCost)
  Decision = CM_GatherScatter;
else
  Decision = CM_Scalarize;
```

So if the target TTI underestimates gather/scatter or predicated vector memory, that directly propagates into:

- the per-instruction widening decision
- total loop `expectedCost`
- final VF chosen by [LoopVectorize.cpp](/Users/cheolwanpark/Documents/Lab/code-lab/vplan-cost-measure/llvm-project/llvm/lib/Transforms/Vectorize/LoopVectorize.cpp#L7375) `computeBestVF()`

## Most Plausible Benchmark-to-Bug Mapping

- `s2101`
  - likely bug: x86 and RVV gather/scatter cost too low
  - evidence: diagonal stride became expensive indexed vector memory in practice
- `s4112`
  - likely bug: wide indirect gather too cheap in TTI
  - evidence: profile prefers narrower gather; emulate prefers scalar
- `s4117`
  - likely bug: gather cost path misses pairwise-reuse semantics
  - evidence: generic indexed path chosen; reuse-aware narrowed/scalar path wins
- `s111`, `s128`
  - likely bug: sparse-lane scatter/interleave cost too low, especially on wide VF
  - evidence: wide vector forms generate extra shuffle/split-scatter work
- `s2710`, `s279`
  - likely bug: predicated CFG / if-conversion cost too low
  - evidence: branchy scalar loops beat masked vector execution
- `s276`
  - likely bug: mixed case
  - evidence: some gather-like memory cost plus some predication cost both likely undercounted
- `s1115`
  - likely bug: transposed irregular operand cost too low, plus loop-shape sensitivity not modeled

## Practical Patch Targets

If we want to improve ranking for this benchmark family, the most promising places to patch are:

1. `llvm/lib/Target/X86/X86TargetTransformInfo.cpp`
   - `getGSVectorCost`
   - `getGatherScatterOpCost`
2. `llvm/lib/Target/RISCV/RISCVTargetTransformInfo.cpp`
   - `getGatherScatterOpCost`
   - `getStridedMemoryOpCost`
3. `llvm/lib/Transforms/Vectorize/VPlanRecipes.cpp`
   - `VPBranchOnMaskRecipe::computeCost`
4. `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp`
   - `setCostBasedWideningDecision`
   - `computePredInstDiscount`
   - possibly add a narrow-VF bias for sparse-lane / duplicated-index patterns

## Bottom Line

The current code strongly suggests the ranking errors are caused by under-modeled overhead, not by failed legality.

The clearest code-level grounds are:

- x86 gather cost is explicitly a rough average model
- RVV gather/strided cost is basically lane-count based
- `VPBranchOnMaskRecipe::computeCost()` is literally zero
- semantic patterns like `i/2` reuse or odd-lane-only usefulness are not represented in the memory classification path

That combination is enough to explain why the oracle winners in this repo are often:

- narrower fixed VFs on x86
- `fixed:1` on RVV/emulate

even though the default vectorizer cost path initially preferred wider vector forms.
