# Dynamic LMUL Strategy

RVV loop body 안에서 LMUL을 하나로 고정하지 않고, low-pressure 구간에서는 큰 LMUL을 쓰고 high-pressure 구간에서는 작은 LMUL을 쓰는 전략을 정리한 문서.

핵심 가설은 다음과 같다.

- 큰 LMUL은 `VLMAX`를 키워 iteration 수와 loop overhead를 줄인다.
- 하지만 큰 LMUL은 vector register pressure를 키워 spill 가능성을 높인다.
- 따라서 loop 전체에 하나의 LMUL을 고정하는 것보다, loop body 내부 region별로 LMUL을 바꾸는 편이 더 나을 수 있다.

이 문서는 production compiler pass 설계가 아니라, 먼저 "어떤 기계 특성이 중요하고", "그 값을 어떻게 추정할 수 있고", "그 값을 바탕으로 어떤 asm-level LMUL switching 규칙을 만들 수 있는지"를 정리하는 데 목적이 있다.

## 중요한 기계 특성

Dynamic LMUL 효과는 아래 값들에 의해 결정된다.

| Feature | 의미 | 왜 중요한가 |
|---------|------|-------------|
| `VLEN` | 구현의 vector register bit width | 가능한 `VLMAX`와 LMUL 효과의 기본 규모를 결정 |
| Supported `LMUL` set | `mf8/mf4/mf2/m1/m2/m4/m8` 등 지원 범위 | 탐색 가능한 LMUL 후보를 결정 |
| `Cset(L1->L2)` | `vsetvli`로 LMUL을 바꿀 때 드는 cycle cost | switching 이득이 setup cost를 넘는지 판단 |
| `Bmem(L, Ns)` | LMUL `L`, memory stream 수 `Ns`에서의 sustained memory throughput | load/store dominated region의 최적 LMUL 추정 |
| `Talu(Op, L)` | simple ALU/FMA류의 throughput | compute region에서 LMUL 증가가 실제로 이득인지 판단 |
| `Twiden(Op, L)` | widening/narrowing/reduction 류의 throughput | widening 계열은 register pressure 민감도가 커서 별도 측정 필요 |
| `Pcliff(Class, L)` | 특정 code class에서 성능 cliff가 나타나는 effective pressure 임계값 | spill 또는 severe scheduling degradation 시작점 추정 |
| `Sspill(L)` | pressure cliff 이후의 성능 손실 크기 | 큰 LMUL의 위험 비용 모델링 |
| `Mmask(L)` | masked execution의 추가 비용 | predicate-heavy kernel이면 중요 |
| `Rfront(L)` | 큰 LMUL이 줄여주는 loop-control/front-end overhead | 짧은 body에서도 큰 LMUL이 유리할 수 있는 이유 |

실제로는 모든 값을 정확히 알 필요는 없고, 아래 세 가지 derived value만 잡혀도 충분하다.

- `Lmem*`: memory-dominated region에서 가장 좋은 LMUL
- `Lcmp*`: high-pressure compute region에서 가장 좋은 LMUL
- `Lwide*`: widening/reduction-heavy region에서 가장 좋은 LMUL

## Fractional LMUL

RVV의 LMUL은 `m1/m2/m4/m8` 같은 integer LMUL만 있는 것이 아니라, `mf2/mf4/mf8` 같은 fractional LMUL도 있다.

- integer LMUL은 한 logical vector value가 여러 register를 묶어 쓰는 경우다.
- fractional LMUL은 한 physical vector register를 여러 logical value가 나눠 쓰는 경우다.
- 따라서 fractional LMUL은 `VLMAX`를 줄이는 대신 register pressure를 낮추는 방향으로 작동한다.

예를 들어 `SEW=32`, `VLEN=128`이면:

- `m1`은 한 vector register group당 4 lane
- `m2`는 8 lane
- `m4`는 16 lane
- `m8`는 32 lane
- `mf2`는 2 lane
- `mf4`는 1 lane

즉, fractional LMUL은 "더 작은 vector length"라기보다 "더 작은 register footprint를 갖는 vector grouping"으로 이해하는 편이 정확하다.

이 문서의 dynamic LMUL 관점에서는 fractional LMUL을 다음처럼 해석하면 된다.

- `m2/m4/m8`: iteration 수와 front-end overhead를 줄이기 위해 쓰는 공격적인 선택
- `m1`: 기본 균형점
- `mf2/mf4/mf8`: register footprint를 더 줄여야 하는 고압력 구간에서 쓰는 보수적 선택

특히 mask-heavy 코드, 매우 좁은 element type와 큰 SEW 전환이 섞인 코드, 또는 widening/reduction 때문에 live range가 터지는 구간에서는 `m1`보다 더 작은 LMUL이 필요할 수 있다.

다만 대부분의 throughput-oriented kernel에서는 fractional LMUL이 `VLMAX`를 줄여 iteration 수를 늘리므로, 기본 후보는 여전히 `m1/m2/m4/m8`가 되고 fractional LMUL은 "pressure escape hatch"로 보는 편이 실용적이다.

## Effective Pressure 모델

register pressure는 단순히 "live vector 개수"만 세면 부족하다. widening 연산과 accumulator는 footprint가 더 크기 때문이다.

실험용 surrogate metric으로는 아래 정도면 충분하다.

```text
Peff = W(L) * (Nnorm + 2*Nwiden + Nacc + 0.5*Nmask) + Nextra
```

여기서 `W(L)`는 LMUL footprint weight다.

- `W(m8)=8`, `W(m4)=4`, `W(m2)=2`, `W(m1)=1`
- `W(mf2)=0.5`, `W(mf4)=0.25`, `W(mf8)=0.125`

각 항의 의미:

- `Nnorm`: 일반 live vector 값 개수
- `Nwiden`: widening 결과 또는 widening operand로 인해 footprint가 큰 값 개수
- `Nacc`: reduction 또는 long-lived accumulator 개수
- `Nmask`: live mask 개수
- `Nextra`: implementation-specific temporary margin

이렇게 두면 같은 live-value 개수라도 LMUL이 클수록 `Peff`가 빠르게 증가하고, fractional LMUL에서는 같은 구간이 더 안전한 pressure 영역으로 내려간다.

정확한 hardware truth는 아니어도, asm 수정을 위한 heuristic에는 이 정도 surrogate면 충분하다.

## Microbench 제안

여기서의 microbench는 두 종류로 나누는 것이 좋다.

- extreme proof bench: dynamic LMUL 또는 fractional LMUL의 효과가 크게 드러나도록 의도적으로 만든 case
- incremental attribution bench: 어느 LMUL이 왜 좋은지 feature별로 분해해서 보여주는 case

즉, "정말 이 전략이 먹히는가"를 먼저 보여주고, 그 다음에 "왜 먹히는가"를 작은 축별로 설명하는 순서다.

또한 extreme proof bench를 제외한 대부분의 run은 fixed LMUL로 수행한다. dynamic LMUL은 각 feature를 다 측정한 뒤 마지막에 조합해서 검증하는 편이 해석이 쉽다.

### A. Extreme proof bench

이 그룹의 목적은 "dynamic LMUL이 분명히 작동한다", "fractional LMUL이 분명히 이긴다"를 보여주는 것이다. 현실 workload와 100% 같을 필요는 없고, 기계 특성을 드러내는 쪽이 더 중요하다.

### MB1. `vsetvli` switching cost baseline

목적:

- `Cset(m1->m4)`, `Cset(m4->m1)`, `Cset(m1->m8)`, `Cset(m1->mf2)` 같은 switching cost 측정

형태:

- loop 안에서 `vsetvli`로 LMUL만 바꾸고, 각 설정 뒤에 dependent dummy vector op를 둔다
- 비교군으로는 "LMUL 고정, AVL만 변경" 버전도 둔다

관찰값:

- pure mode-switch cost
- same-LMUL reconfiguration cost
- switching asymmetry 여부

이 값은 뒤의 dynamic bench에서 "switch를 해도 되는 phase 길이"를 정하는 기준이 된다.

### MB2. extreme memory phase

목적:

- low-pressure region에서 high LMUL이 분명히 이기는 조건 확인
- `Lmem*`의 상한을 잡음

형태:

- 매우 긴 contiguous copy / saxpy / triad
- temporary는 1~2개만 유지
- widening, mask, reduction 없음

변수:

- LMUL sweep: `mf2`, `m1`, `m2`, `m4`, `m8`
- stream 수 sweep: load 1개, load 2개, load 3개, store 포함

기대 패턴:

- `mf2`/`m1`은 iteration 수가 많아 손해
- 충분히 긴 구간에서는 `m4` 또는 `m8`이 명확히 우세

### MB3. fractional rescue bench

목적:

- fractional LMUL이 실제로 이기는 조건을 의도적으로 만듦
- "pressure가 충분히 크면 `m1`도 과하다"는 것을 보여줌

형태:

- 좁은 loop body 안에 long-lived temporary와 accumulator를 많이 둠
- 마지막에만 결과를 소비해서 live range를 길게 유지
- plain ALU 버전과 widening 버전 둘 다 준비

변수:

- LMUL sweep: `mf4`, `mf2`, `m1`, `m2`
- live temporary 개수 `K` sweep

기대 패턴:

- 작은 `K`에서는 `m1`이 가장 좋거나 비슷
- 특정 임계점 이후에는 `m1`이 cliff에 걸리고 `mf2`가 승리
- 더 과한 압력에서는 `mf4`까지 의미가 생길 수 있음

이 bench는 fractional LMUL을 "이론적으로 가능"이 아니라 "실제로 필요할 수 있음"으로 보여주는 핵심 case다.

### MB4. two-phase synthetic dynamic bench

목적:

- 같은 loop body 안에서 mixed LMUL이 fixed LMUL보다 이기는 극단적 사례 생성

형태:

- 앞부분은 긴 streaming load/store 또는 simple transform
- 뒷부분은 widening/reduction 또는 temporary-dense compute
- region 경계는 명확하게 보이도록 설계

비교군:

- fixed `mf2`
- fixed `m1`
- fixed `m2`
- fixed `m4`
- fixed `m8`
- mixed 예: `m8 -> m1`, `m4 -> mf2`

기대 패턴:

- memory phase만 보면 high LMUL이 이김
- pressure phase만 보면 low/fractional LMUL이 이김
- 전체 loop에서는 mixed LMUL이 최선

이 bench가 dynamic LMUL의 "proof of concept figure"로 가장 적합하다.

### MB5. widening cliff bench

목적:

- widening 계열에서 pressure cliff가 plain ALU보다 훨씬 빨리 오는지 확인
- fractional LMUL 필요성을 더 강하게 보여줌

형태:

- `i8 -> i16 -> i32` 또는 `i16 -> i32` widening multiply-accumulate
- optional narrowing store
- accumulator 수를 의도적으로 늘림

변수:

- LMUL sweep: `mf2`, `m1`, `m2`, `m4`
- accumulator 개수 sweep

기대 패턴:

- 같은 live-value 개수에서도 widening bench가 더 빨리 cliff에 도달
- 일부 구간에서 `m1`보다 `mf2`가 더 안정적일 수 있음

### B. Incremental attribution bench

이 그룹의 목적은 "어느 LMUL이 왜 좋은가"를 축별로 분해해서 설명하는 것이다. extreme bench에서 보인 현상을 feature에 다시 매핑하는 역할을 한다.

### MB6. stream-count sweep

목적:

- `Bmem(L, Ns)` 측정
- memory-dominated region의 best LMUL이 stream 수에 따라 어떻게 달라지는지 확인

형태:

- `y[i] = x[i]`
- `y[i] = a * x[i] + b`
- `y[i] = x[i] + z[i]`
- `y[i] = a * x[i] + z[i]`

변수:

- LMUL sweep: `mf2`, `m1`, `m2`, `m4`, `m8`
- stream 수 sweep: load 1개, load 2개, load 3개, store 포함

관찰값:

- 큰 LMUL이 load/store overhead를 얼마나 줄이는지
- stream 수가 많아질수록 큰 LMUL 이점이 유지되는지

### MB7. pure compute throughput

목적:

- `Talu(Op, L)` 추정

형태:

- independent vector add chains
- independent vector mul/FMA accumulators
- latency 버전과 throughput 버전 분리

관찰값:

- 큰 LMUL이 pure compute에서도 좋은지
- 아니면 memory region에서만 큰 LMUL이 이득인지

### MB8. live temporary sweep

목적:

- `Pcliff(Class, L)` 추정

형태:

- fixed-LMUL kernel에서 independent live vector temporary 또는 accumulator 개수 `K`를 늘린다
- 예: `v0..v(K-1)`를 동시에 live로 유지한 뒤 마지막에 모두 소비

변수:

- LMUL sweep
- op class sweep: plain ALU, FMA, widening MAC

관찰값:

- 성능 cliff가 시작되는 `K`
- LMUL이 커질수록 cliff가 어디로 이동하는지

이 microbench가 dynamic LMUL 논리에서 가장 중요하다.

### MB9. phase-length sweep

목적:

- switching이 언제부터 이득인지 확인
- `SavedCycles > Cset + Hysteresis` 규칙을 empirical하게 검증

형태:

- 동일한 두-phase kernel에서 memory phase 길이만 늘리거나 줄임
- 또는 pressure-heavy phase 길이만 조절

관찰값:

- 어느 길이부터 switching이 이득인지
- 왕복 switching이 언제부터 손해인지

### MB10. spill surrogate

목적:

- `Sspill(L)` 추정

형태:

- compute block 사이에 명시적 save/reload traffic 삽입
- stack 또는 별도 spill buffer 사용

관찰값:

- pressure cliff를 넘었을 때 penalty가 어느 정도인지 rough estimate 확보

정확한 allocator spill은 아니지만, "spill이 나면 대략 얼마나 나빠지는가"를 보여주기엔 충분하다.

### MB11. masked execution

목적:

- `Mmask(L)` 측정

형태:

- 같은 arithmetic kernel에 대해 mask density를 바꿔가며 실행

관찰값:

- predicate-heavy kernel이면 큰 LMUL 이득이 유지되는지
- mask-heavy case에서 fractional LMUL이 pressure 완화에 도움이 되는지

mask를 거의 쓰지 않는 workload라면 생략 가능하다.

## 추천 측정 순서

가장 설득력 있는 순서는 "proof first, attribution second"다.

1. `MB1`: switching overhead 측정
2. `MB2`: extreme memory phase로 high LMUL win 확인
3. `MB3`: fractional rescue bench로 fractional LMUL win 확인
4. `MB4`: two-phase synthetic bench로 mixed LMUL win 확인
5. `MB6`, `MB7`, `MB8`: 왜 그런 결과가 나왔는지 feature별 분해
6. 필요하면 `MB9`, `MB10`, `MB11`로 switching threshold, spill penalty, mask effect 보강

가장 작은 세트는 `MB1 + MB2 + MB3 + MB4`다. 이 네 개만 있어도:

- high LMUL이 유리한 구간
- fractional LMUL이 유리한 구간
- mixed LMUL이 유리한 구간

을 각각 분리해서 보여줄 수 있다.

## Dynamic LMUL 적용 규칙

현재 단계에서는 compiler가 자동으로 이해할 수 있는 복잡한 모델보다, 사람이 asm을 수정할 수 있는 규칙이면 충분하다.

핵심 아이디어는 loop body를 region으로 나누고 region별로 LMUL을 고르는 것이다.

### Region 분할 기준

loop body를 아래와 같은 region으로 나눈다.

- load / address update cluster
- simple arithmetic cluster
- widening / reduction cluster
- store cluster

또는 더 일반적으로,

- live vector set이 크게 변하는 지점
- widening op가 시작되는 지점
- long-lived accumulator가 늘어나는 지점

에서 split한다.

### Region 분류

각 region을 아래 중 하나로 분류한다.

- `mem`: load/store 비중이 높고 temporary가 적다
- `alu`: simple arithmetic 위주이며 pressure가 중간 수준
- `wide`: widening/narrowing/reduction 위주이며 pressure 민감도가 높다
- `mixed`: 한 region 안에 두 성질이 섞여 있으면 더 쪼갠다

### LMUL 선택 규칙

region `R`에 대해 `Peff(R)`를 계산하고, 아래 규칙으로 LMUL을 고른다.

1. `mem` region이고 `Peff(R)`가 충분히 낮으면 큰 LMUL 사용
   - 보통 `m4` 또는 `m8`
2. `wide` region이면 한 단계 또는 두 단계 낮은 LMUL 사용
   - 보통 `m1` 또는 `m2`, 필요하면 `mf2`
3. `alu` region은 machine measurement에 따라 선택
   - `Lcmp*`가 `m2`면 `m2`, `m4`면 `m4`
4. `Peff(R)`가 `Pcliff(Class, L)` 근처면 안전하게 더 작은 LMUL 선택
5. region이 너무 짧으면 switching 하지 않고 이전 LMUL 유지

이를 더 요약하면:

- low pressure + long memory region -> 큰 LMUL
- high pressure / widening / reduction region -> 작은 LMUL, 필요하면 fractional LMUL
- tiny region -> switch 금지

### Switching 규칙

`prev` LMUL에서 `next` LMUL로 바꾸는 조건:

```text
SavedCycles(R, next) > Cset(prev->next) + Hysteresis
```

여기서:

- `SavedCycles`는 해당 region에서 예상되는 body cost 감소량
- `Hysteresis`는 measurement noise와 불안정한 oscillation을 막기 위한 margin

실용적으로는 아래와 같은 정성 규칙으로도 충분하다.

- load/store region 길이가 길수록 switching 허용
- 바로 다음 짧은 region에서 다시 원복해야 하면 switching 자제
- pressure cliff 근처에서는 무조건 보수적으로 선택

## 실용적인 asm-level 규칙

논문 초안이나 manual tuning 관점에서는 다음 규칙이 가장 설명하기 쉽다.

### Rule A. Memory phase는 가장 큰 safe LMUL 사용

- contiguous load/store 위주
- temporary 1~2개 수준
- widening 없음

이 경우 `m4` 또는 `m8` 사용

### Rule B. Widening / reduction phase는 작은 LMUL로 낮춤

- widening multiply
- widening add
- reduction accumulator
- polynomial approximation with many temporaries

이 경우 `m1` 또는 `m2` 사용, `m1`에서도 cliff가 보이면 `mf2`까지 고려

### Rule C. Pressure cliff 근처는 작은 LMUL 선택

microbench에서 얻은 `Pcliff(Class, L)` 근처로 추정되면, raw throughput이 조금 좋아 보여도 작은 LMUL 선택. 필요하면 `m1`보다 더 낮은 `mf2/mf4`를 써서 register footprint 자체를 줄인다.

### Rule D. Tiny phase는 그대로 둠

phase 길이가 짧아서 `vsetvli` cost를 회수하지 못하면 switching 하지 않음

### Rule E. One-way switching이 가능하면 적극 사용

예를 들어:

- 긴 load phase에서 `m8`
- 이어지는 dense compute phase에서 `m2`
- loop 끝까지 `m2` 유지

처럼 "왕복 switching"보다 "한 번만 큰 폭으로 낮추는" 구조가 더 유리할 수 있다.

## 간단한 비용 모델

region `R`와 candidate LMUL `L`에 대해:

```text
Cost(R, L) = BodyCost(R, L) + SpillPenalty(R, L)
```

여기서:

- `BodyCost`는 `Bmem`, `Talu`, `Twiden`에서 추정
- `SpillPenalty`는 `Peff(R)`가 `Pcliff(Class, L)`를 넘으면 큰 값을 부여

최종적으로 region별 최소 cost LMUL을 고른 뒤, 인접 region 사이 switching 이득이 `Cset`보다 큰 경우에만 `vsetvli`를 삽입한다.

정밀 모델이 아니더라도, 이 정도면 "왜 어떤 loop에서 mixed LMUL이 fixed LMUL보다 좋은가"를 설명하기에 충분하다.

## Real Small Benchmark 후보

microbench보다 복잡하지만 여전히 작고 설명 가능한 benchmark가 필요하다. 아래 benchmark들은 하나의 loop body 안에 "큰 LMUL이 좋은 구간"과 "작은 LMUL이 좋은 구간"이 같이 존재한다.

### 1. Unrolled FIR-16 / FIR-32

구조:

- input/tap load
- 여러 tap의 multiply-accumulate
- final store

dynamic LMUL 포인트:

- load phase는 큰 LMUL 선호
- accumulator 수가 늘어나는 MAC phase는 작은 LMUL 선호

장점:

- 설명이 쉽고 signal-processing 예제로 익숙함

### 2. `int8` 또는 `int16` dequantized GEMV

구조:

- packed input/weight load
- widening multiply
- `i32` accumulation
- optional scale / store

dynamic LMUL 포인트:

- load phase는 큰 LMUL 선호
- widening MAC phase는 pressure가 급격히 증가하여 작은 LMUL 선호

장점:

- widening pressure 문제를 가장 분명하게 보여줌

### 3. Softmax row kernel

구조:

- load
- max reduction
- subtract max
- exp approximation
- sum reduction
- normalize and store

dynamic LMUL 포인트:

- load, subtract, final store는 큰 LMUL 후보
- reduction과 exp approximation은 작은 LMUL 후보

장점:

- ML workload로 설명 가능

### 4. LayerNorm / RMSNorm

구조:

- load
- mean 또는 norm accumulation
- reciprocal sqrt / normalization
- affine transform
- store

dynamic LMUL 포인트:

- load/store와 affine transform은 큰 LMUL 후보
- accumulation 및 normalization core는 작은 LMUL 후보

### 5. 5-point / 9-point stencil with nonlinear update

구조:

- neighbor load 다수
- stencil sum
- limiter 또는 nonlinear update
- store

dynamic LMUL 포인트:

- neighbor load는 큰 LMUL 후보
- nonlinear update에서 temporary가 많아져 작은 LMUL 후보

### 6. RGB -> YUV + gamma / clamp

구조:

- deinterleaved load
- color transform
- polynomial 또는 piecewise gamma
- clamp/store

dynamic LMUL 포인트:

- load/store phase는 큰 LMUL 후보
- gamma approximation phase는 작은 LMUL 후보

## 우선순위가 높은 benchmark

빠르게 설득력 있는 결과를 얻으려면 아래 세 개를 먼저 보는 것이 좋다.

1. `FIR-16`
2. `int8 -> i32` dequantized GEMV
3. softmax row

이 세 개는 모두:

- phase 구조가 명확하고
- dynamic LMUL 직관이 설명 가능하며
- microbench에서 얻은 feature와 연결하기 쉽다

## 기대 결과

가장 보고 싶은 패턴은 다음과 같다.

- fixed `m1`은 high-pressure region에서는 안정적이지만 memory phase에서 손해
- fixed `mf2`/`mf4`는 pressure escape에는 유리하지만 iteration 수 증가로 memory phase에서 더 불리할 수 있음
- fixed `m4`/`m8`은 memory phase에서는 좋지만 pressure-heavy phase에서 손해
- mixed LMUL은 두 phase의 장점을 동시에 취함

즉, 좋은 결과는 "항상 큰 LMUL이 최고"가 아니라:

```text
memory-like region: high LMUL wins
pressure-heavy region: low LMUL wins
same loop body: mixed LMUL wins
```

이 경향을 여러 benchmark에서 반복적으로 보이면, dynamic LMUL이 hand-picked anecdote가 아니라 machine-aware optimization이라는 주장을 할 수 있다.

## 최소 실험 계획

가장 작은 실험 세트는 다음과 같다.

1. `MB1`로 `vsetvli` switching overhead 측정
2. `MB2`로 "긴 low-pressure memory phase에서는 high LMUL이 이긴다"를 확인
3. `MB3`로 "pressure cliff 근처에서는 fractional LMUL이 이긴다"를 확인
4. `MB4`로 "같은 loop body에서는 mixed LMUL이 이긴다"를 확인
5. `FIR-16`, dequantized GEMV, softmax row에 대해:
   - fixed `mf2`
   - fixed `m1`
   - fixed `m2`
   - fixed `m4`
   - fixed `m8`
   - manual mixed LMUL
   를 비교

이 정도만 해도:

- dynamic LMUL이 실제로 이긴다는 것
- fractional LMUL이 단순한 spec artifact가 아니라 실제 escape hatch라는 것
- 각 승패가 memory throughput, pressure cliff, switching cost 중 무엇 때문인지

를 충분히 설명할 수 있다.
