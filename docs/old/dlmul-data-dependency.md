# Dynamic LMUL Data Dependency Notes

Source DB: `artifacts/dlmul-bench.sqlite`

이 문서의 목적은 하나다.

```text
dynamic LMUL의 비용을 설명하는 핵심 요인이
"phase 간 data dependency가 있는가?"인지,
아니면
"LMUL boundary value가 실제 asm에서 copy/spill/reload로 materialize되는가?"인지
구분하는 것
```

이번 문서는 아래 순서로 읽으면 된다.

1. 어떤 가설을 검증하려는가
2. 그 가설을 보기 위해 어떤 벤치를 두었는가
3. 현재 DB에서는 무엇이 이미 확인되었는가
4. 무엇이 이미 직접 검증됐고, 남은 질문이 무엇인가

## 핵심 가설

이번에 보고 싶은 가설은 사실 두 단계다.

### 가설 1. 단순한 dependency 유무만으로는 설명이 안 된다

phase 1의 값이 phase 2나 phase 3에서 쓰인다고 해서, 그 자체만으로 dynamic
LMUL이 반드시 비싸지는 것은 아닐 수 있다.

즉 아래 두 문장은 다를 수 있다.

- `phase 1 -> phase 2/3 dependency exists`
- `그 dependency가 실제 register-group copy나 spill/reload를 강제한다`

### 가설 2. 진짜로 비싼 경우는 aliasing이 깨질 때다

핵심은 "m4에서 만든 값을 m2에서 쪼개 쓸 때, 같은 physical register half를
그대로 재해석해서 쓸 수 있는가?"다.

가능하면 싸다. 불가능하면 복사가 생긴다.

이걸 가장 잘 보여주는 예시는 아래 두 asm이다.

## 보고 싶은 asm 차이

### `kernel_alias_ok`

이 경우는 phase 2가 phase 1의 `m4` 값을 반쪽씩 제자리에서 업데이트해도 된다.
phase 3는 "업데이트된 m4 값"만 필요하므로 원래 값을 따로 보존할 필요가 없다.

```asm
kernel_alias_ok:
      # Phase 1: produce one m4 value A in v8-v11.
      vsetivli zero, 16, e32, m4, ta, ma
      vle32.v   v8,  (a0)        # A input, m4: v8-v11
      vle32.v   v12, (a1)        # B input, m4: v12-v15
      vfadd.vv  v8, v8, v12      # A = x + y, still v8-v11

      # Phase 2: switch to m2 and operate on A's two halves in place.
      # A.low  is v8-v9.
      # A.high is v10-v11.
      vsetivli zero, 8, e32, m2, ta, ma
      vfadd.vv  v8,  v8,  v8     # chunk 0: update lower half in place
      vfadd.vv  v10, v10, v10    # chunk 1: update upper half in place

      # Phase 3: switch back to m4. v8-v11 is already the reassembled m4 value.
      vsetivli zero, 16, e32, m4, ta, ma
      vse32.v   v8, (a2)

      ret
```

여기서는 중요한 것이 없다.

- `vmv2r.v` 없음
- 별도 temporary group 없음
- `v8-v11`를 그대로 m2 half로 재사용

즉 cheap half aliasing case다.

### `kernel_alias_bad`

이 경우는 phase 2에서 phase 1의 `m4` 값을 쪼개 써야 하지만, phase 3에서
원래 `A`도 계속 필요하다. 그래서 `v8-v11`를 덮어쓸 수 없고, half를 다른
register group으로 복사해야 한다.

```asm
kernel_alias_bad:
      # Phase 1: produce one m4 value A in v8-v11.
      vsetivli zero, 16, e32, m4, ta, ma
      vle32.v   v8,  (a0)        # A input, m4: v8-v11
      vle32.v   v12, (a1)        # B input, m4: v12-v15
      vfadd.vv  v8, v8, v12      # A = x + y, v8-v11

      # Phase 2: need m2 chunks derived from A, but A must remain live.
      # Cannot clobber v8-v11, so copy halves out.
      vsetivli zero, 8, e32, m2, ta, ma
      vmv2r.v   v24, v8          # T.low  = copy A.low  from v8-v9
      vmv2r.v   v26, v10         # T.high = copy A.high from v10-v11

      vfadd.vv  v24, v24, v24    # update T.low
      vfadd.vv  v26, v26, v26    # update T.high

      # Phase 3: A is still needed, so v8-v11 had to be preserved.
      vsetivli zero, 16, e32, m4, ta, ma
      vfmul.vv  v16, v8, v8      # uses original A
      vse32.v   v16, (a2)

      # T is now assembled as m4 in v24-v27 from two m2 chunks.
      vse32.v   v24, (a3)

      ret
```

여기서 보고 싶은 것은 명확하다.

- `vmv2r.v` 등장
- 원래 `A`와 chunked temporary `T`가 동시에 live
- phase 3에서 original `A`와 reconstructed `T`가 서로 다른 register group에 존재

즉 expensive materialized-transfer case다.

## 이번에 둔 실험들

이번 코드베이스에는 두 축의 실험이 있다.

### 1. 이미 실행되어 DB에 들어간 실험

현재 DB에는 아래 11개 case가 들어 있다.

- 기존 workload:
  - `db1`
  - `db11`
  - `db12`
  - `db8-medium`
  - `db9`
- synthetic dependency matrix:
  - `no-data-dep`
  - `dep-1-3`
  - `dep-1-2`
  - `dep-1-3-1-2`

이 실험의 목적은 "dependency edge 자체가 성능을 얼마나 설명하느냐"를 먼저
보는 것이다.

### 2. aliasing을 직접 분리한 실험

현재 DB에는 아래 두 개의 alias isolation case도 들어 있다.

- `alias-ok`
- `alias-bad`

이 둘의 목적은 dependency edge 유무가 아니라, 바로 위 asm 예시처럼
"half aliasing이 유지되는가 / 깨지는가"를 직접 분리해서 보는 것이다.

## 현재 DB에서 확인된 결과

모든 dynamic variant는 `status=PASS`, `asm_check_status=PASS`였다.

### 1. 기존 workload 5개

`kernel_cycles` 기준으로 dynamic과 best fixed를 비교하면 다음과 같다.

| Case | Dynamic | Best fixed | Dynamic vs best fixed | 해석 |
| --- | --- | --- | ---: | --- |
| `db1` | `dyn_m4_m2_m4` `50,132` | `fixed_m2` `68,843` | `27.2%` faster | phase 간 독립성이 커서 dynamic이 이김 |
| `db11` | `dyn_m4_m2_m4` `48,220` | `fixed_m4` `41,427` | `16.4%` slower | dependency는 있지만 큰 transfer cost는 없음 |
| `db12` | `dyn_m4_m2_m4` `56,923` | `fixed_m4` `52,666` | `8.1%` slower | dependency가 group copy로 materialize됨 |
| `db8-medium` | `dyn_m8_m2_m8` `135,377` | `fixed_m2` `48,784` | `177.5%` slower | `m8 -> m2 -> m8` transfer와 loop-carried path가 매우 비쌈 |
| `db9` | `dyn_m8_m2_m4` `78,785` | `fixed_m4` `33,337` | `136.3%` slower | `m8 -> m2 -> m4` transfer 비용이 큼 |

### 2. dependency matrix 4개

| Case | Dependency | Dynamic | Best fixed | Dynamic vs best fixed |
| --- | --- | ---: | ---: | ---: |
| `no-data-dep` | 없음 | `52,268` | `45,282` (`fixed_m4`) | `15.4%` slower |
| `dep-1-3` | phase 1 -> phase 3 | `50,414` | `42,080` (`fixed_m4`) | `19.8%` slower |
| `dep-1-2` | phase 1 -> phase 2 | `54,236` | `45,685` (`fixed_m4`) | `18.7%` slower |
| `dep-1-3-1-2` | phase 1 -> phase 2, 3 | `54,346` | `44,198` (`fixed_m4`) | `23.0%` slower |

이 4개는 기대한 만큼 깔끔한 ordering을 주지 않았다.

- `dep-1-3`는 `no-data-dep`보다 오히려 빠르다.
- `dep-1-2`와 `dep-1-3-1-2`는 조금 느리지만, 차이가 아주 크진 않다.
- 즉 "dependency edge가 많을수록 반드시 느려진다"는 수준의 증거는 아니다.

### 3. alias isolation 2개

이제 직접 보고 싶었던 `alias-ok` / `alias-bad`도 DB에 들어 있다.

| Case | Dynamic | Best fixed | Dynamic vs best fixed | 해석 |
| --- | --- | --- | ---: | --- |
| `alias-ok` | `dyn_m4_m2_m4` `23,961` | `fixed_m4` `23,468` | `2.1%` slower | in-place half reuse라 boundary cost가 거의 없다 |
| `alias-bad` | `dyn_m4_m2_m4` `39,194` | `fixed_m4` `37,278` | `5.1%` slower | original wide value를 살려야 해서 group copy가 생긴다 |

이 둘을 dynamic끼리 직접 비교하면 `alias-bad`는 `alias-ok`보다 `63.6%`
느리다.

즉 source-level dependency 여부가 아니라, aliasing이 유지되느냐 깨지느냐가
실제로 measurable한 차이를 만든다.

## asm에서 실제로 본 것

dynamic variant의 `kernel` 함수만 따로 잘라서 `vmv*r.v`, `vs*r.v`,
`vl*r.v`를 셌다.

| Case | `vsetvli` | `vmv*r.v` | Spill | Reload | 해석 |
| --- | ---: | ---: | ---: | ---: | --- |
| `db1` | 6 | 0 | 2 | 2 | 독립 workload라 boundary transfer는 없음 |
| `db11` | 5 | 0 | 0 | 0 | dependency가 있어도 aliasing이 유지됨 |
| `db12` | 5 | 7 | 0 | 0 | group copy가 실제로 생김 |
| `db8-medium` | 49 | 38 | 23 | 228 | transfer가 spill/reload까지 폭발 |
| `db9` | 14 | 11 | 8 | 28 | `m8 -> m2` 경계가 비쌈 |
| `no-data-dep` | 5 | 0 | 0 | 0 | synthetic이지만 transfer 신호 없음 |
| `dep-1-3` | 5 | 0 | 0 | 0 | transfer 신호 없음 |
| `dep-1-2` | 5 | 0 | 0 | 0 | transfer 신호 없음 |
| `dep-1-3-1-2` | 5 | 0 | 0 | 0 | transfer 신호 없음 |
| `alias-ok` | 5 | 0 | 0 | 0 | half aliasing이 유지돼 in-place reuse로 끝남 |
| `alias-bad` | 5 | 7 | 0 | 0 | `vmv4r.v`/`vmv2r.v`로 group copy가 materialize됨 |

이 표가 현재 DB에서 제일 중요한 포인트다.

dependency matrix 4개는 source-level dependency는 다르지만 asm-level
transfer 신호는 사실상 동일했다.

반대로 alias pair는 dependency라는 큰 틀은 비슷하지만 asm-level transfer
신호가 갈린다.

- `alias-ok`는 `vmv*r.v` 없이 in-place half reuse로 끝난다.
- `alias-bad`는 `vmv4r.v`, `vmv2r.v`가 실제로 생긴다.
- 둘 다 spill/reload는 없으므로, 여기서는 pure group-copy materialization만
  분리해서 보고 있다고 해석할 수 있다.

즉 이번 DB는 아래 주장을 강하게 지지한다.

```text
"dependency exists?" 만으로는 부족하고,
"그 dependency가 실제 asm에서 vmv/spill/reload로 materialize되는가?"
가 더 직접적인 비용 원인이다.
```

## 현재까지의 결론

현재 DB로 확실히 말할 수 있는 것은 다음이다.

1. data dependency 자체는 충분조건이 아니다.
   - `db11`은 dependency가 있어도 큰 move/spill/reload가 없다.
   - synthetic 4개도 dependency edge 차이만으로는 asm 차이를 못 만들었다.

2. 진짜로 비싼 경우는 aliasing이 깨져서 value transfer가 materialize될 때다.
   - `db12`는 `vmv*r.v`가 나타난다.
   - `db8-medium`, `db9`는 move + spill + reload가 함께 나타난다.
   - `alias-bad`는 `alias-ok`와 달리 `vmv*r.v` 7개가 생기고, dynamic 기준으로도
     `alias-ok`보다 `63.6%` 느리다.

3. `alias-ok` 대 `alias-bad`는 이번 DB에서 가장 직접적인 메커니즘 검증이다.
   - `alias-ok`는 in-place half reuse가 가능한 경우
   - `alias-bad`는 original wide value를 phase 3까지 살려야 해서 copy가 필요한 경우
   - 이 둘의 차이는 "dependency가 있느냐"보다 "copy가 materialize되느냐"가 더
     직접적인 비용 원인임을 보여준다

## 남은 질문

`alias-ok` / `alias-bad`로 "group copy materialization" 자체는 이미 직접
검증됐다. 이제 남은 질문은 그 다음 단계다.

- 언제 단순 `vmv*r.v` 수준에서 끝나고,
- 언제 `db8-medium`, `db9`처럼 spill/reload까지 폭발하는가?
- 특히 wide LMUL(`m8`)과 loop-carried live range가 결합될 때 register pressure가
  어떤 임계점을 넘는가?

```text
비용의 본질이 "dependency 존재"인가,
아니면 "original wide value를 살려야 해서 copy가 생기는가"인가?
```

현재 DB는 두 번째 설명을 강하게 지지한다. 다음 단계는 그 copy pressure가 언제
spill/reload 단계로 증폭되는지를 더 정교하게 분해하는 것이다.
