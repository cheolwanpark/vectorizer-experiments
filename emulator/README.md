# RVV-POC: RISC-V Vector Extension RTL Simulation Benchmark Suite

Run TSVC-style vectorization benchmarks on multiple open-source RVV RTL implementations and compare kernel-level performance across LMUL configurations.

## Supported Hardware Targets

| Target | VLEN | ISA | Scalar Core | Config |
|--------|------|-----|-------------|--------|
| **Saturn** | 512 | rv64gcv | Rocket | `REFV512D128RocketConfig` |
| **XiangShan** | 128 | rv64gcv | KunMingHu (v3) | `KunminghuV2Config` |
| **T1** | 2048 | rv32gcv | Rocket | `blastoise` (DLEN=256) |
| **Ara** | 512 | rv64gcv | Rocket | `V512Ara2LaneRocketConfig` |

## Initial Setup

```bash
# Build the container from the project root
cd .. && docker build -f Dockerfile .

# 1. Install dependencies, clone submodules, build LLVM toolchain (one-time, ~1hr)
./build.sh

# 2. Load environment variables (every new shell)
source env.sh

# 3. Build simulators (default: saturn, xiangshan, t1)
./build-sim.sh

# Or build a specific target only
./build-sim.sh saturn
./build-sim.sh xiangshan
./build-sim.sh t1
./build_gem5.sh
# ./build-sim.sh ara       not built by default
```

`build.sh` handles all prerequisites (apt packages, conda, nix, CIRCT/firtool, chipyard setup, LLVM).
After it completes, `source env.sh` and then `./build-sim.sh` to build the RTL simulators.

## Quick Start: Running a Benchmark

### Step 1: Write (or pick) a kernel

Kernel workloads live under categorized directories such as `run/src/tsvc/<bench>/`, `run/src/npb/<bench>/`, or `run/src/dlmul-synthesis/...`, with a `manifest.yaml` and local sources. A simple kernel source still looks like:

```c
// run/src/tsvc/s351/s351.c
#include "common.h"

void kernel(void) {
    real_t alpha = c[0];
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = alpha + b[i] * c[i];
    }
}
```

Existing workloads: `run/src/tsvc/s000/`, `run/src/tsvc/s271/`, `run/src/dlmul-synthesis/microbench/mb1_switch/`, `run/src/npb/npb_is_s/`, etc.

### Step 2: Run simulation

```bash
# Basic: one target, one LMUL
./run-sim.sh saturn run/src/examples/example/manifest.yaml --lmul=2 --len=4096

# Output:
#   Building: example (target=saturn, lmul=2)
#   ...
#   Status:    PASS
#   Kernel:    1,234 cycles    ← This is the metric you want
#   Total sim: 354,556 cycles
#   Sim speed: 3.8 kHz
```

### Step 3: Sweep across LMULs and targets

```bash
for target in saturn xiangshan t1; do
    for lmul in 1 2 4 8; do
        ./run-sim.sh $target run/src/tsvc/s351/manifest.yaml --lmul=$lmul --len=4096
    done
done
```

## Command Reference

### `run-sim.sh` — Build + Simulate + Parse cycles

```
./run-sim.sh <target> <manifest.yaml | source.c | elf> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--lmul=N` | LMUL value (1, 2, 4, 8) | 1 |
| `--len=N` | Array size (`LEN_1D`) | 1000 |
| `--timeout=N` | Wall-clock timeout (seconds) | 600 |
| `--max-cycles=N` | Simulation cycle limit | 100,000,000 |
| `--no-sim-verbose` | Disable verbose/trace output | (verbose on) |
| `--dry-run` | Print command without executing | - |
| `--log-dir=DIR` | Log output directory | `sim-logs/` |
| `--list` | Show available simulators | - |

**What it does internally:**
1. Calls `run/build-kernel` / `run/build-workload` to compile the workload sources → `.elf`
2. Launches the RTL Verilator simulator
3. Parses kernel cycles from trace output
4. Reports results

### `run/build-kernel` — Compile only (no simulation)

```
cd run
./build-kernel <target> <manifest.yaml | source.c> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--lmul=N` | LMUL value | 1 |
| `--len=N` | Array size | 1000 |
| `--asm` | Emit assembly (`.s`) instead of ELF | - |
| `--llvm=FLAGS` | Extra LLVM backend flags | - |
| `--cflags=FLAGS` | Extra C compiler flags | - |

**Useful for inspection:**
```bash
# Check vectorization — does it use the expected instructions?
cd run && ./build-kernel saturn src/s351/manifest.yaml --lmul=4 --asm
# → run/out/s351_saturn_lmul4.s

# Use -ffast-math to allow vfredusum instead of vfredosum
cd run && ./build-kernel saturn src/s311/manifest.yaml --lmul=2 --cflags="-ffast-math" --asm
```

### Using extra compiler flags (e.g. `-ffast-math`)

`run-sim.sh` does not pass `--cflags` to `build-kernel`. Pre-build the ELF, then pass it directly:

```bash
# Step 1: build with --cflags
cd run && ./build-kernel xiangshan src/s311/manifest.yaml --lmul=2 --len=4096 \
    --cflags="-ffast-math" --output=out/s311_ffast_xiangshan_lmul2.elf && cd ..

# Step 2: simulate the pre-built ELF
./run-sim.sh xiangshan run/out/s311_ffast_xiangshan_lmul2.elf
```

Loop version:
```bash
for lmul in 1 2 4 8; do
    cd run && ./build-kernel xiangshan src/s311/manifest.yaml --lmul=$lmul --len=4096 \
        --cflags="-ffast-math" --output=out/s311_ffast_xiangshan_lmul${lmul}.elf && cd ..
    ./run-sim.sh xiangshan run/out/s311_ffast_xiangshan_lmul${lmul}.elf
done
```

## Full Worked Example: s351 on 3 targets × 4 LMULs

```bash
#!/bin/bash
# Run s351 on saturn, xiangshan, t1 with LEN=4096, LMUL=1,2,4,8

KERNEL="run/src/s351/manifest.yaml"
LEN=4096

for target in saturn xiangshan t1; do
    echo "========== $target =========="
    for lmul in 1 2 4 8; do
        echo "--- LMUL=$lmul ---"
        ./run-sim.sh $target $KERNEL --lmul=$lmul --len=$LEN --timeout=300
        echo ""
    done
done
```

Expected output per run:
```
Building: s351 (target=saturn, lmul=4)
...
Status:    PASS
Kernel:    987 cycles
Total sim: 310,234 cycles
Sim speed: 3.5 kHz
```

Collect the **Kernel: N cycles** lines to build your comparison table.

## Output & Logs

Each simulation produces files in `sim-logs/`:

| File | Content |
|------|---------|
| `<kernel>_<target>_lmul<N>.log` | Simulator stdout |
| `<kernel>_<target>_lmul<N>.out` | Decoded trace (Saturn: spike-dasm) |
| `<kernel>_<target>_lmul<N>.trace` | Raw trace (XiangShan: commit trace) |
| `<kernel>_<target>_lmul<N>-rtl-event.jsonl` | T1 RTL events |
| `<kernel>_<target>_lmul<N>-sim_result.json` | Machine-readable results |

## Writing New Kernels

1. Create `run/src/<name>/manifest.yaml`
2. Add `run/src/<name>/<name>.c` with `#include "common.h"` and `void kernel(void)`
3. Use predefined arrays (`a[]`, `b[]`, `c[]`, `d[]`, `e[]`) and `LEN_1D`
4. No `main()`, no `printf`, no `#include <stdio.h>` for kernel-mode workloads — the harness handles everything

```c
#include "common.h"

void kernel(void) {
    // Your vectorizable loop here
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = b[i] + c[i] * d[i];
    }
}
```

Available global arrays (all `real_t`, size >= `LEN_1D`):
`a`, `b`, `c`, `d`, `e`, `aa` (2D), `bb` (2D), `cc` (2D)

Whole-program workloads are also supported with `entry.mode: "main"` in the manifest. Those run through the `main_harness_*` entry path and report whole-program cycles instead of kernel-only cycles.

## Important Notes

### LEN_1D consistency
Always specify `--len=` explicitly when comparing across LMUL or targets. The default is 1000, but forgetting `--len` on one run produces incomparable data.

### Simulation speed
Saturn is fastest (~4 kHz). XiangShan is slowest (~1 kHz). T1 is in between. Budget wall time accordingly — a single run typically takes 10-60 seconds for `LEN=4096`.

### T1 is rv32, not rv64
T1 uses `rv32gcv`. The toolchain and ABI differ from Saturn/XiangShan (`rv64gcv`). `build-kernel` handles this automatically via the Nix-based T1 toolchain.

### Stack size for Chipyard targets
Saturn and Ara require `ulimit -s 65536`. `run-sim.sh` sets this automatically.

## Project Layout

```
rvv-poc/
├── run-sim.sh          # Main entry point: build + simulate + report
├── sim-configs.yaml    # Simulator paths and configurations
├── run/
│   ├── build-kernel    # Compatibility build wrapper
│   ├── build-workload  # Manifest-driven workload builder
│   ├── src/            # Workload directories
│   ├── common/         # Shared headers, arrays, harness
│   ├── targets/        # Per-target build config
│   ├── crt/            # C runtime startup
│   ├── link/           # Linker scripts
│   └── out/            # Build artifacts (.elf, .s)
├── chipyard/           # Saturn/Ara simulator (submodule)
├── XiangShan/          # XiangShan simulator (submodule)
├── t1-micro58ae/       # T1 simulator (submodule)
├── llvm-build/         # LLVM toolchain
└── sim-logs/           # Simulation output logs
```
