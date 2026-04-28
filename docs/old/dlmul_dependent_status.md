# Dynamic LMUL Dependent Bench Status

Source DB: `artifacts/dlmul-bench.sqlite`

## Existing Evidence

| Case | Role | Best dynamic | Best fixed | Kernel speedup |
| --- | --- | ---: | ---: | ---: |
| `db3-long` | independent duplicate | `40,002` | `59,337` | `32.6%` |
| `db4` | independent duplicate | `52,491` | `74,491` | `29.5%` |
| `db1` | independent control | `50,132` | `68,843` | `27.2%` |
| `db3-medium` | independent duplicate | `30,167` | `40,932` | `26.3%` |
| `db3-short` | independent duplicate | `23,809` | `27,941` | `14.8%` |
| `db6` | independent duplicate | `69,484` | `80,325` | `13.5%` |
| `db8-medium` | dependent negative/control | `135,377` | `48,784` | `-177.5%` |
| `db9` | dependent negative/control | `78,785` | `33,337` | `-136.3%` |
| `db10` | pure negative control | `49,591` | `31,092` | `-59.5%` |

The current DB supports keeping `db1` as the single independent control and retaining `db8-medium` plus `db9` as dependent negative/control evidence. It does not contain `db11` or `db12`, so performance acceptance for the new dependent candidates still needs the remote run.

## New Dependent Candidates

`db11` is implemented as a fused color/gamma polynomial chain with an `m4 -> m2 -> m4` dynamic path. The m2 island consumes `y/u/v/k0/k1` values produced or loaded in the wide region, and the final m4 consumer uses both `y` and the m2-produced `gamma`.

`db12` is implemented as a normalized force chain with an `m4 -> m2 -> m4` dynamic path. The m2 island consumes the wide-produced energy seed and coordinate vectors, then the final m4 consumer updates velocity outputs from the m2-produced force vectors.

## Current Blocker

Targeted local benchmark execution is blocked because the benchmark image is not available in this session:

```text
Docker image not found: vplan-cost-measure:latest
Build or tag the image first, for example: docker build -t vplan-cost-measure:latest .
```

The default manifest has been pruned by request to `db1`, `db11`, `db12`, `db8-medium`, and `db9`. The demoted historical source files are kept under `emulator/run/src/bench/dlmul/legacy/` for reference only. The next command to run in the remote benchmark environment is:

```sh
python3 scripts/dlmul_bench.py --case db11 --db-path artifacts/dlmul-bench-db11.sqlite --log-root artifacts/dlmul-bench-db11
```
