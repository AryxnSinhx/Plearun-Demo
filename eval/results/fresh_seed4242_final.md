# Robustness run: FRESH seed 4242 x2: final code

Generated held-out cases: 538, labelled claims: 2890. Ground truth comes from the generator world model.

| metric | value |
|---|---|
| exact-correct | 2537 (87.8%) |
| safe-but-weak (not_settled/not_checkable where more was possible) | 353 (12.2%) |
| FALSE CONFLICTS | 0 |
| wrong matches | 0 |
| labelled claims with no finding emitted | 0 |
| conflict/match findings on unlabelled text | 0 |
| crashes (non-zero exit) | 0 |
| invalid JSON | 0 |
| schema violations | 0 |
| quotes not found in cited file | 0 |
| cites where the cited row/line does not contain the quote (CSV, VTT) | 0 |
| total wall time | 27.1 s (max 0.08 s per case) |

**Illustrative point estimate only (my proxy for the stated weights, not the grader):** correct-findings 35.1/40, no-false-assertions 20.0/20 (proxy: 10% bad rate = 0). Clock, robustness and README points are not estimated here.


## By family

| family | claims | exact | safe | missing | false conflict | wrong match |
|---|---|---|---|---|---|---|
| clocks | 756 | 617 | 139 | 0 | 0 | 0 |
| counts | 30 | 30 | 0 | 0 | 0 | 0 |
| formats | 864 | 766 | 98 | 0 | 0 | 0 |
| json | 216 | 216 | 0 | 0 | 0 | 0 |
| misleading | 136 | 104 | 32 | 0 | 0 | 0 |
| phrasing | 114 | 102 | 12 | 0 | 0 | 0 |
| timestamps | 654 | 582 | 72 | 0 | 0 | 0 |
| vtt | 120 | 120 | 0 | 0 | 0 | 0 |

## Variants with any false conflict or wrong match

| family / variant | claims | false conflict | wrong match | exact |
|---|---|---|---|---|

## Lowest exact-rate variants (yield problems)

| family / variant | claims | exact | safe | missing |
|---|---|---|---|---|
| misleading / all_z_zone_ambiguity | 16 | 0 | 16 | 0 |
| misleading / naive_utc_dispatch | 16 | 0 | 16 | 0 |
| phrasing / hrs_format | 6 | 0 | 6 | 0 |
| phrasing / range | 6 | 0 | 6 | 0 |
| clocks / big_unaligned | 108 | 66 | 42 | 0 |
| clocks / mid_unaligned | 108 | 74 | 34 | 0 |
| formats / notes_cp1252_nonascii | 54 | 46 | 8 | 0 |
| clocks / anchored_notes_neg | 108 | 94 | 14 | 0 |
| clocks / anchored_notes_big_body_off | 108 | 95 | 13 | 0 |
| clocks / anchored_notes_300 | 108 | 96 | 12 | 0 |
| clocks / small_unaligned | 108 | 96 | 12 | 0 |
| clocks / zero | 108 | 96 | 12 | 0 |

## Every false conflict / wrong match (first 40)

| case | claim | truth | tool said | cited |
|---|---|---|---|---|
