# CLAUDE.md - RVV-POC Project

## Overview

A simulation setup for running various RISC-V RVV vectorization benchmarks on multiple open-source RVV RTL units to measure performance.

**Core Goal**: Execute benchmarks across various open-source RVV RTL units to identify diverse research hypotheses.

### Research Questions

1. **Optimal Compilation Options per Architecture**: Different benchmarks may have different optimal compilation options (specific instruction usage, LMUL values, etc.)
2. **HW-aware Optimization**: Leverage deep architectural understanding of RVV RTL to identify particularly fast/slow instructions and HW-aware optimization points for compiler integration

## Project Structure

```
rvv-poc/
├── CLAUDE.md           # This file - project overview
├── setup.sh            # Reproducible environment setup
├── build.sh            # Build orchestration
├── env.sh              # Environment variables
├── scripts/            # Build scripts for each target
│   ├── build_chipyard.sh   # Saturn (Chipyard) build
│   ├── build_llvm.sh       # LLVM toolchain
│   ├── build_t1.sh         # T1 (Nix-based)
│   └── build_xiangshan.sh  # XiangShan build
├── artifacts/          # Build artifacts
│   └── build_vicuna.sh     # Vicuna build script
├── run/                # Benchmark execution (see run/CLAUDE.md)
├── chipyard/           # Chipyard (Saturn) submodule
├── XiangShan/          # XiangShan submodule
├── t1-micro58ae/       # T1 submodule
├── vicuna/             # Vicuna submodule (rv32 Zve32x)
├── llvm-project/       # LLVM source
├── llvm-build/         # LLVM build output
└── artifacts/          # Build artifacts
```

## Supported Targets

| Target | VLEN | Architecture | Build Method | Notes |
|--------|------|--------------|--------------|-------|
| Saturn | 512 | rv64gcv | Chipyard/Verilator | LOADMEM support, fast simulation (~4 kHz) |
| Ara | 512/4096 | rv64gcv | Chipyard/Verilator | LOADMEM support |
| T1 (blastoise) | 2048 | rv32gcv | Nix-based | Requires emurt library, DLEN=256 |
| XiangShan | 128 | rv64gcv | Mill + Verilator | Large-scale RTL |
| Vicuna | 512/1024 | rv32im_zve32x | Verilator (4.210+) | Integer-only vectors, **Needs Verilator upgrade** |

**Important**: Even same architectures may have different VLEN, DLEN, CPU cores, etc. Always specify the configuration.

## Simulator Setup Guidelines

### Build Optimization

- Build without modifying original RTL source code (unless absolutely necessary)
- Verilator RTL Build is slow, so maximize hardware parallelism
  - Recommended: Use `$nproc/2` cores with NUMA pinning
  - Example: `numactl --cpunodebind=0 --membind=0 make -j$(nproc)/2`

### Simulation Performance

- **Goal**: Minimum 30,000 cycles per minute for simple kernels
- Utilize VERILATOR_THREADS: `export VERILATOR_THREADS=$(( $(nproc) / 2 ))`
- Use LOADMEM option (for supported simulators)
- **Always report both simulation cycles AND wall-clock time (seconds)**

### Critical: Stack Size Requirement

**Issue**: Chipyard Verilator simulators (Saturn, Ara) require sufficient stack size for mmap operations during ELF loading. Without this, simulations fail with "No such device" error or hang at bootrom `wfi`.

**Solution**: Always set `ulimit -s 65536` (64MB stack) before running simulations.
- `run-sim.sh` automatically sets this for Chipyard targets
- For manual runs: `ulimit -s 65536 && ./simulator ...`

**Verified working configuration** (Saturn):
```bash
ulimit -s 65536 && ./simulator-chipyard.harness-REFV512D128RocketConfig \
    +permissive +max_core_cycles=200000 +loadmem=kernel.elf +verbose \
    +permissive-off kernel.elf
```
- Result: 155,506 cycles @ ~3.9 kHz (40 seconds wall time)

**Ara-specific notes**:
- Ara uses `rdtime` for `+max_core_cycles` timeout, not actual simulation cycles
- `run-sim.sh` automatically sets `+max_core_cycles=0` (disable timeout) for Ara
- **WARNING**: Verbose mode causes hang due to spike-dasm pipe blocking

### Inter-sim vs Intra-sim Parallelism (Open Question)

Experience shows that running multiple simulations with high verilator_threads causes interference and performance degradation.

**Trade-off**:
- Increase individual simulation parallelism (faster single simulation)
- vs. Utilize 96 cores for higher simulation throughput with slower individual sims

Quantitative analysis is a future task.

## Benchmarks

See `run/CLAUDE.md`. Core principles:
- Measure simple micro-benchmark level kernels
- Source C contains only the kernel; other parts (linker, CRT, HW-specific) are separated
- Users only need to focus on: kernel code, hardware, and compilation config

## Meta Rules (Critical)

### Reproducibility

1. **When changing setup**: Must reflect in `setup.sh` or `scripts/*.sh`
2. **When changing benchmark builds**: Reflect in `run/` scripts
3. **Maintain reproducibility for every task, session, and commit**

### Problem Solving

- If setup has issues, must reflect in reproducible scripts
- If blocked in a session, explore solutions via skills, subagents, etc.

---

## Documentation Maintenance

Use `/reflect` skill after significant debugging sessions or task completion to:
- Capture learnings and add to appropriate documentation
- Fix outdated/incorrect content in CLAUDE.md and agent files
- Remove duplicates and resolve conflicts

## Quick Start

```bash
# 1. Environment setup
source env.sh

# 2. Build a target (e.g., Saturn)
./scripts/build_chipyard.sh

# 3. Run a benchmark (from project root)
./run-sim.sh saturn run/src/s271/manifest.yaml --lmul=2 --len=4096
```

## Agent Instructions

When working on this project:

1. **Before building**: Check the corresponding `scripts/build_*.sh`
2. **Running benchmarks**: Refer to `run/CLAUDE.md`
3. **Reporting results**: Include both cycle count AND actual simulation time
4. **Making changes**: Always reflect in scripts to maintain reproducibility

---

## Failure Records

### Issue: T1 Simulator CLI Format Mismatch (2026-01-14)
- **Symptoms**: T1 simulation failed with "Assertion failed: +t1_elf_file must be set"
- **Root Cause**: `run-sim.sh` used standard CLI format (`--elf=path`) instead of Verilator plusarg format (`+t1_elf_file=path`)
- **Solution**: Rewrote `run_t1_sim()` function to use correct plusarg format, added `+t1_dramsim3_cfg=no`
- **Abstracted Learning**:
  > Verilator-based simulators use plusarg format (`+option=value`), not standard CLI format (`--option=value`). Always verify the actual CLI interface of each simulator before implementing automation scripts.
- **Documentation Updates**: `run/CLAUDE.md` - Added "Simulator CLI Formats" and "Verbose/Trace Support" tables

### Issue: build-kernel RVV_ROOT Path Bug (2026-01-14)
- **Symptoms**: T1 build failed silently, Nix couldn't find T1 flake
- **Root Cause**: `RVV_ROOT` was set to `${SCRIPT_DIR}/../..` (resolves to `/root`) instead of `${SCRIPT_DIR}/..` (resolves to `/root/rvv-poc`)
- **Solution**: Fixed path in `run/build-kernel:5`
- **Abstracted Learning**:
  > When using relative paths in scripts, always verify the resolved absolute path. Use `realpath` with explicit verification when paths are critical for submodule/toolchain resolution.
- **Documentation Updates**: `run/CLAUDE.md` - Added T1 troubleshooting section

### Issue: Ara Simulation Extremely Slow (2026-01-14, Resolved 2026-01-26)
- **Symptoms**: Ara simulation times out (>10min) for example.c even with small LEN_1D
- **Resolution (2026-01-26)**: Retested with s271_int.c, LEN_1D=4096 completed in ~1 minute
  - Previous slow performance may have been due to other system factors
- **Added Config**: `V512Ara2LaneRocketConfig` in `chipyard/generators/ara/chipyard/AraConfigs.scala`
- **Note**: Verbose mode still causes hang due to spike-dasm pipe blocking
- **Status**: RESOLVED

### Issue: Vicuna Requires Verilator 4.210+ (2026-01-22)
- **Symptoms**: Vicuna build fails with "Expecting expression to be constant" errors
- **Root Cause**: Ubuntu 22.04 apt provides Verilator 4.038, but Vicuna RTL uses SystemVerilog features only supported in Verilator 4.210+
  - Specifically: package-defined constant arrays as parameter defaults
- **Current Setup**:
  - All configuration files created and ready:
    - `artifacts/build_vicuna.sh` - Build script
    - `run/targets/vicuna.sh` - Target configuration
    - `run/crt/crt_vicuna.S` - RV32 CRT startup
    - `run/link/link_vicuna.ld` - Linker script
    - `run/common/harness_vicuna.c` - Simulation harness
  - `run/src/s271/` - Example hand-written kernel workload
  - `sim-configs.yaml` and `run-sim.sh` updated with Vicuna support
- **Solution Required**: Install Verilator 4.210+ from source
  ```bash
  git clone https://github.com/verilator/verilator
  cd verilator && autoconf && ./configure && make -j$(nproc) && sudo make install
  ```
- **Vicuna Key Characteristics**:
  - ISA: `rv32im_zve32x` (integer-only vectors, NO floating-point)
  - VLEN: 512 or 1024 bits (configurable via `--vreg-w`)
  - Termination: `jr x0` (fetch address 0 ends simulation)
  - UART: 0xFF000000 for stdout output
- **Abstracted Learning**:
  > When integrating new RTL projects, always check Verilator version requirements upfront. SystemVerilog feature support varies significantly between Verilator versions.
- **Status**: BLOCKED - Waiting for Verilator upgrade

### Issue: Kernel Cycles Parsing Varies by Target (2026-01-22)
- **Symptoms**: XiangShan and T1 simulations showed only "Total sim cycles", not actual kernel execution cycles
- **Root Cause**: Each target has different harness and trace output mechanisms
  - Saturn: tohost/fromhost stdout captured by spike-dasm
  - XiangShan: No stdout mechanism; `harness_xiangshan.c` stores cycles in memory variable
  - T1: UART output (0x10000000) not captured by simulator
- **Solution**: Parse kernel cycles from trace files for each target
  - **Saturn**: spike-dasm output, pattern: `csrr REG, mcycle` with register value
  - **XiangShan**: commit trace, pattern: `inst b00XXXXX` (mcycle CSR read), data field contains value
  - **T1**: rtl-event.jsonl, pattern: s0/s1 RegWrite where value ≈ sim_cycle (mcycle read), then subsequent small value (end-start)
- **Files Modified**:
  - `run-sim.sh`: Added `_parse_kernel_cycles_from_xiangshan_trace()` and `_parse_kernel_cycles_from_t1_rtl_event()`
  - `run/CLAUDE.md`: Updated Output Format section with kernel cycles extraction details
- **Abstracted Learning**:
  > Harness stdout may not be available in all simulators. Parse kernel timing from CSR read values in traces: find mcycle reads (inst starts with CSR number), extract register values, compute end-start.
- **Status**: RESOLVED - run-sim.sh now shows "Kernel: N cycles" for all targets

### Issue: XiangShan cycleCnt Comma Parsing Bug (2026-02-04)
- **Symptoms**: XiangShan simulation reported 93 cycles instead of 93,558
- **Root Cause**: `_parse_cycles_from_log()` regex used `\d+` which stopped at comma in `cycleCnt = 93,558`
- **Solution**: Changed all patterns to `[\d,]+` and added `.replace(",", "")`
- **Abstracted Learning**:
  > Numeric values in log output may contain locale-specific formatting (commas, dots). Always handle formatted numbers in parsers.
- **Status**: RESOLVED

### Issue: T1 Kernel Cycle Parser Picks Up Wrong Values (2026-02-05)
- **Symptoms**: T1 kernel cycles reported by `_parse_kernel_cycles_from_t1_rtl_event()` were wrong (e.g., 2 instead of 3,014)
- **Root Cause**: After kernel measurement writes `s1 = end_mcycle - start_mcycle`, the harness checksum computation writes progressively smaller values to s1. Parser picked up the last small s1 value instead of the actual kernel cycles.
- **Pattern in rtl-event.jsonl**:
  ```
  cycle=16008 s0=16008     ← start mcycle (rdcycle)
  cycle=19022 s1=19022     ← end mcycle (rdcycle)
  cycle=19101 s1=3014      ← kernel cycles (correct: end-start)
  cycle=19113 s0=...       ← checksum computation begins
  cycle=19168 s1=2411      ← checksum values...
  cycle=19402 s1=2         ← parser wrongly picked this
  ```
- **Correct parsing**: Find s0 write where value ≈ cycle (rdcycle), then first s1 write where value ≈ cycle (rdcycle), compute difference.
- **Impact**: ALL previous T1 kernel cycle data from the broken parser is unreliable
- **Abstracted Learning**:
  > When parsing register trace events for specific values, be aware that the same registers are reused for different purposes throughout execution. Match the architectural pattern (rdcycle → register value ≈ simulation cycle) rather than searching for "small values."
- **Status**: KNOWN - Parser needs rewrite; independent parser in `/tmp/claude-0/parse_t1_kernel_cycles.py` produces correct values

### Issue: T1 Config Misidentification (2026-02-04)
- **Symptoms**: T1 was documented as VLEN=1024 (default config) in CLAUDE.md Supported Targets table
- **Root Cause**: The nix flake target `".#t1.blastoise.t1rocketemu.verilator-emu"` builds the blastoise config (VLEN=2048, DLEN=256), not the default config (VLEN=1024)
- **Verification**: Traced nix derivation chain → `t1/designs/.../T1RocketTile.toml` → blastoise uses `zvl2048b`
- **Solution**: Updated CLAUDE.md target table to show T1 blastoise VLEN=2048
- **Abstracted Learning**:
  > When using nix-based builds, the actual hardware configuration is determined by the flake target path, not by a "default" config name. Always verify the config by tracing through the derivation chain.
- **Status**: RESOLVED

### Issue: Incomparable Data from Mixed LEN Builds (2026-02-05)
- **Symptoms**: s000 T1 LMUL=1 appeared faster (3,014 cycles) than LMUL=2 (3,483) despite processing fewer elements per iteration
- **Root Cause**: LMUL=1 ELF was rebuilt separately with LEN=100, while LMUL=2,4,8 used LEN=4096. File timestamps confirmed different build times.
- **Verification**: Disassembly showed LMUL=1 processes 100 elements total, LMUL=4 processes 4096
- **Abstracted Learning**:
  > Always specify `--len=N` explicitly in every build/run command. Never compare kernel cycles across runs without verifying identical LEN. Check `start_mcycle` (init time) as a quick sanity check — significantly different init times indicate different array sizes.
- **Status**: RESOLVED (documentation added to README.md)

### Issue: Ocelot (Bobcat) Removed (2026-02-08)
- **Summary**: Ocelot (Tenstorrent riscv-ocelot, BOOMv3+RVV) was removed from the project after extensive Verilator bringup attempts all failed. The BOOM+OVI pipeline never committed a single instruction under Verilator. Tested: firtool 1.59.1/1.75.0, randReset 0/2, assertions on/off, --x-assign unique, multiple workloads — all identical hang.
- **Root Cause**: Ocelot targets VCS (commercial simulator), not Verilator.
- **Abstracted Learning**:
  > Before investing in Verilator bringup for third-party RTL, check which simulator the project officially supports. Some BOOM+vector extensions may only be validated against commercial simulators.
- **Status**: REMOVED - submodules, scripts, and all references deleted
