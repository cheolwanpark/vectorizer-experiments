# Emulation and Cost-Model Limitations

This document summarizes the main limitations of using LLVM vectorization output together with RTL or emulator-based performance measurements.

## Scope

This repository combines two different kinds of information:

- LLVM middle-end decisions such as VF selection, vectorization remarks, and IR-level cost estimates.
- Emulator or RTL execution results such as kernel cycles, total simulation cycles, and observed performance on a concrete target.

These two layers are related, but they are not the same model.

## Main Principle

A compiler cost model is not a hardware simulator.

Even when LLVM is configured with the correct ISA family and vector length, its middle-end cost model is still only an approximation of hardware behavior. It can help rank candidates, but it does not guarantee that the selected VF or generated code will be the fastest on a specific microarchitecture.

## What Usually Matches

The setup is generally reliable for the following:

- Whether RVV code generation is legal for a target.
- Whether a loop is vectorized at all.
- Whether generated code broadly matches the target ISA profile.
- Whether vector width constraints such as `VLEN`, LMUL, and RVV legality are reflected in compilation.

If the target and the compiler agree on the ISA profile, the generated assembly is often directionally reasonable.

## What Can Diverge

The following can still differ from measured emulator results:

- VF ranking chosen by LLVM versus the true best VF on hardware.
- Relative performance between LMUL choices.
- Profitability of reductions, gathers, scatters, permutes, and mixed-width code.
- Sensitivity to load/store latency, bypass behavior, issue width, queue pressure, and pipeline structure.
- Performance effects from implementation details that LLVM does not model precisely.

In short, legality tends to transfer better than profitability.

## Why This Happens

There are several common reasons:

- LLVM may have no processor-specific scheduling model for the target CPU.
- A target may have a processor definition but still use a generic or incomplete performance model.
- The middle-end makes decisions using target transform information, not cycle-accurate simulation.
- Emulator results include concrete microarchitectural effects that are invisible at IR-level optimization time.
- Some passes use general heuristics that are only loosely tied to backend scheduling data.

## Practical Interpretation

When comparing `vplan-explain` output with emulator measurements:

- Treat LLVM cost as a heuristic signal, not as ground truth.
- Treat emulator cycle counts as the final authority for target-specific performance.
- Expect the compiler to be more trustworthy for "can this vectorize?" than for "which VF is truly optimal?".

## Implication for Target Configuration

When no target-specific performance model exists in LLVM, the best available setup is usually:

- match the ISA family,
- enable the relevant target features,
- and constrain vector length to the real hardware value.

This is still useful, but it should be understood as a closest available proxy, not a faithful microarchitectural model.

## Recommended Usage

- Use LLVM-derived VF candidates to narrow the search space.
- Use emulator results to validate or override LLVM profitability decisions.
- Be careful when drawing strong conclusions from small LLVM cost differences.
- Prefer measured cycle data when reporting target-specific performance claims.

## Bottom Line

This workflow is best understood as:

- LLVM for candidate generation and structural analysis.
- Emulator or RTL for actual performance validation.

If the two disagree, trust the measured result and treat the compiler model as an approximation that may need target-specific tuning or empirical correction.
