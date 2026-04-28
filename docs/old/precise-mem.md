# Precise Memory Cost Model

LLVM 벡터라이저의 gather/scatter 및 strided memory 비용이 실제 코드 대비 과소평가되는 문제를 보정하기 위한 패치.

## LLVM Flags

| Flag | Type | Default | 설명 |
|------|------|---------|------|
| `-precise-mem-cost` | bool | false | 상세 비용 모델 활성화 게이트 |
| `-gather-scatter-overhead=N` | unsigned | 2 | gather/scatter per-element memory cost 곱연산 계수 |
| `-strided-mem-overhead=N` | unsigned | 1 | strided load/store per-element memory cost 곱연산 계수 |

clang에서는 `-mllvm` prefix 필요:

```
clang -mllvm -precise-mem-cost -mllvm -gather-scatter-overhead=3 ...
```

## 동작 모드

### `-precise-mem-cost` OFF (기본)

기존 LLVM 비용 모델이 그대로 사용된다. overhead 값을 설정해도 무시된다.

```
gather/scatter:  NumLoads × TCC_Basic (=1)
strided:         NumLoads × scalar_mem_cost
```

### `-precise-mem-cost` ON

상세 비용 모델이 활성화된다. 비용은 아래 세 항의 합이다.

## 비용 공식

### Gather/Scatter (`getGatherScatterOpCost`)

```
TotalCost = MemCost + SetupCost + TruncCost

MemCost   = NumLoads × LaneMemCost × GatherScatterOverhead
SetupCost = LT.first × getRISCVInstructionCost({VSETVLI, VID_V, VSLL_VI, [VMERGE_VVM]})
TruncCost = LT.first × getRISCVInstructionCost({VNSRL_WI})  (RV32에서 64-bit index인 경우만)
```

각 항의 의미:

| 항 | 의미 | 적용 방식 |
|----|------|-----------|
| MemCost | per-element 메모리 접근 비용 | overhead 값이 **곱연산**으로 적용 |
| SetupCost | 벡터 제어/인덱스 생성 비용 | legalized part 수에 비례, LMUL 민감 |
| TruncCost | RV32 인덱스 축소 비용 | RV64에서는 0 |

SetupCost의 instruction별 역할:

| Instruction | 역할 |
|-------------|------|
| `VSETVLI` | VL(vector length) 설정 |
| `VID_V` | 인덱스 벡터 생성 (0, 1, 2, ...) |
| `VSLL_VI` | 인덱스를 element 크기만큼 shift (스케일링) |
| `VMERGE_VVM` | masked gather에서 passthrough 값 merge (variable mask일 때만) |
| `VNSRL_WI` | 64-bit 포인터 인덱스를 32-bit로 축소 (RV32 전용) |

### Strided (`getStridedMemoryOpCost`)

```
TotalCost = MemCost + SetupCost

MemCost   = NumLoads × MemOpCost × StridedMemOverhead
SetupCost = LT.first × getRISCVInstructionCost({VSETVLI})
```

Gather/scatter와 달리 `VID_V`, `VSLL_VI`가 없다. `vlse`/`vsse`는 stride를 스칼라 레지스터로 받으므로 인덱스 벡터 생성이 불필요.

## LMUL 민감도

`getRISCVInstructionCost`의 default case가 `LMULCost`를 반환하므로, setup instruction들(VSETVLI, VID_V, VSLL_VI 등)은 자동으로 LMUL에 비례한다.

```
LMUL=1 → LMULCost=1 → SetupCost = LT.first × 3
LMUL=4 → LMULCost=4 → SetupCost = LT.first × 12
```

## Overhead 값 해석

Overhead는 per-element memory cost에 곱해지는 계수다. setup cost에는 영향을 주지 않는다.

- `gather-scatter-overhead=1`: 기존과 동일한 per-element 비용 (setup만 추가)
- `gather-scatter-overhead=2` (기본): per-element 비용 2배 (indexed memory가 contiguous보다 느린 것을 반영)
- `gather-scatter-overhead=3+`: 더 공격적으로 gather/scatter를 페널티

기본값 근거:
- Gather/scatter overhead 2: RVV indexed memory 명령어가 contiguous 대비 실제로 느린 것을 반영. AArch64 SVE는 기본값 10을 사용하지만, RVV는 아키텍처적으로 단일 명령어(vloxei/vsoxei)이므로 보수적으로 2.
- Strided overhead 1: `vlse`/`vsse`는 하드웨어에서 비교적 효율적. 추가 setup(VSETVLI)만으로 충분.

## Overhead 우선순위

CLI flag > Subtarget 기본값 순으로 적용된다.

```cpp
static unsigned getRVVGatherScatterOverhead(const RISCVSubtarget *ST) {
  if (RVVGatherScatterOverhead.getNumOccurrences() > 0)  // CLI flag 있으면 우선
    return RVVGatherScatterOverhead;
  return ST->getGatherScatterOverhead();                  // 없으면 Subtarget 기본값 (2)
}
```

## 비용 변화 예시

`<8 x double>` gather on RV64 (LMUL=1, `-riscv-v-fixed-length-vector-lmul-max=1`):

| 모드 | MemCost | SetupCost | Total |
|------|---------|-----------|-------|
| OFF | 8×1 = 8 | - | **8** |
| ON, overhead=2 | 8×1×2 = 16 | 1×(4+4+4) = 12 | **28** |
| ON, overhead=3 | 8×1×3 = 24 | 12 | **36** |
| ON, overhead=1 | 8×1×1 = 8 | 12 | **20** |

## Makefile 사용법

```bash
# 기본 (기존 동작, precise-mem-cost OFF)
make emulate-all

# 상세 비용 모델 활성화
make emulate-all LLVM_CUSTOM=llvm-project/build/bin PRECISE_MEM_COST=1

# Overhead 커스터마이즈
make vplan-explain s4112 PRECISE_MEM_COST=1 GATHER_SCATTER_OVERHEAD=3

# Strided도 조정
make emulate-all PRECISE_MEM_COST=1 GATHER_SCATTER_OVERHEAD=4 STRIDED_MEM_OVERHEAD=2
```

## 수정 파일

| 파일 | 변경 |
|------|------|
| `llvm/lib/Target/RISCV/RISCVTargetTransformInfo.cpp` | flag 선언, helper 함수, `getGatherScatterOpCost`, `getStridedMemoryOpCost` 분기 추가 |
| `llvm/lib/Target/RISCV/RISCVSubtarget.h` | `GatherScatterOverhead`, `StridedMemoryOverhead` 멤버 및 접근자 |
| `llvm/test/Analysis/CostModel/RISCV/fixed-vector-{gather,scatter}.ll` | PRECISE RUN line + CHECK lines |
| `llvm/test/Analysis/CostModel/RISCV/scalable-{gather,scatter}.ll` | PRECISE RUN line + CHECK lines |
| `scripts/llvm_pipeline.py` | `extra_cflags` param |
| `scripts/{vplan_explain,profile,emulate}.py` | `--extra-cflags` CLI arg |
| `scripts/{vplan_explain_all,profile_all,emulate_all}.py` | `extra_cflags` thread-through |
| `Makefile` | `PRECISE_MEM_COST`, `GATHER_SCATTER_OVERHEAD`, `STRIDED_MEM_OVERHEAD` 변수 및 help |
