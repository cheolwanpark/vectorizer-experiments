# CLAUDE.md - Benchmark Execution (run/)

## Overview

A directory for running simple RVV micro-benchmarks on various hardware targets and measuring performance.

**Core Principle**: Users only need to focus on **kernel code, hardware, and compilation config**. Everything else is automated.

## Directory Structure

```
run/
├── CLAUDE.md           # This file
├── build-kernel        # Main build/run script
├── Makefile            # Alternative make-based build
├── src/                # Kernel source files
│   └── example.c       # Example kernel (s271-based)
├── common/             # Shared code
│   ├── common.h        # Kernel include header
│   ├── types.h         # Type definitions
│   ├── arrays.h/c      # Test arrays
│   ├── harness.c       # Standard harness (tohost/fromhost)
│   └── harness_t1.c    # T1-specific harness
├── crt/                # C runtime startup files
│   ├── crt_rv64.S      # RV64 CRT
│   └── crt_rv32.S      # RV32 CRT
├── link/               # Linker scripts
│   ├── link_rv64.ld    # RV64 linker
│   └── link_rv32.ld    # RV32 linker
├── targets/            # Per-target configuration
│   ├── saturn.sh       # Saturn config
│   ├── ara.sh          # Ara config
│   ├── t1.sh           # T1 config
│   ├── xiangshan.sh    # XiangShan config
│   ├── spike.sh        # Spike ISA sim
│   └── c910.sh         # C910 config
└── out/                # Build output directory
```

## Kernel Writing Convention

Kernel sources (`src/*.c`) must contain **only pure kernel logic**.

### Example: src/example.c

```c
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        if (b[i] > (real_t)0.)
            a[i] += b[i] * c[i];
    }
}
```

### Guidelines

- `#include "common.h"` is mandatory (includes types, arrays)
- Define `void kernel(void)` function
- Use `LEN_1D` macro (defined at build time)
- Global arrays `a[]`, `b[]`, `c[]` etc. are available (defined in arrays.c)
- initialise_arrays, checksum, etc. are not needed - harness handles these

## Usage

### build-kernel Script (Recommended)

```bash
./build-kernel <target> <source.c> [options]
```

**Targets**: spike, saturn, ara, xiangshan, t1, c910

**Options**:
| Option | Description | Default |
|--------|-------------|---------|
| `--lmul=N` | LMUL value (1,2,4,8) | 1 |
| `--len=N` | LEN_1D array size | 1000 |
| `--output=FILE` | Output ELF path | auto |
| `--asm` | Generate assembly output | - |
| `--llvm=FLAGS` | Additional LLVM flags | - |
| `--cflags=FLAGS` | Additional C flags | - |

### Examples

```bash
# Build only
./build-kernel saturn src/example.c --lmul=2

# Generate assembly to check vectorization
./build-kernel saturn src/example.c --lmul=4 --asm

# Different array size
./build-kernel saturn src/example.c --lmul=2 --len=10000
```

## Running Simulations

After building, use `run-sim.sh` for simulation execution:

```bash
# Run ELF directly
./run-sim.sh saturn run/out/example_saturn_lmul2.elf

# Build+run from source file (internally calls build-kernel)
./run-sim.sh saturn run/src/example.c --lmul=2

# With options
./run-sim.sh saturn src/example.c --lmul=4 --len=10000 --timeout=300

# Compare multiple LMULs
for lmul in 1 2 4 8; do
    ./run-sim.sh saturn run/src/example.c --lmul=$lmul
done

# List available simulators
./run-sim.sh --list
```

### Makefile (Legacy)

```bash
make KERNEL=example LMUL=2 saturn
```

## Target Configuration

Each target's settings are defined in `targets/<target>.sh`.

### Key Variables

```bash
TARGET_ARCH="rv64gcv"           # -march value
TARGET_ABI="lp64d"              # -mabi value
TARGET_CC="clang"               # Compiler
TARGET_CC_FLAGS=""              # Extra CC flags
TARGET_CRT="crt/crt_rv64.S"     # CRT file
TARGET_LD="link/link_rv64.ld"   # Linker script
TARGET_SIM="..."                # Simulator binary
TARGET_SIM_ARGS="..."           # Simulator arguments
TARGET_LOADMEM=1                # LOADMEM support (0/1)
TARGET_VLEN=512                 # Vector length
TARGET_NIX=0                    # Nix-based build (T1)
```

### Target-specific Notes

| Target | Notes |
|--------|-------|
| Saturn | LOADMEM=1, fast simulation. `+permissive +max_core_cycles=N` |
| Ara | LOADMEM=1 |
| T1 | Nix-based, **rv32gcv** (not rv64), Verilator plusarg format |
| XiangShan | Large-scale RTL, slow simulation |
| Spike | ISA simulator, fast, for accuracy verification |
| C910 | Requires .pat file conversion |

### Simulator CLI Formats

**Important**: Different simulators use different CLI argument formats:

| Simulator | Format | Example |
|-----------|--------|---------|
| Saturn/Ara | Verilator plusarg | `+loadmem=file.elf +max_core_cycles=1000000` |
| T1 | Verilator plusarg | `+t1_elf_file=file.elf +t1_timeout=1000000` |
| XiangShan | Standard CLI | `--img file.bin --max-cycles 1000000` |
| Spike | Standard CLI | `--isa=rv64gcv file.elf` |

### Verbose/Trace Support

| Simulator | Verbose Method | Output Type |
|-----------|---------------|-------------|
| Saturn/Ara | `+verbose \| spike-dasm` | Instruction trace with disassembly |
| XiangShan | `--dump-commit-trace` | Commit trace |
| T1 | `RUST_LOG=TRACE` | RTL events only (no instruction trace) |
| Spike | `-l` | Instruction trace |

**Note**: T1 does not support instruction-level trace. Use spike (rv32gcv) or ELF disassembly for instruction analysis.

## Output Format

Information displayed during execution:

```
Building: example (target=saturn, lmul=2)
Output: out/example_saturn_lmul2.elf
Running on saturn...
Status:    PASS
Exit code: 0
Wall time: 93.35s
Kernel:    3,150 cycles      ← Primary metric (harness measured)
Total sim: 354,556 cycles    ← Total simulation cycles
Sim speed: 3.8 kHz
```

**Mandatory Reporting Items**:
1. **Kernel cycles** - Actual kernel execution time (measured by harness using `rdcycle()`)
2. **Wall time** - Actual simulation time in seconds (measured by `run-sim.sh`)

### Kernel Cycles vs Total Simulation Cycles

| Metric | Description | Source |
|--------|-------------|--------|
| **Kernel cycles** | Time spent in `kernel()` function only | Harness: `rdcycle()` before/after `kernel()` |
| **Total sim cycles** | Entire simulation including init, warmup, checksum | Simulator output |

**Important**: Always report **kernel cycles** for performance comparison, not total simulation cycles.

### Kernel Cycles Extraction by Target

| Target | Harness | Output Method | Extraction |
|--------|---------|---------------|------------|
| Saturn | `harness.c` | tohost/fromhost stdout | spike-dasm trace: `csrr REG, mcycle` |
| XiangShan | `harness_xiangshan.c` | `measured_cycles` variable | Commit trace: `inst b00XXXXX` (mcycle CSR) |
| T1 | `harness_t1.c` | UART (0x10000000) | rtl-event.jsonl: s0/s1 RegWrite pattern |

`run-sim.sh` automatically parses kernel cycles from traces and displays "Kernel: N cycles".

## Batch Benchmark Example

Example comparing 4 targets across LMULs (32 data points):

```bash
#!/bin/bash
for target in saturn ara t1 xiangshan; do
    for lmul in 1 2 4 8; do
        echo "=== $target lmul=$lmul ==="
        ./run-sim.sh $target run/src/example.c --lmul=$lmul
    done
done
```

**Result Format Example**:

| Target | LMUL=1 | LMUL=2 | LMUL=4 | LMUL=8 |
|--------|--------|--------|--------|--------|
| Saturn | 1234 (0.5s) | 890 (0.5s) | 678 (0.5s) | 567 (0.6s) |
| Ara | ... | ... | ... | ... |
| T1 | ... | ... | ... | ... |
| XiangShan | ... | ... | ... | ... |

## Adding New Kernels

1. Create new kernel file in `src/` (e.g., `src/s271.c`)
2. Add `#include "common.h"`
3. Implement `void kernel(void)` function
4. Test: `./build-kernel spike src/s271.c --run`

## Adding New Targets

1. Create `targets/<newtarget>.sh`
2. Define required variables (see Key Variables above)
3. If needed, add target-specific files to `crt/`, `link/`, `common/`

## Troubleshooting

### Simulation timeout
- Increase `max_core_cycles` in `TARGET_SIM_ARGS`

### Verify vectorization
```bash
./build-kernel saturn src/example.c --asm
# Check for vsetvli, vadd, vmul, etc.
```

### Targets without LOADMEM support
- Check ELF loading method (TARGET_LOADMEM=0)
- Some targets require .bin or .pat conversion

### T1 simulation fails or shows wrong cycle count
- **Symptom**: T1 sim exits immediately or shows unexpectedly low cycles
- **Possible causes**:
  1. Wrong plusarg format (use `+t1_elf_file=`, not `--elf=`)
  2. Missing DRAMSim3 config (add `+t1_dramsim3_cfg=no` to disable)
  3. Kernel built with wrong LEN_1D (check with `llvm-objdump -d`)
- **Verify**: Check for `0x3e8` (1000) in disassembly for default LEN_1D

### T1 build fails silently
- **Symptom**: `build-kernel t1 ...` exits with no output
- **Cause**: Nix toolchain resolution fails
- **Check**: Ensure `RVV_ROOT` points to project root (not parent)
- **Verify**: `nix build /path/to/t1#rv32-stdenv.cc --no-link --print-out-paths`

## Agent Instructions

1. **When writing kernels**: Only pure kernel in `src/`, never include harness code
2. **When changing build method**: Update `build-kernel` script
3. **When adding new targets**: Create `targets/<name>.sh`
4. **When reporting results**: Include both cycles AND simulation time
5. **When comparing LMULs**: Run all 1,2,4,8 and organize in table format
