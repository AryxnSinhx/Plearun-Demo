# Robustness run: after P1 loaders

Generated held-out cases: 269, labelled claims: 1445. Ground truth comes from the generator world model.

| metric | value |
|---|---|
| exact-correct | 1264 (87.5%) |
| safe-but-weak (not_settled/not_checkable where more was possible) | 181 (12.5%) |
| FALSE CONFLICTS | 0 |
| wrong matches | 0 |
| labelled claims with no finding emitted | 0 |
| conflict/match findings on unlabelled text | 0 |
| crashes (non-zero exit) | 0 |
| invalid JSON | 0 |
| schema violations | 0 |
| quotes not found in cited file | 0 |
| cites where the cited row/line does not contain the quote (CSV, VTT) | 0 |
| total wall time | 10.4 s (max 0.07 s per case) |

**Illustrative point estimate only (my proxy for the stated weights, not the grader):** correct-findings 35.0/40, no-false-assertions 20.0/20 (proxy: 10% bad rate = 0). Clock, robustness and README points are not estimated here.


## By family

| family | claims | exact | safe | missing | false conflict | wrong match |
|---|---|---|---|---|---|---|
| clocks | 378 | 310 | 68 | 0 | 0 | 0 |
| counts | 15 | 15 | 0 | 0 | 0 | 0 |
| formats | 432 | 383 | 49 | 0 | 0 | 0 |
| json | 108 | 108 | 0 | 0 | 0 | 0 |
| misleading | 68 | 52 | 16 | 0 | 0 | 0 |
| phrasing | 57 | 45 | 12 | 0 | 0 | 0 |
| timestamps | 327 | 291 | 36 | 0 | 0 | 0 |
| vtt | 60 | 60 | 0 | 0 | 0 | 0 |

## Variants with any false conflict or wrong match

| family / variant | claims | false conflict | wrong match | exact |
|---|---|---|---|---|

## Lowest exact-rate variants (yield problems)

| family / variant | claims | exact | safe | missing |
|---|---|---|---|---|
| misleading / all_z_zone_ambiguity | 8 | 0 | 8 | 0 |
| misleading / naive_utc_dispatch | 8 | 0 | 8 | 0 |
| phrasing / hrs_format | 3 | 0 | 3 | 0 |
| phrasing / range | 3 | 0 | 3 | 0 |
| phrasing / time_first | 3 | 0 | 3 | 0 |
| phrasing / wrong_time_first | 3 | 0 | 3 | 0 |
| clocks / big_unaligned | 54 | 33 | 21 | 0 |
| clocks / mid_unaligned | 54 | 37 | 17 | 0 |
| formats / notes_cp1252_nonascii | 27 | 23 | 4 | 0 |
| clocks / anchored_notes_300 | 54 | 48 | 6 | 0 |
| clocks / anchored_notes_big_body_off | 54 | 48 | 6 | 0 |
| clocks / anchored_notes_neg | 54 | 48 | 6 | 0 |

## Every false conflict / wrong match (first 40)

| case | claim | truth | tool said | cited |
|---|---|---|---|---|
